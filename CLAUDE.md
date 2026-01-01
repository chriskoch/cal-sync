# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack web application that synchronizes Google Calendar events between multiple calendar accounts. Users can configure multiple sync pairs, each syncing events from a source calendar to a destination calendar with customizable color schemes.

**Stack:**
- **Backend**: FastAPI (Python) with PostgreSQL database
- **Frontend**: React + TypeScript + Material-UI
- **Infrastructure**: Docker Compose for local development
- **Authentication**: Dual OAuth 2.0 flows for source and destination Google accounts

## Development Commands

```bash
# Start all services (PostgreSQL, backend, frontend)
docker compose up

# Run backend tests
docker compose exec backend pytest

# Run database migrations
docker compose exec backend alembic upgrade head

# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Stop all services
docker compose down
```

## Architecture

### Web Application Structure

```
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints (auth, oauth, calendars, sync)
│   │   ├── core/          # Business logic (sync_engine)
│   │   ├── models/        # SQLAlchemy models
│   │   ├── migrations/    # Alembic database migrations
│   │   └── database.py    # Database configuration
│   ├── tests/             # Backend tests
│   └── Dockerfile         # Backend container
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components (Dashboard, Login, Register)
│   │   ├── services/      # API client
│   │   └── context/       # React context (AuthContext)
│   └── Dockerfile         # Frontend container
└── docker-compose.yml     # Multi-container orchestration
```

### Google OAuth-Only Authentication

**Key Innovation:** Google OAuth is used for both user authentication and calendar access. The registered Google account automatically becomes the source account.

```
User Authentication Flow:
1. User clicks "Sign in with Google" on login page
2. Google OAuth flow initiates (account_type: "register")
3. After OAuth callback:
   - If new user: Creates user record (email from Google, no password)
   - Creates source OAuth token automatically (account_type: "source")
   - Generates JWT token for API authentication
   - Redirects to dashboard with JWT token
4. User connects destination Google account (OAuth flow #2)
   → Stores separate OAuth tokens in database (account_type: "destination")
5. User creates sync configurations linking source → destination calendars
```

**Database Schema:**
- `users`: User accounts (email from Google OAuth, no passwords)
- `oauth_tokens`: OAuth tokens per user per account_type (source/destination)
- `sync_configs`: Calendar sync configurations (source_calendar_id, dest_calendar_id, settings)
- `sync_logs`: Sync execution history (events created/updated/deleted, status, errors)
- `event_mappings`: Links source events to destination events via source_id

### Idempotent Sync Engine

Located in [backend/app/core/sync_engine.py](backend/app/core/sync_engine.py).

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

**Error Handling:**
- 410 (Gone) errors: Event already deleted, skip gracefully
- 404 (Not Found) errors: Event doesn't exist, skip or recreate
- All errors logged to sync_logs table

### Event Color Customization

**Google Calendar Color System:**
- **Calendar colors**: 24 colors (IDs 1-24) - for calendar backgrounds
- **Event colors**: 11 colors (IDs 1-11) - for individual events

**Implementation:**
- Users can select destination event color from 11 valid event colors
- Source calendar color is auto-selected if valid (IDs 1-11)
- Out-of-range calendar colors (12-24) default to Lavender (ID 1)
- "Same as source" option preserves source event's original color

**Color Palette:**
```typescript
1: Lavender (#7986cb)
2: Sage (#33b679)
3: Grape (#8e24aa)
4: Flamingo (#e67c73)
5: Banana (#f6c026)
6: Tangerine (#f5511d)
7: Peacock (#039be5)
8: Graphite (#616161)
9: Blueberry (#3f51b5)
10: Basil (#0b8043)
11: Tomato (#d60000)
```

### Event Comparison

[sync_engine.py](backend/app/core/sync_engine.py) defines comparable fields:
- summary, description, location
- start, end, recurrence
- transparency, visibility, colorId
- reminders

Only these fields trigger updates. Metadata (etag, updated, id) is ignored.

### Time Window Behavior

Default sync window: **now → 90 days** (configurable per sync config).
Past events are never synced or modified.

## API Endpoints

### Authentication
- `GET /auth/me` - Get current user info

### OAuth
- `GET /oauth/start/{account_type}` - Initiate OAuth flow
  - `account_type`: "register" (no auth required), "source" (auth required), "destination" (auth required)
  - For "register": Creates user + source OAuth token, returns JWT via redirect
- `GET /oauth/callback` - OAuth callback handler
  - Handles registration (creates user + source token) or connects source/destination
  - For registration: Generates JWT and redirects to frontend with token in URL
- `GET /oauth/status` - Check OAuth connection status

### Calendars
- `GET /calendars/{account_type}/list` - List available calendars (includes color_id)
- `POST /calendars/{account_type}/events/create` - Create event (for testing)
- `POST /calendars/{account_type}/events/update` - Update event (for testing)
- `POST /calendars/{account_type}/events/delete` - Delete event (for testing)
- `POST /calendars/{account_type}/events/list` - List events with filters (for testing)

