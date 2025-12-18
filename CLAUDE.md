# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python script that synchronizes Google Calendar events from christian@livelyapps.com to a specific calendar (4bd46f6a...@group.calendar.google.com) owned by koch.chris@gmail.com using dual OAuth flows. Infrastructure provisioned via Terraform.

## Development Commands

```bash
# Setup
terraform init && terraform apply
terraform output -raw client_secret > creds/source/credentials.json
terraform output -raw client_secret > creds/dest/credentials.json
pip install -r requirements.txt
python auth.py

# Sync
python sync.py

# Test
pytest test_sync.py -v

# Re-authenticate
python auth.py
```

## Architecture

### Dual OAuth Flow

**Key Innovation:** Single OAuth client ID used for two separate authentications.

```
main.tf provisions:
├── OAuth consent screen (external, calendar scope)
├── OAuth client ID (Desktop app: calendar-sync-client)
└── Google Calendar API enabled

OAuth client exported twice:
├── creds/source/credentials.json  (same client)
└── creds/dest/credentials.json    (same client)

Authentication (auth.py):
├── Flow 1: christian@livelyapps.com → creds/source/token.json
└── Flow 2: koch.chris@gmail.com → creds/dest/token.json

Sync (sync.py):
├── service_src = build(creds_src)  # Reads source calendar
└── service_dst = build(creds_dst)  # Writes dest calendar
```

**Why same credentials.json?** The OAuth client defines the "application" requesting access. When users authenticate, they grant the application access to THEIR calendar. Same app, different users, different tokens.

### Idempotent Sync Mechanism

Located in [sync.py:68-87](sync.py#L68-L87) and [sync.py:131-160](sync.py#L131-L160).

**Core Pattern:**
1. Fetch all source and destination events for time window
2. Index destination events by `extendedProperties.shared.source_id`
3. For each source event:
   - If cancelled → delete destination event with matching `source_id`
   - If `source_id` exists in destination:
     - Compare event fields
     - Update only if changed
   - If `source_id` doesn't exist → create new event with `source_id`

**Extended Property Structure:**
```python
"extendedProperties": {
    "shared": {
        "source_id": "original_event_id_from_source_calendar"
    }
}
```

This allows unlimited re-runs without duplicates. The `source_id` is the foreign key linking destination events back to their source.

### Event Comparison

[sync.py:90-106](sync.py#L90-L106) defines comparable fields:
- summary, description, location
- start, end, recurrence
- transparency, visibility, colorId
- reminders

Only these fields trigger updates. Metadata (etag, updated, id) is ignored.

### Time Window Behavior

[sync.py:109-111](sync.py#L109-L111) sets sync window:
```python
now = datetime.datetime.now(datetime.timezone.utc)
time_min = iso_utc(now)
time_max = iso_utc(now + timedelta(days=SYNC_LOOKAHEAD_DAYS))
```

Default: now → 90 days. Past events never synced or modified.

### Credential Loading

[sync.py:14-28](sync.py#L14-L28) loads credentials from directories:
- Checks for `token.json` existence
- Auto-refreshes expired tokens with refresh_token
- Fails with helpful message if token missing/invalid
- No OAuth flow in sync.py (moved to auth.py)

## File Structure

**Infrastructure:**
- [main.tf](main.tf) - Single-file Terraform (OAuth client, consent screen, Calendar API)

**Python Scripts:**
- [auth.py](auth.py) - Interactive dual OAuth authentication (run once, or when tokens expire)
- [sync.py](sync.py) - Main sync logic with dual service architecture (~165 lines)
- [test_sync.py](test_sync.py) - Unit tests with mocked API calls

**Configuration:**
- [.env](.env) - Calendar IDs and sync window (not in repo, see [.gitignore](.gitignore))
- [requirements.txt](requirements.txt) - Python dependencies including pytest

**Credentials (gitignored):**
- `creds/source/` - OAuth client + token for christian@livelyapps.com (accesses source calendar)
- `creds/dest/` - Same OAuth client + separate token for koch.chris@gmail.com (accesses destination group calendar)

## Terraform Infrastructure

[main.tf](main.tf) provisions GCP resources:

```hcl
google_project_service.calendar_api       # Enables calendar-json.googleapis.com
google_iap_brand.project_brand            # OAuth consent screen
google_iap_client.calendar_sync_client    # OAuth client ID (Desktop app)
output.client_secret                      # JSON for credentials.json
```

**Output format:** Complete OAuth client JSON compatible with `google-auth-oauthlib`:
```json
{
  "installed": {
    "client_id": "...",
    "client_secret": "...",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    ...
  }
}
```

## Testing

[test_sync.py](test_sync.py) uses pytest with mocked Google Calendar API:

**Test Categories:**
1. `TestBuildPayloadFromSource` - Event transformation logic
2. `TestEventsDiffer` - Change detection
3. `TestLoadCredentialsFromDir` - Credential loading, refresh, errors
4. `TestFetchEventsPagination` - API pagination handling
5. `TestSyncScenarios` - End-to-end sync with mocked services

**No real API calls.** All Google Calendar API interactions use `unittest.mock.Mock`.

Run: `pytest test_sync.py -v`

## Key Constraints

- **One-way sync only:** Changes in destination are overwritten
- **No attendees/attachments:** Only basic event fields copied
- **Future events only:** Historical events ignored
- **No conflict resolution:** Destination always matches source
- **Sequential OAuth flows:** auth.py prompts between authentications
- **Manual execution:** No built-in scheduling (use cron/systemd externally)

## Common Development Tasks

**Add new syncable field:**
1. Add to `build_payload_from_source()` [sync.py:68-87](sync.py#L68-L87)
2. Add to `comparable_keys` in `events_differ()` [sync.py:91-102](sync.py#L91-L102)
3. Add test in [test_sync.py](test_sync.py)

**Change OAuth scopes:**
1. Update `SCOPES` in [auth.py](auth.py) and [sync.py](sync.py)
2. Update Terraform consent screen scopes in [main.tf](main.tf)
3. Re-run `terraform apply` and `python auth.py`

**Debug sync issues:**
1. Check token validity: `python auth.py`
2. Verify calendar IDs in [.env](.env)
3. Check extended properties on destination events for `source_id`
4. Run sync with print statements to see event comparison logic

## Why Dual OAuth (Not Calendar Sharing)?

User confirmed calendars must stay isolated. Cannot use calendar sharing because:
- Source (christian@livelyapps.com) doesn't share calendar with destination
- Destination (koch.chris@gmail.com) doesn't have write access to source
- Separate OAuth flows allow reading from one account, writing to another
