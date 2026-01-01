import datetime
import hashlib
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
import uuid

from app.models.event_mapping import EventMapping


def iso_utc(dt: datetime.datetime) -> str:
    """Convert datetime to ISO UTC format (preserved from sync.py:31-32)."""
    return dt.replace(microsecond=0, tzinfo=None).isoformat() + "Z"


def fetch_events(service, calendar_id: str, time_min: str, time_max: str) -> List[dict]:
    """Fetch events with pagination (preserved from sync.py:35-55)."""
    events: List[dict] = []
    page_token = None
    while True:
        resp = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                showDeleted=True,
                pageToken=page_token,
            )
            .execute()
        )
        events.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return events


def build_payload_from_source(
    src: dict,
    sync_cluster_id: Optional[str] = None,
    dest_event_id: Optional[str] = None,
    destination_color_id: Optional[str] = None,
    origin_calendar_id: Optional[str] = None,
    sync_config_id: Optional[str] = None,
    privacy_mode_enabled: bool = False,
    privacy_placeholder_text: str = "Personal appointment",
) -> dict:
    """Build event payload from source event with bi-directional and privacy support."""
    extended_props = {
        "source_id": src.get("id"),
        "synced_by_system": "true",  # CRITICAL: Loop prevention flag
    }

    # Add bidirectional tracking metadata
    if sync_cluster_id:
        extended_props["sync_cluster_id"] = sync_cluster_id
        extended_props["last_sync_timestamp"] = iso_utc(datetime.datetime.now(datetime.timezone.utc))
        if dest_event_id:
            extended_props["dest_event_id"] = dest_event_id

    if origin_calendar_id:
        extended_props["origin_calendar_id"] = origin_calendar_id
        extended_props["origin_event_id"] = src.get("id")

    if sync_config_id:
        extended_props["sync_config_id"] = sync_config_id

    # Build base payload
    body = {
        "summary": src.get("summary"),
        "description": src.get("description"),
        "location": src.get("location"),
        "start": src.get("start"),
        "end": src.get("end"),
        "recurrence": src.get("recurrence"),
        "transparency": src.get("transparency"),
        "visibility": src.get("visibility"),
        "colorId": destination_color_id if destination_color_id else src.get("colorId"),
        "reminders": {"useDefault": False},  # avoid noisy notifications
        "extendedProperties": {
            "shared": extended_props
        },
    }

    # Apply privacy transformation if enabled
    if privacy_mode_enabled:
        body["summary"] = privacy_placeholder_text
        body["description"] = ""
        body["location"] = ""
        body.pop("attendees", None)  # Remove attendees if present
        extended_props["privacy_mode"] = "true"

    # Remove None entries the Calendar API dislikes.
    return {k: v for k, v in body.items() if v is not None}


def events_differ(src_body: dict, dest_event: dict) -> bool:
    """Check if events differ (preserved from sync.py:80-96)."""
    comparable_keys = [
        "summary",
        "description",
        "location",
        "start",
        "end",
        "recurrence",
        "transparency",
        "visibility",
        "colorId",
        "reminders",
    ]
    for key in comparable_keys:
        if src_body.get(key) != dest_event.get(key):
            return True
    return False


def compute_content_hash(event: dict) -> str:
    """Compute SHA-256 hash of event content for change detection (Story 3)."""
    comparable_fields = {
        "summary": event.get("summary"),
        "description": event.get("description"),
        "location": event.get("location"),
        "start": event.get("start"),
        "end": event.get("end"),
        "recurrence": event.get("recurrence"),
        "transparency": event.get("transparency"),
        "visibility": event.get("visibility"),
        "colorId": event.get("colorId"),
    }
    content = str(sorted(comparable_fields.items()))
    return hashlib.sha256(content.encode()).hexdigest()