### Sync Configuration
- `POST /sync/config` - Create sync configuration
- `GET /sync/config` - List user's sync configurations
- `DELETE /sync/config/{config_id}` - Delete sync configuration
- `POST /sync/trigger/{config_id}` - Manually trigger sync
- `GET /sync/logs/{config_id}` - Get sync history

## Database Models

### SyncConfig
```python
- source_calendar_id: str
- dest_calendar_id: str
- sync_lookahead_days: int (default: 90)
- destination_color_id: str | None  # Event color ID (1-11)
- is_active: bool
- last_synced_at: datetime | None
```

### SyncLog
```python
- sync_config_id: UUID
- events_created: int
- events_updated: int
- events_deleted: int
- status: str (running|success|failed)
- error_message: str | None
- sync_window_start: datetime
- sync_window_end: datetime
- started_at: datetime
- completed_at: datetime | None
```

## Frontend Components

### Key Components
- **Dashboard**: Main page showing OAuth status and sync configurations
- **SyncConfigForm**: Create sync configuration with calendar selection and color picker
- **CalendarSelector**: Dropdown to select source/destination calendars
- **SyncHistoryDialog**: Modal showing sync execution history

### State Management
- React Context for authentication (AuthContext)
- Component-level state for sync configurations and UI state

## Testing

### Backend Tests
```bash
# Run all tests
docker compose exec backend pytest -v

# Run tests in parallel (faster)
docker compose exec backend pytest -n auto

# Run with coverage
docker compose exec backend pytest --cov=app --cov-report=html
```

**Test Coverage:**
- **101 unit/integration tests** with 100% pass rate
- sync_engine.py: 95% coverage (42 tests)
- API endpoints: 99% coverage (51 tests - auth, oauth, sync, calendars)
- E2E integration tests: 8 tests with real OAuth tokens
- Error handling: 410/404 errors, authentication failures, UUID type correctness

**Test Categories:**
1. Sync engine: Event creation, updates, deletions, error handling, bi-directional sync
2. OAuth API: Authorization flow, token storage, status checks, registration
3. Sync API: Configuration CRUD, manual triggers, history, bi-directional pairs
4. Auth API: JWT token validation (OAuth-only, no password auth)
5. Security: Token encryption, JWT validation
6. E2E Integration: Real OAuth token flows, UUID type handling

**Test Optimizations:**
- Session-scoped database fixtures (3-5x faster)
- Shared mock fixtures for OAuth and Google Calendar API
- Parallel execution support via pytest-xdist
- Test utilities for common operations

### Frontend Tests
```bash
cd frontend
npm test          # Run tests in watch mode
npm test -- --run # Run tests once
```

**Test Setup:**
- Vitest for test runner
- React Testing Library for component testing
- TypeScript type checking
- ESLint for code quality

### Frontend
- React components with TypeScript type checking
- Material-UI for consistent UI/UX
- ESLint configured with TypeScript support

## Key Features

- **Multi-user support**: Each user has separate OAuth tokens and sync configurations
- **Multiple sync pairs**: Users can configure multiple source → destination pairs
- **Custom colors**: Choose event colors for destination calendar
- **Manual sync triggers**: Trigger syncs on-demand via UI
- **Sync history**: View past sync executions with detailed statistics
- **Error resilience**: Gracefully handles deleted events and API errors
- **Idempotent syncs**: Unlimited re-runs without duplicates
- **Containerized**: Docker Compose for easy local development

## E2E Testing Scripts

The repository includes comprehensive E2E test scripts for real Google Calendar API testing located in `backend/tests/e2e/`:

```bash
# All scripts require an access token from the /auth/me endpoint
# Get token: Login to app → Browser dev tools → localStorage → copy JWT token

# One-way sync test (create, rename, move, delete)
python3 backend/tests/e2e/e2e_test_auto.py <ACCESS_TOKEN>

# Bi-directional sync test (multiple events, both directions)
python3 backend/tests/e2e/e2e_test_bidirectional.py <ACCESS_TOKEN>

# Edge case: Delete synced event and resync (idempotency test)
python3 backend/tests/e2e/e2e_test_delete_synced.py <ACCESS_TOKEN>

# Recurring events test (with edge case documentation)
python3 backend/tests/e2e/e2e_test_recurring.py <ACCESS_TOKEN>
```

**Test Scripts:**
- `backend/tests/e2e/e2e_test_auto.py` - Fully automated one-way sync testing
- `backend/tests/e2e/e2e_test_bidirectional.py` - Bi-directional sync with multiple events
- `backend/tests/e2e/e2e_test_delete_synced.py` - Tests sync idempotency after manual deletion
- `backend/tests/e2e/e2e_test_recurring.py` - Recurring event handling with edge cases

All scripts use calendars `test-4` and `test-5` by default and include automatic cleanup.

## Recent Bug Fixes & Stability Improvements

### Bug Fix 1: UUID Type Mismatch in Sync Trigger (Jan 2026)
**Location:** `backend/app/api/sync.py:229-230`

**Problem:** Sync trigger endpoint was converting `current_user.id` (UUID object) to string before passing to `get_credentials_from_db()`, causing OAuth credential lookups to fail. All syncs were broken.

