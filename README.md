# Calendar Sync - Multi-tenant SaaS

Bi-directional and one-way synchronization of Google Calendar events between two different Google accounts. Web-based multi-tenant SaaS application with React + Material UI frontend and FastAPI backend.

**✅ Fully tested and stable** - 101 passing tests with comprehensive E2E coverage.

> **📋 See [CHANGELOG.md](CHANGELOG.md) for detailed version history and release notes**

## How it works

- Multi-tenant SaaS with Google OAuth-only authentication
- Registration and login via Google OAuth (registered Google account becomes Account 1)
- Web OAuth flow for connecting Account 2
- Calendar selection UI for choosing which calendars to sync
- **Bi-directional sync:** Events sync both ways between selected calendars
- **One-way sync:** Traditional source → destination syncing
- Each synced event stores `source_id` and bidirectional metadata in extended properties
- Idempotent sync mechanism - unlimited re-runs without duplicates
- Sync triggered manually via web dashboard (or scheduled via Cloud Scheduler in production)
- Only syncs future events (default: now → 90 days)

## Architecture

**Tech Stack:**
- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **Frontend:** React 18, TypeScript, Material UI 5, Vite
- **Infrastructure:** Terraform (GCP Cloud Run, Cloud SQL, Secret Manager)
- **OAuth:** Web Application flow (migrated from Desktop OOB)

**Database Schema:**
- `users` - User accounts (email from Google OAuth, no passwords)
- `oauth_tokens` - Encrypted Google OAuth tokens (Fernet encryption)
- `calendars` - Cached calendar lists from Google
- `sync_configs` - User sync configurations
- `sync_logs` - Sync history and statistics
- `event_mappings` - Bidirectional event tracking (Story 3)

## Prerequisites

- **Local Development:**
  - Python 3.12+
  - Node.js 18+
  - Docker and Docker Compose
  - Google Cloud project with OAuth client

- **Production Deployment:**
  - Terraform
  - GCP project with billing enabled

## Quick Start

```bash
# Clone repository
git clone <repository-url>
cd cal-sync

# Copy environment template
cp .env.example .env
# Edit .env with your OAuth credentials and secrets

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# Access application
# Frontend: http://localhost:3033
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Local Development Setup

### 1. Create OAuth Client in GCP Console

1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth consent screen:
   - User Type: External
   - App name: Calendar Sync
   - Scopes: Add `https://www.googleapis.com/auth/calendar`
   - Add test users (your Google accounts)
3. Create OAuth client ID:
   - Application type: **Web application**
   - Authorized redirect URIs: `http://localhost:8000/oauth/callback`
   - Download JSON credentials

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
# From OAuth client JSON
OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
OAUTH_CLIENT_SECRET=your-client-secret

# Generate secrets
JWT_SECRET=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(openssl rand -base64 32)

# Database (Docker Postgres)
DATABASE_URL=postgresql://postgres:dev@localhost:5433/calsync

# API URLs
API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3033
```

Frontend dev server uses `frontend/.env`:

```bash
VITE_API_URL=http://localhost:8000
```

### 3. Start PostgreSQL Database

```bash
docker run -d --name cal-sync-db \
  -e POSTGRES_PASSWORD=dev \
  -e POSTGRES_DB=calsync \
  -p 5433:5432 \
  postgres:15
