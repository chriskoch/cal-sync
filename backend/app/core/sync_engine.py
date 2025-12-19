import datetime
import hashlib
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from googleapiclient.discovery import build
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


def build_payload_from_source(src: dict, sync_cluster_id: Optional[str] = None, dest_event_id: Optional[str] = None) -> dict:
    """Build event payload from source event (preserved from sync.py:58-77 + Story 3 enhancements)."""
    extended_props = {
        "source_id": src.get("id"),
    }

    # Story 3: Add bidirectional tracking metadata
    if sync_cluster_id:
        extended_props["sync_cluster_id"] = sync_cluster_id
        extended_props["last_sync_timestamp"] = iso_utc(datetime.datetime.now(datetime.timezone.utc))
        extended_props["sync_direction"] = "source_to_dest"
        if dest_event_id:
            extended_props["dest_event_id"] = dest_event_id

    body = {
        "summary": src.get("summary"),
        "description": src.get("description"),
        "location": src.get("location"),
        "start": src.get("start"),
        "end": src.get("end"),
        "recurrence": src.get("recurrence"),
        "transparency": src.get("transparency"),
        "visibility": src.get("visibility"),
        "colorId": src.get("colorId"),
        "reminders": {"useDefault": False},  # avoid noisy notifications
        "extendedProperties": {
            "shared": extended_props
        },
    }
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

    def sync_calendars(
        self,
        sync_config_id: str,
        source_creds: Credentials,
        dest_creds: Credentials,
        source_calendar_id: str,
        dest_calendar_id: str,
        lookahead_days: int = 90,
    ) -> Dict[str, int]:
        """
        Main sync logic (preserved from sync.py:99-165).

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
        dest_map: Dict[str, dict] = {}
        for ev in dest_events:
            shared = ev.get("extendedProperties", {}).get("shared", {})
            src_key = shared.get("source_id")
            if src_key:
                dest_map[src_key] = ev

        # Main sync loop (preserved from sync.py:131-160)
        created = updated = deleted = 0
        for src in source_events:
            src_id = src.get("id")
            if not src_id:
                continue
            dest_match = dest_map.get(src_id)

            if src.get("status") == "cancelled":
                if dest_match:
                    service_dst.events().delete(calendarId=dest_calendar_id, eventId=dest_match["id"]).execute()
                    deleted += 1
                    # Remove event mapping
                    self.db.query(EventMapping).filter(
                        EventMapping.sync_config_id == sync_config_id,
                        EventMapping.source_event_id == src_id
                    ).delete()
                continue

            # Get or create sync_cluster_id
            mapping = self.db.query(EventMapping).filter(
                EventMapping.sync_config_id == sync_config_id,
                EventMapping.source_event_id == src_id
            ).first()

            sync_cluster_id = str(mapping.sync_cluster_id) if mapping else str(uuid.uuid4())
            dest_event_id = dest_match["id"] if dest_match else None

            payload = build_payload_from_source(src, sync_cluster_id, dest_event_id)

            if dest_match:
                if events_differ(payload, dest_match):
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
                        mapping.dest_last_modified = datetime.datetime.fromisoformat(result["updated"].replace("Z", "+00:00"))
            else:
                result = service_dst.events().insert(
                    calendarId=dest_calendar_id,
                    body=payload,
                    sendUpdates="none",
                ).execute()
                created += 1

                # Create event mapping
                new_mapping = EventMapping(
                    sync_config_id=sync_config_id,
                    source_event_id=src_id,
                    dest_event_id=result["id"],
                    sync_cluster_id=uuid.UUID(sync_cluster_id),
                    content_hash=compute_content_hash(src),
                    last_synced_at=datetime.datetime.now(datetime.timezone.utc),
                    source_last_modified=datetime.datetime.fromisoformat(src["updated"].replace("Z", "+00:00")) if src.get("updated") else None,
                    dest_last_modified=datetime.datetime.fromisoformat(result["updated"].replace("Z", "+00:00"))
                )
                self.db.add(new_mapping)

        self.db.commit()

        return {
            "created": created,
            "updated": updated,
            "deleted": deleted,
        }