class SyncEngine:
    """Refactored sync logic from sync.py with database integration."""

    def __init__(self, db: Session):
        self.db = db

    def should_skip_event(self, event: dict, sync_config_id: str) -> tuple[bool, str]:
        """
        Determine if event should be skipped from syncing (loop prevention).

        Returns:
            (should_skip: bool, reason: str)
        """
        shared = event.get("extendedProperties", {}).get("shared", {})

        # Skip if synced by system (loop prevention)
        if shared.get("synced_by_system") == "true":
            return (True, "synced_by_system")

        return (False, "")

    def get_origin_calendar_id(
        self,
        event: dict,
        mapping: Optional[EventMapping],
        source_calendar_id: str
    ) -> str:
        """
        Determine which calendar originally created this event.

        Priority:
        1. EventMapping.origin_calendar_id (most reliable)
        2. extendedProperties.shared.origin_calendar_id
        3. Infer: if no mapping exists, source is origin
        """
        if mapping and mapping.origin_calendar_id:
            return mapping.origin_calendar_id

        shared = event.get("extendedProperties", {}).get("shared", {})
        if shared.get("origin_calendar_id"):
            return shared["origin_calendar_id"]

        # First time seeing this event - source is origin
        return source_calendar_id

    def resolve_conflict(
        self,
        source_event: dict,
        dest_event: dict,
        mapping: EventMapping,
        source_calendar_id: str,
    ) -> str:
        """
        Resolve conflict when both source and dest have been modified.
        Uses "origin wins" strategy.

        Returns:
            "source_wins" or "dest_wins"
        """
        origin_calendar_id = mapping.origin_calendar_id

        # Origin wins strategy
        if origin_calendar_id == source_calendar_id:
            return "source_wins"
        else:
            return "dest_wins"

    def sync_calendars(
        self,
        sync_config_id: str,
        source_creds: Credentials,
        dest_creds: Credentials,
        source_calendar_id: str,
        dest_calendar_id: str,
        lookahead_days: int = 90,
        destination_color_id: Optional[str] = None,
        privacy_mode_enabled: bool = False,
        privacy_placeholder_text: str = "Personal appointment",
        sync_direction: str = "one_way",
        paired_config_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Main sync logic with bi-directional and privacy support.

        Args:
            sync_config_id: ID of the sync configuration
            source_creds: Google OAuth credentials for source calendar
            dest_creds: Google OAuth credentials for destination calendar
            source_calendar_id: Source calendar ID
            dest_calendar_id: Destination calendar ID
            lookahead_days: Number of days to sync ahead
            destination_color_id: Optional Google Calendar color ID to apply to all synced events
            privacy_mode_enabled: Whether to hide event details (keep only time)
            privacy_placeholder_text: Text to show instead of actual event details
            sync_direction: Sync direction ('one_way', 'bidirectional_a_to_b', 'bidirectional_b_to_a')
            paired_config_id: ID of paired config for bi-directional sync

        Returns:
            Dict with keys: created, updated, deleted
        """
        # Build Calendar API services
        service_src = build("calendar", "v3", credentials=source_creds, cache_discovery=False)
        service_dst = build("calendar", "v3", credentials=dest_creds, cache_discovery=False)

        # Calculate time window
        now = datetime.datetime.now(datetime.timezone.utc)
        time_min = iso_utc(now)
        time_max = iso_utc(now + datetime.timedelta(days=lookahead_days))

        # Fetch source events
        source_events = fetch_events(service_src, source_calendar_id, time_min, time_max)

        # Fetch destination events
        dest_events = fetch_events(service_dst, dest_calendar_id, time_min, time_max)

        # Build destination map by source_id
        # IMPORTANT: Exclude cancelled events so they get recreated if source still exists
        dest_map: Dict[str, dict] = {}
        for ev in dest_events:
            # Skip cancelled/deleted events - treat them as non-existent
            if ev.get("status") == "cancelled":
                continue

            shared = ev.get("extendedProperties", {}).get("shared", {})
            src_key = shared.get("source_id")
            if src_key:
                dest_map[src_key] = ev

        # Main sync loop with bi-directional support
        created = updated = deleted = 0
        for src in source_events:
            src_id = src.get("id")
            if not src_id:
                continue

            # LOOP PREVENTION: Skip if synced by system
            should_skip, skip_reason = self.should_skip_event(src, sync_config_id)
            if should_skip:
                continue  # Don't sync events created by sync system

            dest_match = dest_map.get(src_id)

            if src.get("status") == "cancelled":
                if dest_match:
                    try:
                        service_dst.events().delete(calendarId=dest_calendar_id, eventId=dest_match["id"]).execute()
                        deleted += 1
                    except HttpError as e:
                        # If event already deleted (404/410), that's fine - count it as deleted
                        if e.resp.status in [404, 410]:
                            deleted += 1
                        else:
                            # Re-raise other errors
                            raise
                    # Remove event mapping
                    self.db.query(EventMapping).filter(
                        EventMapping.sync_config_id == sync_config_id,
                        EventMapping.source_event_id == src_id
                    ).delete()
                continue

            # Get existing mapping
            mapping = self.db.query(EventMapping).filter(
                EventMapping.sync_config_id == sync_config_id,
                EventMapping.source_event_id == src_id
            ).first()

            # Determine origin calendar
            origin_calendar_id = self.get_origin_calendar_id(src, mapping, source_calendar_id)

            # Get or create sync_cluster_id
            sync_cluster_id = str(mapping.sync_cluster_id) if mapping else str(uuid.uuid4())
            dest_event_id = dest_match["id"] if dest_match else None

            # Build payload with all metadata
            payload = build_payload_from_source(
                src,
                sync_cluster_id=sync_cluster_id,
                dest_event_id=dest_event_id,
                destination_color_id=destination_color_id,
                origin_calendar_id=origin_calendar_id,
                sync_config_id=sync_config_id,
                privacy_mode_enabled=privacy_mode_enabled,
                privacy_placeholder_text=privacy_placeholder_text,
            )

            if dest_match:
                # CONFLICT RESOLUTION: Check if both sides modified
                if mapping:
                    src_modified = datetime.datetime.fromisoformat(src["updated"].replace("Z", "+00:00")) if src.get("updated") else None
                    dest_modified = datetime.datetime.fromisoformat(dest_match["updated"].replace("Z", "+00:00")) if dest_match.get("updated") else None

                    # Ensure mapping timestamps are timezone-aware for comparison (SQLite may return naive)
                    mapping_src_modified = mapping.source_last_modified
                    if mapping_src_modified and mapping_src_modified.tzinfo is None:
                        mapping_src_modified = mapping_src_modified.replace(tzinfo=datetime.timezone.utc)

                    mapping_dest_modified = mapping.dest_last_modified
                    if mapping_dest_modified and mapping_dest_modified.tzinfo is None:
                        mapping_dest_modified = mapping_dest_modified.replace(tzinfo=datetime.timezone.utc)

                    # Both modified since last sync?
                    if (mapping_src_modified and src_modified and src_modified > mapping_src_modified and
                        mapping_dest_modified and dest_modified and dest_modified > mapping_dest_modified):

                        # CONFLICT! Use origin wins strategy
                        winner = self.resolve_conflict(src, dest_match, mapping, source_calendar_id)

                        if winner == "dest_wins":
                            # Destination is origin and wins - don't update from source
                            continue
                        # else: source_wins - proceed with update

                if events_differ(payload, dest_match):
                    try:
                        result = service_dst.events().update(
                            calendarId=dest_calendar_id,
                            eventId=dest_match["id"],
                            body=payload,
                            sendUpdates="none",
                        ).execute()
                        updated += 1

                        # Update event mapping
                        if mapping:
                            mapping.content_hash = compute_content_hash(src)
                            mapping.last_synced_at = datetime.datetime.now(datetime.timezone.utc)
                            mapping.source_last_modified = datetime.datetime.fromisoformat(src["updated"].replace("Z", "+00:00")) if src.get("updated") else None
                            mapping.dest_last_modified = datetime.datetime.fromisoformat(result["updated"].replace("Z", "+00:00"))
                            if not mapping.origin_calendar_id:
                                mapping.origin_calendar_id = origin_calendar_id
                            mapping.is_privacy_mode = privacy_mode_enabled
                    except HttpError as e:
                        # Handle 410 (Gone) or 404 (Not Found) - event was deleted on Google's side
                        if e.resp.status in [404, 410]:
                            # Remove the mapping since the destination event no longer exists
                            if mapping:
                                self.db.delete(mapping)
                            # Recreate the event
                            try:
                                result = service_dst.events().insert(
                                    calendarId=dest_calendar_id,
                                    body=payload,
                                    sendUpdates="none",
                                ).execute()
                                created += 1

                                # Create new event mapping
                                new_mapping = EventMapping(
                                    sync_config_id=sync_config_id,
                                    source_event_id=src_id,
                                    dest_event_id=result["id"],
                                    sync_cluster_id=uuid.UUID(sync_cluster_id),
                                    content_hash=compute_content_hash(src),
                                    last_synced_at=datetime.datetime.now(datetime.timezone.utc),
                                    source_last_modified=datetime.datetime.fromisoformat(src["updated"].replace("Z", "+00:00")) if src.get("updated") else None,
                                    dest_last_modified=datetime.datetime.fromisoformat(result["updated"].replace("Z", "+00:00")),
                                    origin_calendar_id=origin_calendar_id,
                                    is_privacy_mode=privacy_mode_enabled,
                                )
                                self.db.add(new_mapping)
                            except HttpError:
                                # If recreate also fails, skip this event
                                pass
                        else:
                            # Re-raise other HTTP errors
                            raise
            else:
                try:
                    result = service_dst.events().insert(
                        calendarId=dest_calendar_id,
                        body=payload,
                        sendUpdates="none",
                    ).execute()
                    created += 1

                    # Create event mapping with origin tracking
                    new_mapping = EventMapping(
                        sync_config_id=sync_config_id,
                        source_event_id=src_id,
                        dest_event_id=result["id"],
                        sync_cluster_id=uuid.UUID(sync_cluster_id),
                        content_hash=compute_content_hash(src),
                        last_synced_at=datetime.datetime.now(datetime.timezone.utc),
                        source_last_modified=datetime.datetime.fromisoformat(src["updated"].replace("Z", "+00:00")) if src.get("updated") else None,
                        dest_last_modified=datetime.datetime.fromisoformat(result["updated"].replace("Z", "+00:00")),
                        origin_calendar_id=origin_calendar_id,
                        is_privacy_mode=privacy_mode_enabled,
                    )
                    self.db.add(new_mapping)
                except HttpError as e:
                    # Log and skip events that fail to insert
                    if e.resp.status not in [404, 410]:
                        # Re-raise non-404/410 errors
                        raise

        self.db.commit()

        return {
            "created": created,
            "updated": updated,
            "deleted": deleted,
        }
