import datetime
import os
from typing import Dict, List

from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def load_credentials_from_dir(creds_dir: str) -> Credentials:
    """Load credentials from a specific directory."""
    token_path = os.path.join(creds_dir, "token.json")
    if not os.path.exists(token_path):
        raise SystemExit(f"Token not found at {token_path}. Run auth.py first.")

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        else:
            raise SystemExit(f"Invalid token at {token_path}. Run auth.py again.")
    return creds


def iso_utc(dt: datetime.datetime) -> str:
    return dt.replace(microsecond=0, tzinfo=None).isoformat() + "Z"


def fetch_events(service, calendar_id: str, time_min: str, time_max: str) -> List[dict]:
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


def build_payload_from_source(src: dict) -> dict:
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
            "shared": {
                "source_id": src.get("id"),
            }
        },
    }
    # Remove None entries the Calendar API dislikes.
    return {k: v for k, v in body.items() if v is not None}


def events_differ(src_body: dict, dest_event: dict) -> bool:
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


def main():
    load_dotenv()

    source_id = os.getenv("SOURCE_CALENDAR_ID")
    dest_id = os.getenv("DEST_CALENDAR_ID")
    if not source_id or not dest_id:
        raise SystemExit("SOURCE_CALENDAR_ID and DEST_CALENDAR_ID env vars are required.")

    lookahead_days = int(os.getenv("SYNC_LOOKAHEAD_DAYS", "90"))

    now = datetime.datetime.now(datetime.timezone.utc)
    time_min = iso_utc(now)
    time_max = iso_utc(now + datetime.timedelta(days=lookahead_days))

    creds_src = load_credentials_from_dir("creds/source")
    creds_dst = load_credentials_from_dir("creds/dest")
    service_src = build("calendar", "v3", credentials=creds_src, cache_discovery=False)
    service_dst = build("calendar", "v3", credentials=creds_dst, cache_discovery=False)

    print(f"Fetching source events from {source_id}...")
    source_events = fetch_events(service_src, source_id, time_min, time_max)
    print(f"Found {len(source_events)} source events in window.")

    print(f"Fetching destination events from {dest_id}...")
    dest_events = fetch_events(service_dst, dest_id, time_min, time_max)
    dest_map: Dict[str, dict] = {}
    for ev in dest_events:
        shared = ev.get("extendedProperties", {}).get("shared", {})
        src_key = shared.get("source_id")
        if src_key:
            dest_map[src_key] = ev

    created = updated = deleted = 0
    for src in source_events:
        src_id = src.get("id")
        if not src_id:
            continue
        dest_match = dest_map.get(src_id)

        if src.get("status") == "cancelled":
            if dest_match:
                service_dst.events().delete(calendarId=dest_id, eventId=dest_match["id"]).execute()
                deleted += 1
            continue

        payload = build_payload_from_source(src)
        if dest_match:
            if events_differ(payload, dest_match):
                service_dst.events().update(
                    calendarId=dest_id,
                    eventId=dest_match["id"],
                    body=payload,
                    sendUpdates="none",
                ).execute()
                updated += 1
        else:
            service_dst.events().insert(
                calendarId=dest_id,
                body=payload,
                sendUpdates="none",
            ).execute()
            created += 1

    print(
        f"Done. Created: {created}, Updated: {updated}, Deleted: {deleted}. "
        f"Window: now → {lookahead_days} days."
    )


if __name__ == "__main__":
    main()
