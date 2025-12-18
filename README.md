# Calendar Sync (Dual Account)

One-way synchronization of Google Calendar events between two different Google accounts. Designed for native Python execution with infrastructure-as-code setup via Terraform.

## How it works

- Uses Google Calendar API with separate OAuth flows for each account
- Syncs events from SOURCE calendar (christian@livelyapps.com) to DEST calendar (a specific calendar owned by koch.chris@gmail.com)
- Each synced event stores `source_id` in extended properties for idempotent updates
- Cancelled source events delete their synced counterpart
- Only syncs future events (default: now → 90 days)

## Prerequisites

- Python 3.12+
- Terraform
- GCP project `cal-sync-481621`

## Setup (One-time)

### 1. Provision OAuth Infrastructure

```bash
terraform init
terraform apply
```

This creates:
- OAuth consent screen
- OAuth client ID (Desktop app)
- Enables Calendar API

### 2. Download Credentials

```bash
terraform output -raw client_secret > creds/source/credentials.json
terraform output -raw client_secret > creds/dest/credentials.json
```

### 3. Install Python Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure Calendar IDs

Create `.env` file:
```bash
SOURCE_CALENDAR_ID=christian@livelyapps.com
DEST_CALENDAR_ID=4bd46f6a8fb2f581fb9a8dc0a5d5a4fae4f339d5d10ae1e1226cf0e239674038@group.calendar.google.com
SYNC_LOOKAHEAD_DAYS=90
```

**Note:** The destination is a specific calendar (group calendar) owned by the koch.chris@gmail.com account.

### 5. Authenticate Both Calendars

```bash
python auth.py
```

This opens two browser windows sequentially:
1. Authenticate as christian@livelyapps.com (for source calendar access)
2. Authenticate as koch.chris@gmail.com (for destination calendar access)

Tokens are saved to:
- `creds/source/token.json`
- `creds/dest/token.json`

## Usage

### Sync Calendars

```bash
python sync.py
```

Syncs all events from source → destination for the next 90 days.

### Re-authenticate (when tokens expire)

```bash
python auth.py
```

### Run Tests

```bash
pytest test_sync.py -v
```

## Project Structure

```
cal-sync/
├── main.tf              # Terraform infrastructure (OAuth, API, consent screen)
├── auth.py              # Dual OAuth authentication script
├── sync.py              # Main sync logic
├── test_sync.py         # Unit tests with mocked API calls
├── requirements.txt     # Python dependencies
├── .env                 # Calendar IDs configuration
├── .gitignore           # Excludes credentials, tokens, Terraform state
└── creds/
    ├── source/
    │   ├── credentials.json  # OAuth client (from Terraform)
    │   └── token.json        # Access/refresh token (from auth.py)
    └── dest/
        ├── credentials.json  # Same OAuth client
        └── token.json        # Separate access/refresh token
```

## Architecture

### Dual OAuth Design

Same OAuth client ID, two separate authentications:
- `creds/source/credentials.json` → authenticate as christian@livelyapps.com → `token.json` (accesses source calendar)
- `creds/dest/credentials.json` → authenticate as koch.chris@gmail.com → `token.json` (accesses destination group calendar)

Two independent service objects:
- `service_src` (reads from source calendar)
- `service_dst` (writes to destination calendar)

### Idempotent Sync

Events are tracked via `extendedProperties.shared.source_id`:
- Create: Source event not in destination → insert with `source_id`
- Update: Source event changed → update destination event with matching `source_id`
- Delete: Source event cancelled → delete destination event with matching `source_id`
- Skip: Source event unchanged → no API call

## What Gets Synced

**Copied fields:**
- Summary, description, location
- Start/end times
- Recurrence rules
- Transparency, visibility, colorId

**Not copied:**
- Attendees
- Attachments
- Reminders (disabled on synced events)

## Limitations

- One-way sync only (source → destination)
- Future events only (configurable via `SYNC_LOOKAHEAD_DAYS`)
- Manual execution (no automatic scheduling included)
- Calendars must belong to different isolated Google accounts