```

Or use docker-compose:

```bash
docker-compose up -d db
```

### 4. Setup Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000

### 5. Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3033

### 6. Access the Application

1. Open http://localhost:3033
2. Sign in with Google (registration happens automatically)
3. Your Google account is automatically connected as the source account
4. Connect Destination Google account (OAuth flow)
5. Select calendars and create sync configuration
6. Trigger manual sync and view detailed results
7. View sync history with complete audit trail

## Usage

### Web Application

1. **User Registration/Login**
   - Navigate to http://localhost:3033/login
   - Click "Sign in with Google" → Google OAuth flow
   - Your Google account is automatically registered and connected as the source account
   - JWT token is stored for subsequent API requests

2. **Connect Destination Google Account**
   - Dashboard shows OAuth status cards
   - Source account is already connected (from registration)
   - Click "Connect Destination Account" → Google OAuth flow
   - Both accounts now show connected with email addresses

3. **Create Sync Configuration**
   - Select source calendar from dropdown (shows all accessible calendars)
   - Select destination calendar from dropdown
   - Set sync lookahead window (default: 90 days)
   - Click "Create Sync Configuration"
   - Configuration appears in "Active Sync Configurations" section

4. **Manage Syncs**
   - **Trigger Manual Sync:** Click "Trigger Sync Now" button
   - **View Results:** See detailed feedback (events created/updated/deleted)
   - **View History:** Click "View History" to see complete audit trail
   - **Delete Config:** Remove sync configuration with confirmation
   - **Refresh:** Update configuration list to see latest sync times

### API Endpoints

Backend API documentation: http://localhost:8000/docs

**Authentication:**
- `GET /auth/me` - Get current user

**OAuth:**
- `GET /oauth/start/{account_type}` - Initiate OAuth flow (account_type: "register", "source", or "destination")
- `GET /oauth/callback` - OAuth callback handler (creates user + source token for registration)
- `GET /oauth/status` - Check connection status

**Calendars:**
- `GET /calendars/{account_type}/list` - List available calendars
- `POST /calendars/{account_type}/events/create` - Create event (for E2E testing)
- `POST /calendars/{account_type}/events/update` - Update event (for E2E testing)
- `POST /calendars/{account_type}/events/delete` - Delete event (for E2E testing)
- `POST /calendars/{account_type}/events/list` - List events with filters (for E2E testing)

**Sync:**
- `POST /sync/config` - Create sync configuration (supports bi-directional)
- `GET /sync/config` - List user's sync configs
- `DELETE /sync/config/{config_id}` - Delete sync configuration
- `POST /sync/trigger/{config_id}` - Trigger manual sync (supports trigger_both_directions parameter)
- `GET /sync/logs/{config_id}` - View sync history

## Project Structure

```
cal-sync/
├── backend/
│   ├── app/
│   │   ├── api/                  # API endpoints
│   │   │   ├── auth.py          # User authentication
│   │   │   ├── oauth.py         # Web OAuth flow
│   │   │   ├── calendars.py     # Calendar selection
│   │   │   └── sync.py          # Sync operations
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── oauth_token.py
│   │   │   ├── sync_config.py
│   │   │   ├── sync_log.py
│   │   │   └── event_mapping.py  # Story 3
│   │   ├── core/
│   │   │   ├── security.py      # JWT + encryption
│   │   │   └── sync_engine.py   # Refactored sync.py logic
│   │   ├── migrations/          # Alembic migrations
│   │   ├── config.py            # Settings management
│   │   ├── database.py          # SQLAlchemy setup
│   │   └── main.py              # FastAPI app
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   └── Dashboard.tsx
│   │   ├── components/
│   │   │   ├── CalendarSelector.tsx    # Calendar dropdown
│   │   │   ├── SyncConfigForm.tsx      # Sync config creation
│   │   │   └── SyncHistoryDialog.tsx   # Sync history viewer
│   │   ├── context/
│   │   │   └── AuthContext.tsx
│   │   ├── services/
│   │   │   └── api.ts           # Axios client
│   │   ├── theme/
│   │   │   └── theme.ts         # Material UI theme
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── vite-env.d.ts        # TypeScript declarations
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── docker-compose.yml
├── .env.example
└── main.tf                      # Legacy Terraform
```

## Key Features

### Web OAuth Flow (Story 2)

Migrated from Desktop OOB to Web Application flow:
- Users connect both Google accounts via web browser
- OAuth tokens encrypted with Fernet before database storage
- Separate OAuth connections for source and destination accounts
- Tokens automatically refreshed when expired

### Idempotent Sync (Preserved from CLI)

Events tracked via `extendedProperties.shared.source_id`:
- **Create:** Source event not in destination → insert with `source_id`
- **Update:** Source event changed → update destination event with matching `source_id`
- **Delete:** Source event cancelled → delete destination event with matching `source_id`
- **Skip:** Source event unchanged → no API call

### Bidirectional Event Tracking (Story 3)

Enhanced event metadata for future 2-way sync:
- **sync_cluster_id:** UUID linking source ↔ destination events
- **event_mappings table:** Database tracking of event relationships
- **Content hashing:** SHA-256 for change detection
- **Last modified timestamps:** Conflict detection infrastructure
- **Bidirectional references:** Both events store each other's IDs

## Development Status

### Completed (Production Ready)
- ✅ Backend API with FastAPI
- ✅ SQLAlchemy models and Alembic migrations
- ✅ Google OAuth-only authentication (no passwords)
- ✅ Web OAuth flow (migrated from Desktop OOB)
- ✅ OAuth token encryption (Fernet)
- ✅ React + Material UI frontend with Google Material Design 3
- ✅ Google OAuth login page (registration happens automatically)
- ✅ Dashboard with OAuth connection status
- ✅ **Bi-directional sync** - events sync both ways between calendars
- ✅ **One-way sync** - traditional source → destination syncing
- ✅ **Privacy mode** - hide event details while preserving time slots
- ✅ **Event color customization** - 11 Google Calendar colors
- ✅ Refactored sync engine from CLI with conflict resolution
- ✅ Event mappings table with origin tracking
- ✅ Docker Compose for local development
- ✅ Calendar selection UI with dropdowns
- ✅ Sync configuration creation and management
- ✅ Manual sync trigger with detailed results
- ✅ Sync history viewer with complete audit trail
- ✅ Delete sync configurations
- ✅ Real-time sync status feedback
- ✅ Error handling and user notifications
- ✅ **101 passing tests** - comprehensive unit, integration, and E2E coverage
- ✅ **Bug fixes** - UUID type handling, idempotency restoration
- ✅ **E2E test suite** - 4 automated test scripts with real Google Calendar API
- ✅ Code cleanup and linting setup

### To Do (Story 1 - Terraform)
- ⬜ Terraform modules for production deployment
- ⬜ Cloud SQL with Auth Proxy
- ⬜ Cloud Run deployment
- ⬜ Secret Manager integration
- ⬜ Bootstrap script for OAuth client

### Future Enhancements
- ⬜ Automatic scheduled syncs (Cloud Scheduler)
- ⬜ Email notifications for sync failures
- ⬜ Calendar timezone handling improvements
- ⬜ Batch sync operations
- ⬜ Sync configuration templates
- ⬜ Recurring event instance-level operations (modify/delete single occurrences)
- ⬜ Advanced conflict resolution strategies beyond "origin wins"

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

- Future events only (configurable lookahead window, default: 90 days)
- Manual execution (no automatic scheduling in local dev environment)
- Calendars must belong to different isolated Google accounts
- Google OAuth-only authentication (no password recovery)
- Recurring event instance-level operations not supported in E2E test helpers (use Google Calendar UI for single instance edits)
- Conflict resolution uses "origin wins" strategy (the calendar where event was originally created takes precedence)

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development guide.

## Testing

### Unit & Integration Tests

**Backend (101 tests):**
```bash
docker-compose exec backend pytest -v
docker-compose exec backend pytest -n auto  # Parallel execution (faster)
docker-compose exec backend pytest --cov=app --cov-report=html  # With coverage
```

**Test Coverage:**
- ✅ 101 unit/integration tests with 100% pass rate
- 95% coverage on sync_engine.py (42 tests)
- 99% coverage on API endpoints (51 tests)
- E2E integration tests with real OAuth tokens (8 tests)

**Frontend:**
```bash
cd frontend && npm test -- --run
cd frontend && npm run lint  # ESLint
```

### E2E Testing Scripts

Comprehensive E2E test scripts for real Google Calendar API testing:

```bash
# All scripts require an access token from your session
# Get token: Login to app → Browser dev tools → localStorage → copy JWT token

# One-way sync: create, rename, move, delete
python3 e2e_test_auto.py <ACCESS_TOKEN>

# Bi-directional sync with multiple events
python3 e2e_test_bidirectional.py <ACCESS_TOKEN>

# Edge case: Delete synced event and resync (idempotency test)
python3 e2e_test_delete_synced.py <ACCESS_TOKEN>

# Recurring events test with edge case documentation
python3 e2e_test_recurring.py <ACCESS_TOKEN>
```

**Test Scripts:**
- `e2e_test_auto.py` - Fully automated one-way sync (4 tests: create, rename, move, delete)
- `e2e_test_bidirectional.py` - Bi-directional sync with 6 events (4 tests)
- `e2e_test_delete_synced.py` - Idempotency validation (5-step edge case)
- `e2e_test_recurring.py` - Recurring event handling with limitations documented

All scripts use calendars `test-4` and `test-5` by default and include automatic cleanup.

See [CLAUDE.md](CLAUDE.md) for detailed testing documentation and recent bug fixes.

## Contributing

1. Create feature branch
2. Make changes with tests
3. Run tests and linters
4. Submit pull request

## License

[Add your license here]
