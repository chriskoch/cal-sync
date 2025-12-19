# Next Iteration Plan (3 stories)

We stick to the same three stories: automate infra, add a web app for setup, and introduce durable identifiers for better/2-way sync. This version folds in feedback about OAuth creation limits, security, and rollout risk.

---

## Story 1 — Terraform: fully automated GCP project (minus OAuth client UI)

**Goal:** `terraform apply` brings up everything; only exception is OAuth client creation via a bootstrap script (Terraform can't reliably create web OAuth clients).

**Note:** Story 1 is for **production deployment only**. Local development uses Docker Postgres (see Quick Start Guide).

### Project Structure
```
terraform/
├── main.tf                      # Root module
├── variables.tf
├── outputs.tf
├── backend.tf                   # GCS backend config
├── environments/
│   ├── dev.tfvars
│   ├── staging.tfvars
│   └── prod.tfvars
└── modules/
    ├── apis/                    # Enable GCP APIs
    ├── sql/                     # Cloud SQL + Auth Proxy config
    ├── secrets/                 # Secret Manager
    ├── cloud_run/               # Backend + Frontend services
    └── iam/                     # Service accounts + bindings
```

### Implementation Details

#### 1.1 APIs Module (`terraform/modules/apis/main.tf`)
```hcl
resource "google_project_service" "apis" {
  for_each = toset([
    "calendar-json.googleapis.com",
    "sqladmin.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iap.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}
```

#### 1.2 Cloud SQL Module (`terraform/modules/sql/main.tf`)
**Choice: Cloud SQL Auth Proxy (no VPC needed)**
```hcl
resource "google_sql_database_instance" "postgres" {
  name             = var.instance_name
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = var.tier  # db-f1-micro (dev) / db-custom-2-7680 (prod)

    # Public IP with authorized networks (Cloud Run uses Auth Proxy)
    ip_configuration {
      ipv4_enabled    = true
      require_ssl     = true
      # Cloud Run will use Unix socket via /cloudsql/
    }

    backup_configuration {
      enabled            = true
      start_time         = "03:00"
      point_in_time_recovery_enabled = var.enable_pitr
    }
  }
}

resource "google_sql_database" "app_db" {
  name     = "calsync"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app_user" {
  name     = "calsync_app"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store DB password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "db-password"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

output "connection_name" {
  value = google_sql_database_instance.postgres.connection_name
  # Format: project:region:instance
}
```

#### 1.3 Cloud Run Module (`terraform/modules/cloud_run/main.tf`)
```hcl
# Backend API Service
resource "google_cloud_run_v2_service" "api" {
  name     = "${var.project_id}-api"
  location = var.region

  template {
    service_account = google_service_account.api.email

    # Cloud SQL connection via Unix socket
    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [var.sql_connection_name]
      }
    }

    containers {
      image = var.api_image  # gcr.io/${PROJECT_ID}/api:latest

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      env {
        name  = "DB_HOST"
        value = "/cloudsql/${var.sql_connection_name}"
      }

      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = "db-password"
            version = "latest"
          }
        }
      }

      env {
        name = "OAUTH_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = "oauth-client-id"
            version = "latest"
          }
        }
      }

      env {
        name = "OAUTH_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = "oauth-client-secret"
            version = "latest"
          }
        }
      }

      env {
        name = "ENCRYPTION_KEY"
        value_source {
          secret_key_ref {
            secret  = "app-encryption-key"
            version = "latest"
          }
        }
      }
    }
  }
}

# Service Account for API
resource "google_service_account" "api" {
  account_id = "${var.project_id}-api"
}

# Grant Cloud SQL Client role
resource "google_project_iam_member" "api_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# Grant Secret Manager access
resource "google_secret_manager_secret_iam_member" "api_secrets" {
  for_each = toset([
    "db-password",
    "oauth-client-id",
    "oauth-client-secret",
    "app-encryption-key"
  ])
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}
```

#### 1.4 Bootstrap Script for OAuth Client (`scripts/bootstrap-oauth.sh`)
```bash
#!/bin/bash
set -e

PROJECT_ID="${1}"
ENVIRONMENT="${2:-dev}"
API_URL="${3}"

if [ -z "$PROJECT_ID" ] || [ -z "$API_URL" ]; then
  echo "Usage: $0 <project-id> <environment> <api-url>"
  echo "Example: $0 cal-sync-dev dev https://api-xyz.run.app"
  exit 1
fi

echo "Creating OAuth client for $PROJECT_ID ($ENVIRONMENT)..."

# Create OAuth consent screen (if not exists)
gcloud iap oauth-brands create \
  --application_title="Calendar Sync" \
  --support_email="christian@livelyapps.com" \
  --project="$PROJECT_ID" \
  2>/dev/null || echo "OAuth brand already exists"

# Create Web OAuth client
CLIENT_JSON=$(gcloud iap oauth-clients create \
  projects/$PROJECT_ID/brands/$(gcloud iap oauth-brands list --project=$PROJECT_ID --format='value(name)' | head -n1 | cut -d'/' -f4) \
  --display_name="cal-sync-web-$ENVIRONMENT" \
  --format=json)

CLIENT_ID=$(echo "$CLIENT_JSON" | jq -r '.name' | cut -d'/' -f6)
CLIENT_SECRET=$(echo "$CLIENT_JSON" | jq -r '.secret')

echo "OAuth Client created:"
echo "  Client ID: $CLIENT_ID"

# Store in Secret Manager
echo "$CLIENT_ID" | gcloud secrets create oauth-client-id \
  --data-file=- \
  --project="$PROJECT_ID" \
  2>/dev/null || \
  echo "$CLIENT_ID" | gcloud secrets versions add oauth-client-id \
  --data-file=- \
  --project="$PROJECT_ID"

echo "$CLIENT_SECRET" | gcloud secrets create oauth-client-secret \
  --data-file=- \
  --project="$PROJECT_ID" \
  2>/dev/null || \
  echo "$CLIENT_SECRET" | gcloud secrets versions add oauth-client-secret \
  --data-file=- \
  --project="$PROJECT_ID"

# Generate and store encryption key
ENCRYPTION_KEY=$(openssl rand -base64 32)
echo "$ENCRYPTION_KEY" | gcloud secrets create app-encryption-key \
  --data-file=- \
  --project="$PROJECT_ID" \
  2>/dev/null || \
  echo "$ENCRYPTION_KEY" | gcloud secrets versions add app-encryption-key \
  --data-file=- \
  --project="$PROJECT_ID"

echo ""
echo "✓ Bootstrap complete!"
echo "✓ Secrets stored in Secret Manager"
echo ""
echo "IMPORTANT: Add this redirect URI in GCP Console:"
echo "  https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
echo "  Redirect URI: ${API_URL}/oauth/callback"
```

### Deployment Commands
```bash
# 1. Initialize Terraform
cd terraform
terraform init

# 2. Plan infrastructure
terraform plan -var-file="environments/dev.tfvars" -out=tfplan

# 3. Apply infrastructure
terraform apply tfplan

# 4. Get API URL
API_URL=$(terraform output -raw api_url)

# 5. Bootstrap OAuth client
../scripts/bootstrap-oauth.sh cal-sync-dev dev "$API_URL"

# 6. Manually add redirect URI in Console (TODO: automate if possible)
# Visit: https://console.cloud.google.com/apis/credentials?project=cal-sync-dev
# Edit the OAuth client, add redirect URI: ${API_URL}/oauth/callback
```

### Environment Variables (`terraform/environments/dev.tfvars`)
```hcl
project_id      = "cal-sync-dev"
region          = "us-central1"
sql_tier        = "db-f1-micro"
enable_pitr     = false
api_image       = "gcr.io/cal-sync-dev/api:latest"
frontend_image  = "gcr.io/cal-sync-dev/frontend:latest"
```

### Deliverables
- ✅ Terraform modules for APIs, Cloud SQL, Cloud Run, Secrets, IAM
- ✅ Bootstrap script for OAuth client creation
- ✅ Environment configs (dev/staging/prod)
- ✅ Cloud SQL Auth Proxy integration in Cloud Run
- ✅ All secrets in Secret Manager

---

## Story 2 — Web app for auth and sync setup (React + Material Design)

**Goal:** User logs in, connects two Google accounts, picks source/destination calendars, and can trigger sync from the web UI.

### Project Structure
```
backend/
├── app/
│   ├── main.py                      # FastAPI app
│   ├── config.py                    # Settings from env/secrets
│   ├── database.py                  # SQLAlchemy setup
│   ├── api/
│   │   ├── auth.py                  # POST /auth/register, /auth/login
│   │   ├── oauth.py                 # GET /oauth/start/{type}, /oauth/callback
│   │   ├── calendars.py             # GET /calendars/{type}/list
│   │   └── sync.py                  # POST /sync/config, /sync/trigger
│   ├── models/
│   │   ├── user.py
│   │   ├── oauth_token.py
│   │   ├── calendar.py
│   │   ├── sync_config.py
│   │   ├── sync_log.py
│   │   └── event_mapping.py        # Story 3
│   ├── core/
│   │   ├── security.py              # JWT + encryption
│   │   └── sync_engine.py           # Refactored sync.py logic
│   └── migrations/
│       └── versions/
│           └── 001_initial.py
├── requirements.txt
├── Dockerfile
└── alembic.ini

frontend/
├── src/
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── Dashboard.tsx
│   │   ├── CalendarSetup.tsx
│   │   └── SyncHistory.tsx
│   ├── components/
│   │   ├── GoogleOAuthButton.tsx
│   │   ├── CalendarSelector.tsx
│   │   └── SyncTrigger.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   └── useCalendars.ts
│   ├── context/
│   │   └── AuthContext.tsx
│   └── services/
│       └── api.ts                   # Axios client
├── package.json
├── Dockerfile
└── nginx.conf
```

### Implementation Details

#### 2.1 Database Schema (`backend/app/migrations/versions/001_initial.py`)
```python
"""Initial schema

Revision ID: 001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # OAuth tokens table (encrypted in DB)
    op.create_table('oauth_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('account_type', sa.String(20), nullable=False),  # 'source' or 'destination'
        sa.Column('google_email', sa.String(255), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text()),
        sa.Column('token_expiry', sa.DateTime(timezone=True)),
        sa.Column('scopes', postgresql.ARRAY(sa.String())),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'account_type', name='uq_user_account_type')
    )
    op.create_index('idx_oauth_tokens_user', 'oauth_tokens', ['user_id'])

    # Calendars cache table
    op.create_table('calendars',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('oauth_token_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('oauth_tokens.id', ondelete='CASCADE'), nullable=False),
        sa.Column('google_calendar_id', sa.String(255), nullable=False),
        sa.Column('calendar_name', sa.String(255), nullable=False),
        sa.Column('access_role', sa.String(50)),  # owner, writer, reader
        sa.Column('is_primary', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('oauth_token_id', 'google_calendar_id', name='uq_token_calendar')
    )

    # Sync configs table
    op.create_table('sync_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_calendar_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calendars.id'), nullable=False),
        sa.Column('dest_calendar_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calendars.id'), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('sync_lookahead_days', sa.Integer(), default=90),
        sa.Column('last_sync_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint('source_calendar_id != dest_calendar_id', name='ck_different_calendars')
    )

    # Sync logs table
    op.create_table('sync_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('sync_config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sync_configs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),  # started, running, completed, failed
        sa.Column('events_created', sa.Integer(), default=0),
        sa.Column('events_updated', sa.Integer(), default=0),
        sa.Column('events_deleted', sa.Integer(), default=0),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('error_message', sa.Text())
    )
    op.create_index('idx_sync_logs_config', 'sync_logs', ['sync_config_id'])

def downgrade():
    op.drop_table('sync_logs')
    op.drop_table('sync_configs')
    op.drop_table('calendars')
    op.drop_table('oauth_tokens')
    op.drop_table('users')
```

#### 2.2 Backend API - OAuth Flow (`backend/app/api/oauth.py`)
**Critical: Migrates from [auth.py](auth.py) Desktop → Web OAuth**

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

from app.database import get_db
from app.models.user import User
from app.models.oauth_token import OAuthToken
from app.api.auth import get_current_user
from app.core.security import encrypt_token, decrypt_token

router = APIRouter(prefix="/oauth", tags=["oauth"])

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
API_URL = os.getenv("API_URL")  # From Cloud Run

def create_flow(state: str):
    """Create OAuth flow for Web application."""
    return Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [f"{API_URL}/oauth/callback"],
            }
        },
        scopes=SCOPES,
        state=state,
        redirect_uri=f"{API_URL}/oauth/callback"
    )

