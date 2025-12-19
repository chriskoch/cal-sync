# Calendar Sync - Multi-tenant SaaS

One-way synchronization of Google Calendar events between two different Google accounts. Web-based multi-tenant SaaS application with React + Material UI frontend and FastAPI backend.

> **📋 See [CHANGELOG.md](CHANGELOG.md) for detailed version history and release notes**

## How it works

- Multi-tenant SaaS with user registration and JWT authentication
- Web OAuth flow for connecting source and destination Google accounts
- Calendar selection UI for choosing which calendars to sync
- Each synced event stores `source_id` and bidirectional metadata in extended properties
- Idempotent sync mechanism preserves from original CLI version
- Sync triggered manually via web dashboard (or scheduled via Cloud Scheduler in production)
- Only syncs future events (default: now → 90 days)

## Architecture

**Tech Stack:**
- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **Frontend:** React 18, TypeScript, Material UI 5, Vite
- **Infrastructure:** Terraform (GCP Cloud Run, Cloud SQL, Secret Manager)
- **OAuth:** Web Application flow (migrated from Desktop OOB)

**Database Schema:**
- `users` - User accounts with JWT authentication
- `oauth_tokens` - Encrypted Google OAuth tokens (Fernet encryption)
- `calendars` - Cached calendar lists from Google
- `sync_configs` - User sync configurations
- `sync_logs` - Sync history and statistics
- `event_mappings` - Bidirectional event tracking (Story 3)

## Prerequisites

- **Local Development:**
  - Python 3.12+
  - Node.js 18+
  - Docker (for PostgreSQL)
  - Google Cloud project with OAuth client

- **Production Deployment:**
  - Terraform
  - GCP project with billing enabled

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
2. Register a new account
3. Connect Source Google account (OAuth flow)
4. Connect Destination Google account (OAuth flow)
5. Select calendars and create sync configuration
6. Trigger manual sync and view detailed results
7. View sync history with complete audit trail

## Usage

### Web Application

1. **User Registration**
   - Navigate to http://localhost:3033/register
   - Create account with email/password

2. **Connect Google Accounts**
   - Dashboard shows OAuth status cards
   - Click "Connect Source Account" → Google OAuth flow
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
- `POST /auth/register` - Register new user
- `POST /auth/token` - Login and get JWT
- `GET /auth/me` - Get current user

**OAuth:**
- `GET /oauth/start/{account_type}` - Initiate OAuth flow
- `GET /oauth/callback` - OAuth callback handler
- `GET /oauth/status` - Check connection status

**Calendars:**
- `GET /calendars/{account_type}/list` - List available calendars

**Sync:**
- `POST /sync/config` - Create sync configuration
- `GET /sync/config` - List user's sync configs
- `DELETE /sync/config/{config_id}` - Delete sync configuration
- `POST /sync/trigger/{config_id}` - Trigger manual sync
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
│   │   │   ├── Register.tsx
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
├── terraform/                    # Production infrastructure (TBD)
├── docker-compose.yml
├── .env.example
├── auth.py                      # Legacy CLI OAuth
├── sync.py                      # Legacy CLI sync
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

### Completed (Story 2 - Web App)
- ✅ Backend API with FastAPI
- ✅ SQLAlchemy models and Alembic migrations
- ✅ JWT authentication with user registration
- ✅ Web OAuth flow (migrated from Desktop OOB)
- ✅ OAuth token encryption (Fernet)
- ✅ React + Material UI frontend
- ✅ Login and registration pages
- ✅ Dashboard with OAuth connection status
- ✅ Refactored sync engine from CLI
- ✅ Event mappings table (Story 3)
- ✅ Docker Compose for local development
- ✅ Calendar selection UI with dropdowns
- ✅ Sync configuration creation and management
- ✅ Manual sync trigger with detailed results
- ✅ Sync history viewer with complete audit trail
- ✅ Delete sync configurations
- ✅ Real-time sync status feedback
- ✅ Error handling and user notifications

### To Do (Story 1 - Terraform)
- ⬜ Terraform modules for production deployment
- ⬜ Cloud SQL with Auth Proxy
- ⬜ Cloud Run deployment
- ⬜ Secret Manager integration
- ⬜ Bootstrap script for OAuth client

### Future Enhancements
- ⬜ Automatic scheduled syncs (Cloud Scheduler)
- ⬜ Bidirectional sync (2-way)
- ⬜ Email notifications for sync failures
- ⬜ Calendar timezone handling improvements
- ⬜ Batch sync operations
- ⬜ Sync configuration templates

### Legacy CLI (Preserved)

The original CLI scripts ([auth.py](auth.py), [sync.py](sync.py)) remain functional for backward compatibility. They use Desktop OAuth flow and filesystem token storage.

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