**Fix:** Removed `str()` wrapper - PostgreSQL UUID columns work with UUID objects directly.

```python
# BEFORE (broken):
source_creds = get_credentials_from_db(str(current_user.id), "source", db)

# AFTER (fixed):
source_creds = get_credentials_from_db(current_user.id, "source", db)
```

**Impact:** Restored all sync functionality (one-way and bi-directional).

**Tests Added:** 8 E2E integration tests verifying UUID type handling in `backend/tests/test_sync_integration_e2e.py`

### Bug Fix 2: Sync Engine Not Idempotent for Deleted Events (Jan 2026)
**Location:** `backend/app/core/sync_engine.py:254-259`

**Problem:** When users manually deleted synced events from destination calendar, the sync engine would not recreate them on next sync. The engine was including cancelled events (status: "cancelled") in the destination map, treating deleted events as "existing".

**Fix:** Added status check to exclude cancelled events from destination map.

```python
# Build destination map by source_id
dest_map: Dict[str, dict] = {}
for ev in dest_events:
    # Skip cancelled/deleted events - treat them as non-existent
    if ev.get("status") == "cancelled":
        continue

    shared = ev.get("extendedProperties", {}).get("shared", {})
    src_key = shared.get("source_id")
    if src_key:
        dest_map[src_key] = ev
```

**Impact:** Restored true idempotency - sync now correctly recreates manually deleted synced events.

**Tests Added:** `e2e_test_delete_synced.py` - 5-step edge case test validating idempotency.

### Known Limitations: Recurring Events
**Status:** Documented, not blocking

The backend test helper endpoints (`POST /calendars/{type}/events/*`) have limitations with recurring events:

1. **Cannot create events with recurrence rules** - Requires RRULE syntax support
2. **Cannot modify single instances** - Requires instance-specific API access
3. **Cannot delete single instances** - Requires instance-specific EXDATE handling

**Workaround:** Use manual Google Calendar UI or direct Google Calendar API for recurring event testing.

**Documentation:** See `e2e_test_recurring.py` for 8 documented edge cases and API extension recommendations.

## Common Development Tasks

### Add new syncable event field
1. Update `build_payload_from_source()` in [sync_engine.py](backend/app/core/sync_engine.py)
2. Add to `comparable_keys` in `events_differ()` in same file
3. Add test in [backend/tests/test_sync_engine.py](backend/tests/test_sync_engine.py)

### Add new API endpoint
1. Create router function in appropriate file under [backend/app/api/](backend/app/api/)
2. Add request/response Pydantic models
3. Add authentication dependency if needed: `current_user: User = Depends(get_current_user)`
4. Add tests in [backend/tests/](backend/tests/)
5. Run linters: `cd frontend && npm run lint` and check backend with IDE linter

### Add new database column
1. Modify SQLAlchemy model in [backend/app/models/](backend/app/models/)
2. Generate migration: `docker compose exec backend alembic revision --autogenerate -m "description"`
3. Review and edit migration in [backend/app/migrations/versions/](backend/app/migrations/versions/)
4. Apply migration: `docker compose exec backend alembic upgrade head`
5. Update Pydantic models in [backend/app/api/](backend/app/api/) if needed
6. Update frontend TypeScript interfaces in [frontend/src/services/api.ts](frontend/src/services/api.ts)

### Debug sync issues
1. Check sync logs in UI (Dashboard → View History)
2. Check database: `docker compose exec db psql -U postgres -d calsync`
3. Check backend logs: `docker compose logs backend`
4. Verify OAuth tokens are valid via `/oauth/status` endpoint
5. Check event extended properties for `source_id`

### Code Quality
```bash
# Frontend linting
cd frontend && npm run lint

# Frontend type checking
cd frontend && npm run build

# Backend tests
docker compose exec backend pytest -v

# All tests
docker compose exec backend pytest -v && cd frontend && npm test -- --run
```

## Architecture Decisions

### Why Dual OAuth (Not Calendar Sharing)?
- **Privacy**: Source and destination accounts remain completely isolated
- **Flexibility**: Users can sync between any two Google accounts they control
- **Granular control**: OAuth scopes limit access to calendar data only

### Why Web Application (Not CLI Script)?
- **Multi-user**: Support multiple users with separate configurations
- **User-friendly**: No command-line knowledge required
- **Persistent storage**: Database stores configurations, tokens, and history
- **Remote access**: Access from any device via web browser

### Why Event Colors (Not Calendar Colors)?
- Event colors (IDs 1-11) are the only colors that can be set on individual events
- Calendar colors (IDs 1-24) only affect calendar background, not events
- Synced events need individual colors, so we must use event colors

## Security Considerations

- **Google OAuth-only authentication**: No passwords stored or required
- **JWT tokens**: Short-lived access tokens (30 minutes) for API authentication
- **OAuth tokens**: Stored encrypted in database with Fernet, refreshed automatically
- **HTTPS required**: Production deployment must use HTTPS
- **CORS configured**: Frontend-backend communication restricted
- **Token encryption**: OAuth tokens encrypted before database storage