@router.get("/start/{account_type}")
async def start_oauth(
    account_type: str,
    current_user: User = Depends(get_current_user)
):
    """Initiate Google OAuth flow for source or destination account."""
    if account_type not in ["source", "destination"]:
        raise HTTPException(400, "Invalid account_type")

    # Encode user_id:account_type in state for callback
    state = f"{current_user.id}:{account_type}"
    flow = create_flow(state)

    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",  # Force consent to get refresh_token
        include_granted_scopes="true"
    )

    return {"authorization_url": authorization_url}

@router.get("/callback")
async def oauth_callback(request: Request, db = Depends(get_db)):
    """Handle Google OAuth callback and store tokens."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or not state:
        raise HTTPException(400, "Missing code or state")

    # Parse state
    try:
        user_id, account_type = state.split(":")
    except:
        raise HTTPException(400, "Invalid state")

    # Exchange code for tokens
    flow = create_flow(state)
    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Get user's Google email
    service = build("oauth2", "v2", credentials=credentials)
    user_info = service.userinfo().get().execute()
    google_email = user_info["email"]

    # Store encrypted tokens in database
    oauth_token = db.query(OAuthToken).filter_by(
        user_id=user_id,
        account_type=account_type
    ).first()

    if oauth_token:
        # Update existing
        oauth_token.access_token_encrypted = encrypt_token(credentials.token)
        oauth_token.refresh_token_encrypted = encrypt_token(credentials.refresh_token) if credentials.refresh_token else None
        oauth_token.token_expiry = credentials.expiry
        oauth_token.google_email = google_email
    else:
        # Create new
        oauth_token = OAuthToken(
            user_id=user_id,
            account_type=account_type,
            google_email=google_email,
            access_token_encrypted=encrypt_token(credentials.token),
            refresh_token_encrypted=encrypt_token(credentials.refresh_token) if credentials.refresh_token else None,
            token_expiry=credentials.expiry,
            scopes=SCOPES
        )
        db.add(oauth_token)

    db.commit()

    # Redirect to frontend success page
    frontend_url = os.getenv("FRONTEND_URL")
    return RedirectResponse(f"{frontend_url}/setup/success?account={account_type}")
```

#### 2.3 Backend - Sync Engine (`backend/app/core/sync_engine.py`)
**Preserves [sync.py](sync.py) logic (lines 58-160)**

```python
"""
Refactored sync logic from sync.py
Preserves idempotent sync mechanism
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app.models.sync_log import SyncLog

def iso_utc(dt: datetime) -> str:
    """From sync.py line 31"""
    return dt.replace(microsecond=0, tzinfo=None).isoformat() + "Z"

def fetch_events(service, calendar_id: str, time_min: str, time_max: str) -> List[dict]:
    """From sync.py lines 35-55"""
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
    """From sync.py lines 58-77"""
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
        "reminders": {"useDefault": False},
        "extendedProperties": {
            "shared": {
                "source_id": src.get("id"),
            }
        },
    }
    return {k: v for k, v in body.items() if v is not None}

def events_differ(src_body: dict, dest_event: dict) -> bool:
    """From sync.py lines 80-96"""
    comparable_keys = [
        "summary", "description", "location", "start", "end",
        "recurrence", "transparency", "visibility", "colorId", "reminders",
    ]
    for key in comparable_keys:
        if src_body.get(key) != dest_event.get(key):
            return True
    return False

class SyncEngine:
    """Stateless sync engine with dependency injection."""

    def __init__(self, source_creds: Credentials, dest_creds: Credentials):
        self.service_src = build("calendar", "v3", credentials=source_creds, cache_discovery=False)
        self.service_dst = build("calendar", "v3", credentials=dest_creds, cache_discovery=False)

    def execute_sync(
        self,
        source_google_cal_id: str,
        dest_google_cal_id: str,
        lookahead_days: int = 90
    ) -> dict:
        """
        Execute one-way sync from source to destination.
        Preserves sync.py main loop logic (lines 109-160).

        Returns: {created, updated, deleted, scanned}
        """
        now = datetime.now(timezone.utc)
        time_min = iso_utc(now)
        time_max = iso_utc(now + timedelta(days=lookahead_days))

        # Fetch events
        source_events = fetch_events(self.service_src, source_google_cal_id, time_min, time_max)
        dest_events = fetch_events(self.service_dst, dest_google_cal_id, time_min, time_max)

        # Build destination map by source_id (sync.py lines 124-129)
        dest_map: Dict[str, dict] = {}
        for ev in dest_events:
            shared = ev.get("extendedProperties", {}).get("shared", {})
            src_key = shared.get("source_id")
            if src_key:
                dest_map[src_key] = ev

        created = updated = deleted = 0

        # Main sync loop (sync.py lines 132-160)
        for src in source_events:
            src_id = src.get("id")
            if not src_id:
                continue

            dest_match = dest_map.get(src_id)

            # Handle cancelled events (sync.py lines 138-142)
            if src.get("status") == "cancelled":
                if dest_match:
                    self.service_dst.events().delete(
                        calendarId=dest_google_cal_id,
                        eventId=dest_match["id"]
                    ).execute()
                    deleted += 1
                continue

            payload = build_payload_from_source(src)

            if dest_match:
                # Update if changed (sync.py lines 145-153)
                if events_differ(payload, dest_match):
                    self.service_dst.events().update(
                        calendarId=dest_google_cal_id,
                        eventId=dest_match["id"],
                        body=payload,
                        sendUpdates="none",
                    ).execute()
                    updated += 1
            else:
                # Create new event (sync.py lines 154-160)
                self.service_dst.events().insert(
                    calendarId=dest_google_cal_id,
                    body=payload,
                    sendUpdates="none",
                ).execute()
                created += 1

        return {
            "created": created,
            "updated": updated,
            "deleted": deleted,
            "scanned": len(source_events)
        }
```

#### 2.4 Frontend - Dashboard (`frontend/src/pages/Dashboard.tsx`)
```typescript
import React, { useEffect, useState } from 'react';
import { Container, Grid, Card, CardContent, Typography, Button, Chip } from '@mui/material';
import { CheckCircle, Error, CalendarToday } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

interface OAuthStatus {
  source: { connected: boolean; email: string | null };
  destination: { connected: boolean; email: string | null };
}

export default function Dashboard() {
  const { user } = useAuth();
  const [oauthStatus, setOauthStatus] = useState<OAuthStatus | null>(null);

  useEffect(() => {
    fetchOAuthStatus();
  }, []);

  const fetchOAuthStatus = async () => {
    const { data } = await api.get('/oauth/status');
    setOauthStatus(data);
  };

  const handleConnect = async (accountType: 'source' | 'destination') => {
    const { data } = await api.get(`/oauth/start/${accountType}`);
    window.location.href = data.authorization_url;
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>Dashboard</Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <CalendarToday /> Source Calendar
              </Typography>
              {oauthStatus?.source.connected ? (
                <>
                  <Chip icon={<CheckCircle />} label="Connected" color="success" />
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    {oauthStatus.source.email}
                  </Typography>
                </>
              ) : (
                <>
                  <Chip icon={<Error />} label="Not Connected" color="error" />
                  <Button
                    variant="contained"
                    sx={{ mt: 2 }}
                    onClick={() => handleConnect('source')}
                  >
                    Connect Google Account
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <CalendarToday /> Destination Calendar
              </Typography>
              {oauthStatus?.destination.connected ? (
                <>
                  <Chip icon={<CheckCircle />} label="Connected" color="success" />
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    {oauthStatus.destination.email}
                  </Typography>
                </>
              ) : (
                <>
                  <Chip icon={<Error />} label="Not Connected" color="error" />
                  <Button
                    variant="contained"
                    sx={{ mt: 2 }}
                    onClick={() => handleConnect('destination')}
                  >
                    Connect Google Account
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
}
```

### Deliverables
- ✅ FastAPI backend with JWT auth
- ✅ Web OAuth flow (migrate from [auth.py](auth.py) Desktop flow)
- ✅ Database schema with encrypted token storage
- ✅ Sync engine preserving [sync.py](sync.py) core logic
- ✅ React + MUI frontend
- ✅ Dockerfiles for backend and frontend
- ✅ Cloud Run deployment configuration

---

## Story 3 — Unique identifiers for future better/2-way sync

**Goal:** Each synced pair has a stable identifier to improve matching and enable 2-way later.

### Implementation Details

#### 3.1 Event Mappings Table (`backend/app/migrations/versions/002_event_mappings.py`)
```python
"""Add event_mappings table

Revision ID: 002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('event_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('sync_config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sync_configs.id', ondelete='CASCADE'), nullable=False),

        # Bidirectional references
        sa.Column('source_event_id', sa.String(255), nullable=False),
        sa.Column('dest_event_id', sa.String(255), nullable=False),

        # Unique pairing identifier
        sa.Column('sync_cluster_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Metadata for conflict detection and change tracking
        sa.Column('source_last_modified', sa.DateTime(timezone=True)),
        sa.Column('dest_last_modified', sa.DateTime(timezone=True)),
        sa.Column('last_synced_at', sa.DateTime(timezone=True)),
        sa.Column('content_hash', sa.String(64)),  # SHA-256

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.UniqueConstraint('sync_config_id', 'source_event_id', name='uq_config_source'),
        sa.UniqueConstraint('sync_config_id', 'dest_event_id', name='uq_config_dest')
    )

    op.create_index('idx_event_mappings_config', 'event_mappings', ['sync_config_id'])
    op.create_index('idx_event_mappings_cluster', 'event_mappings', ['sync_cluster_id'])

def downgrade():
    op.drop_table('event_mappings')
```

#### 3.2 Enhanced Extended Properties
**Modify `backend/app/core/sync_engine.py`:**

```python
import hashlib
import uuid

def compute_content_hash(event: dict) -> str:
    """Compute SHA-256 hash of event content for change detection."""
    comparable_fields = {
        "summary": event.get("summary"),
        "description": event.get("description"),
        "location": event.get("location"),
        "start": str(event.get("start")),
        "end": str(event.get("end")),
    }
    content = str(sorted(comparable_fields.items()))
    return hashlib.sha256(content.encode()).hexdigest()

def build_payload_from_source_v2(src: dict, sync_cluster_id: str, dest_event_id: str = None) -> dict:
    """Enhanced version with bidirectional metadata (Story 3)."""
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
        "reminders": {"useDefault": False},
        "extendedProperties": {
            "shared": {
                # Original (backward compatible)
                "source_id": src.get("id"),

                # Story 3: Bidirectional tracking
                "sync_cluster_id": sync_cluster_id,
                "dest_event_id": dest_event_id or "",
                "last_sync_timestamp": iso_utc(datetime.now(timezone.utc)),
                "sync_direction": "source_to_dest",
            }
        },
    }
    return {k: v for k, v in body.items() if v is not None}

class SyncEngine:
    """Enhanced sync engine with event mappings (Story 3)."""

    def __init__(self, source_creds: Credentials, dest_creds: Credentials, db_session):
        self.service_src = build("calendar", "v3", credentials=source_creds, cache_discovery=False)
        self.service_dst = build("calendar", "v3", credentials=dest_creds, cache_discovery=False)
        self.db = db_session

    def execute_sync(
        self,
        sync_config_id: str,
        source_google_cal_id: str,
        dest_google_cal_id: str,
        lookahead_days: int = 90
    ) -> dict:
        """
        Enhanced sync with event mappings.
        """
        from app.models.event_mapping import EventMapping

        now = datetime.now(timezone.utc)
        time_min = iso_utc(now)
        time_max = iso_utc(now + timedelta(days=lookahead_days))

        # Fetch events
        source_events = fetch_events(self.service_src, source_google_cal_id, time_min, time_max)
        dest_events = fetch_events(self.service_dst, dest_google_cal_id, time_min, time_max)

        # Build destination map
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

            # Get or create event mapping
            mapping = self.db.query(EventMapping).filter_by(
                sync_config_id=sync_config_id,
                source_event_id=src_id
            ).first()

            # Handle cancelled events
            if src.get("status") == "cancelled":
                if dest_match:
                    self.service_dst.events().delete(
                        calendarId=dest_google_cal_id,
                        eventId=dest_match["id"]
                    ).execute()
                    deleted += 1

                    # Remove mapping
                    if mapping:
                        self.db.delete(mapping)
                continue

            # Get sync cluster ID
            sync_cluster_id = str(mapping.sync_cluster_id) if mapping else str(uuid.uuid4())

            # Build payload with bidirectional metadata
            dest_event_id = dest_match["id"] if dest_match else None
            payload = build_payload_from_source_v2(src, sync_cluster_id, dest_event_id)
            content_hash = compute_content_hash(src)

            if dest_match:
                # Update if changed
                if events_differ(payload, dest_match):
                    result = self.service_dst.events().update(
                        calendarId=dest_google_cal_id,
                        eventId=dest_match["id"],
                        body=payload,
                        sendUpdates="none",
                    ).execute()
                    updated += 1

                    # Update mapping
                    if mapping:
                        mapping.dest_last_modified = now
                        mapping.content_hash = content_hash
                        mapping.last_synced_at = now
            else:
                # Create new event
                result = self.service_dst.events().insert(
                    calendarId=dest_google_cal_id,
                    body=payload,
                    sendUpdates="none",
                ).execute()
                created += 1

                # Create mapping
                new_mapping = EventMapping(
                    sync_config_id=sync_config_id,
                    source_event_id=src_id,
                    dest_event_id=result["id"],
                    sync_cluster_id=uuid.UUID(sync_cluster_id),
                    source_last_modified=datetime.fromisoformat(src.get("updated").replace("Z", "+00:00")) if src.get("updated") else now,
                    dest_last_modified=now,
                    last_synced_at=now,
                    content_hash=content_hash
                )
                self.db.add(new_mapping)

        self.db.commit()

        return {
            "created": created,
            "updated": updated,
            "deleted": deleted,
            "scanned": len(source_events)
        }
```

#### 3.3 Update Source Events (Optional - For Full Bidirectional)
**Add helper function:**

```python
def update_source_with_dest_reference(
    service_src,
    source_calendar_id: str,
    source_event_id: str,
    dest_event_id: str,
    sync_cluster_id: str
):
    """
    Update source event with destination reference (bidirectional).

    WARNING: This makes an extra API call per event.
    Only enable if bidirectional tracking is critical.
    """
    try:
        src_event = service_src.events().get(
            calendarId=source_calendar_id,
            eventId=source_event_id
        ).execute()

        if "extendedProperties" not in src_event:
            src_event["extendedProperties"] = {"shared": {}}

        src_event["extendedProperties"]["shared"]["dest_event_id"] = dest_event_id
        src_event["extendedProperties"]["shared"]["sync_cluster_id"] = sync_cluster_id

        service_src.events().update(
            calendarId=source_calendar_id,
            eventId=source_event_id,
            body=src_event,
            sendUpdates="none",
        ).execute()

    except Exception as e:
        # Non-critical: log but don't fail sync
        print(f"Warning: Could not update source event {source_event_id}: {e}")
```

### Testing
**`backend/tests/test_event_mappings.py`:**

```python
import pytest
from app.models.event_mapping import EventMapping
from app.core.sync_engine import compute_content_hash
import uuid

def test_event_mapping_creation(db_session):
    """Test creating event mapping."""
    mapping = EventMapping(
        sync_config_id=uuid.uuid4(),
        source_event_id="src_123",
        dest_event_id="dest_456",
        sync_cluster_id=uuid.uuid4(),
        content_hash="abc123"
    )
    db_session.add(mapping)
    db_session.commit()

    assert mapping.id is not None
    assert mapping.sync_cluster_id is not None

def test_content_hash_consistency():
    """Test that identical events produce same hash."""
    event1 = {
        "summary": "Meeting",
        "start": {"dateTime": "2025-12-20T10:00:00Z"},
        "end": {"dateTime": "2025-12-20T11:00:00Z"}
    }
    event2 = dict(event1)

    hash1 = compute_content_hash(event1)
    hash2 = compute_content_hash(event2)

    assert hash1 == hash2

def test_unique_constraint(db_session, sync_config):
    """Test that duplicate source_event_id fails."""
    mapping1 = EventMapping(
        sync_config_id=sync_config.id,
        source_event_id="src_123",
        dest_event_id="dest_456",
        sync_cluster_id=uuid.uuid4()
    )
    db_session.add(mapping1)
    db_session.commit()

    # Try to add duplicate
    mapping2 = EventMapping(
        sync_config_id=sync_config.id,
        source_event_id="src_123",  # Same source event
        dest_event_id="dest_789",
        sync_cluster_id=uuid.uuid4()
    )
    db_session.add(mapping2)

    with pytest.raises(Exception):  # IntegrityError
        db_session.commit()
```

### Deliverables
- ✅ `event_mappings` table with bidirectional references
- ✅ `sync_cluster_id` UUID for each event pair
- ✅ Content hash for change detection
- ✅ Last sync timestamps for conflict detection foundation
- ✅ Enhanced `build_payload_from_source_v2()` with extended properties
- ✅ Sync engine maintains mappings on create/update/delete
- ✅ Tests for mapping creation and edge cases

---

## Migration Path (CLI → Web App)

### For Existing CLI Users
**Script: `scripts/migrate_cli_to_web.py`**

```python
#!/usr/bin/env python3
"""
Migrate existing CLI setup to web app database.
Reads: creds/source/token.json, creds/dest/token.json, .env
Creates: User account, oauth_tokens, sync_config in PostgreSQL
"""
import json
import os
import sys
from getpass import getpass
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")

def main():
    print("=" * 60)
    print("CLI → Web App Migration Tool")
    print("=" * 60)

    # 1. Register user
    print("\n[1/4] Create web app account")
    email = input("Email: ")
    password = getpass("Password: ")
    full_name = input("Full name: ")

    resp = requests.post(f"{API_URL}/auth/register", json={
        "email": email,
        "password": password,
        "full_name": full_name
    })
    resp.raise_for_status()
    print("✓ User created")

    # 2. Login
    resp = requests.post(f"{API_URL}/auth/token", data={
        "username": email,
        "password": password
    })
    resp.raise_for_status()
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Logged in")

    # 3. Upload source tokens
    print("\n[2/4] Migrating source calendar")
    with open("creds/source/token.json") as f:
        source_token = json.load(f)

    # Note: You'd need a special migration endpoint to accept tokens directly
    # For security, normal flow requires OAuth. This is a backdoor for migration.
    resp = requests.post(f"{API_URL}/migration/import-token", headers=headers, json={
        "account_type": "source",
        "token_data": source_token
    })
    resp.raise_for_status()
    print(f"✓ Source: {source_token.get('account', 'unknown email')}")

    # 4. Upload dest tokens
    print("\n[3/4] Migrating destination calendar")
    with open("creds/dest/token.json") as f:
        dest_token = json.load(f)

    resp = requests.post(f"{API_URL}/migration/import-token", headers=headers, json={
        "account_type": "destination",
        "token_data": dest_token
    })
    resp.raise_for_status()
    print(f"✓ Destination: {dest_token.get('account', 'unknown email')}")

    # 5. Create sync config
    print("\n[4/4] Creating sync configuration")
    source_cal_id = os.getenv("SOURCE_CALENDAR_ID")
    dest_cal_id = os.getenv("DEST_CALENDAR_ID")

    if not source_cal_id or not dest_cal_id:
        print("ERROR: SOURCE_CALENDAR_ID and DEST_CALENDAR_ID must be set in .env")
        sys.exit(1)

    # This would need to map calendar IDs to database IDs
    # Simplified: assume migration endpoint handles this
    resp = requests.post(f"{API_URL}/migration/create-config", headers=headers, json={
        "source_calendar_id": source_cal_id,
        "dest_calendar_id": dest_cal_id,
        "sync_lookahead_days": int(os.getenv("SYNC_LOOKAHEAD_DAYS", "90"))
    })
    resp.raise_for_status()

    print("\n" + "=" * 60)
    print("✓ Migration complete!")
    print(f"✓ Login at: {API_URL.replace('8000', '3000')}")  # Frontend URL
    print(f"✓ Email: {email}")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

### Usage
```bash
# Ensure CLI setup exists
ls creds/source/token.json creds/dest/token.json .env

# Run migration
python scripts/migrate_cli_to_web.py

# Verify in web app
open http://localhost:3000/dashboard
```

---

## Quick Start Guide

### Environment Comparison

| Component | Local Development | Production |
|-----------|------------------|------------|
| **Database** | Docker Postgres container | Cloud SQL (Terraform) |
| **OAuth Client** | Manual GCP Console setup | Bootstrap script (Terraform) |
| **Backend** | `uvicorn --reload` | Cloud Run container |
| **Frontend** | `npm run dev` | Cloud Run container (nginx) |
| **Secrets** | `.env` file | Secret Manager |

### Local Development Setup

**Prerequisites:**
- Docker installed
- Python 3.12+
- Node.js 20+
- GCP project for OAuth (manual one-time setup)

**Steps:**

```bash
# 1. Clone repo
git clone <repo-url>
cd cal-sync

# 2. Start local PostgreSQL in Docker
docker run -d --name cal-sync-db \
  -e POSTGRES_PASSWORD=dev \
  -e POSTGRES_DB=calsync \
  -p 5432:5432 \
  postgres:15

# Verify database is running
docker ps | grep cal-sync-db

# 3. Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file for local dev
cat > .env << EOF
DATABASE_URL=postgresql://postgres:dev@localhost:5432/calsync
OAUTH_CLIENT_ID=<from-gcp-console>
OAUTH_CLIENT_SECRET=<from-gcp-console>
ENCRYPTION_KEY=$(openssl rand -base64 32)
API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
JWT_SECRET=$(openssl rand -base64 32)
EOF

# Run database migrations
alembic upgrade head

# Start backend API
uvicorn app.main:app --reload --port 8000

# 4. Setup frontend (separate terminal)
cd frontend
npm install

# Create .env.local
cat > .env.local << EOF
REACT_APP_API_URL=http://localhost:8000
EOF

npm run dev

# 5. Open browser
open http://localhost:3000
```

**One-time OAuth Setup for Local Dev:**
1. Visit https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URI: `http://localhost:8000/oauth/callback`
4. Copy Client ID and Secret to backend `.env` file

### Production Deployment
```bash
# See Story 1 deployment commands
cd terraform
terraform init
terraform apply -var-file="environments/prod.tfvars"

API_URL=$(terraform output -raw api_url)
../scripts/bootstrap-oauth.sh <project-id> prod "$API_URL"

# Build and deploy containers
gcloud builds submit --config=cloudbuild.yaml
```

---

## Success Criteria

### Story 1 ✅
- [ ] `terraform apply` provisions all infrastructure
- [ ] Bootstrap script creates OAuth client
- [ ] Cloud SQL Auth Proxy configured in Cloud Run
- [ ] All secrets in Secret Manager
- [ ] Zero manual GCP Console steps (except OAuth redirect URI)

### Story 2 ✅
- [ ] User can register and login
- [ ] OAuth flow connects source Google account
- [ ] OAuth flow connects destination Google account
- [ ] Calendar list displays for both accounts
- [ ] User can create sync configuration
- [ ] Manual "Sync Now" button works
- [ ] Sync history shows in UI
- [ ] Original [sync.py](sync.py) logic preserved

### Story 3 ✅
- [ ] `event_mappings` table created
- [ ] Each synced event has `sync_cluster_id`
- [ ] Content hash computed and stored
- [ ] Bidirectional references in extended properties
- [ ] Mappings maintained on create/update/delete
- [ ] Tests pass for mapping edge cases
