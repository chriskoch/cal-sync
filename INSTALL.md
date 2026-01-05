# Installation Guide

Get Calendar Sync running in 15 minutes.

## Quick Start

1. **[Configure Google OAuth](#step-1-google-oauth-setup)** (5 min)
2. **[Deploy with Docker](#step-2-deploy-with-docker)** (5 min)
3. **[Configure reverse proxy](#step-3-configure-reverse-proxy)** (optional - for production)
4. **[Start syncing](#step-4-first-use)** (5 min)

---

## Step 1: Google OAuth Setup

### 1.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Navigate to **"APIs & Services"** → **"Library"**
4. Enable **"Google Calendar API"**

### 1.2 Configure OAuth Consent Screen

1. Go to **"APIs & Services"** → **"OAuth consent screen"**
2. Select **"External"** user type → **"Create"**
3. Fill in app information:
   - **App name**: `Calendar Sync`
   - **User support email**: Your email
   - **Developer contact email**: Your email
4. Click **"Save and Continue"**

5. **Add Scopes**:
   - Click **"Add or Remove Scopes"**
   - Search for and select: `https://www.googleapis.com/auth/calendar`
   - Click **"Update"** → **"Save and Continue"**

6. **Add Test Users** (IMPORTANT):
   - Click **"Add Users"**
   - **Add ALL email addresses** you'll use for syncing calendars
   - Click **"Save and Continue"**
   - Click **"Back to Dashboard"**

> **⚠️ Common Issue**: If you skip adding test users, you'll get "Error 403: access_denied" when signing in.

### 1.3 Create OAuth Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. Application type: **"Web application"**
4. Name: `Calendar Sync`
5. **Authorized redirect URIs** - Add:
   - Local: `http://localhost:8033/api/oauth/callback`
   - Production: `https://yourdomain.com/api/oauth/callback`
6. Click **"Create"**
7. **Copy Client ID and Client Secret** (you'll need these next)

---

## Step 2: Deploy with Docker

### 2.1 Create Environment File

```bash
# Create .env.local file
cat > .env.local << 'EOF'
# Docker Image
DOCKER_IMAGE=ghcr.io/chriskoch/cal-sync:latest

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=CHANGE_ME
POSTGRES_DB=calsync

# Google OAuth (from Step 1.3)
OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
OAUTH_CLIENT_SECRET=your-client-secret

# Security Keys (generate below)
JWT_SECRET=GENERATE_ME
ENCRYPTION_KEY=GENERATE_ME

# Optional
SYNC_LOOKAHEAD_DAYS=90
EOF
```

### 2.2 Generate Security Keys

```bash
# Generate JWT secret
openssl rand -base64 32

# Generate encryption key
openssl rand -base64 32

# Generate database password
openssl rand -base64 24
```

Copy each output and paste into `.env.local`.

### 2.3 Create docker-compose.yml

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  db:
    image: postgres:15
    platform: linux/amd64
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-calsync}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  app:
    image: ${DOCKER_IMAGE:-ghcr.io/chriskoch/cal-sync:latest}
    env_file:
      - .env.local
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-calsync}
      ENVIRONMENT: production
      DEBUG: "false"
      API_URL: ${API_URL:-http://localhost:8033}
      FRONTEND_URL: ${FRONTEND_URL:-http://localhost:8033}
    ports:
      - "${EXTERNAL_PORT:-8033}:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres_data:
EOF
```

### 2.4 Start Services

```bash
# Pull the latest image
docker pull ghcr.io/chriskoch/cal-sync:latest

# Start everything
docker compose up -d

# Check logs
docker compose logs -f app
```

**Access**: Open http://localhost:8033

---

## Step 3: Configure Reverse Proxy (Production)

For production deployment with a custom domain:

### 3.1 Update .env.local

```bash
# Add to .env.local
API_URL=https://yourdomain.com
FRONTEND_URL=https://yourdomain.com
```

### 3.2 Update OAuth Redirect URI

In Google Cloud Console, ensure your redirect URI is:
```
https://yourdomain.com/api/oauth/callback
```

### 3.3 Configure Reverse Proxy

**Example: nginx proxy manager**
- Domain: `yourdomain.com`
- Forward to: `localhost:8033`
- SSL: Enable (Let's Encrypt)
- WebSockets: Enable

**Example: Caddy**
```caddy
yourdomain.com {
    reverse_proxy localhost:8033
}
```

**Example: nginx**
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8033;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3.4 Restart Services

```bash
docker compose down
docker compose up -d
```

---

## Step 4: First Use

1. **Open Cal-Sync** in your browser
   - Local: http://localhost:8033
   - Production: https://yourdomain.com

2. **Click "Sign in with Google"**
   - Use a Google account you added as a test user
   - Authorize the app
   - This becomes your **source calendar**

3. **Connect Destination Account**
   - Click "Connect Destination Google Account"
   - Sign in with your second Google account
   - Authorize

4. **Create Sync Configuration**
   - Select source calendar
   - Select destination calendar
   - Choose sync direction:
     - **One-way**: Source → Destination only
     - **Bi-directional**: Both ways
   - Set event color preference
   - **Optional**: Enable auto-sync (cron schedule)

5. **Test Sync**
   - Click "Sync Now"
   - View results and history

---

## Troubleshooting

### Error 403: access_denied

**Cause**: Your Google account is not in the test users list.

**Fix**:
1. Go to [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)
2. Click **"Edit App"**
3. Scroll to **"Test users"**
4. Click **"+ Add Users"**
5. Add the email you're trying to use
6. **Save** and try again

### Error 400: redirect_uri_mismatch

**Cause**: Redirect URI doesn't match Google Console settings.

**Fix**:
1. Check your redirect URI format:
   - Local: `http://localhost:8033/api/oauth/callback`
   - Production: `https://yourdomain.com/api/oauth/callback`
2. No trailing slash!
3. Update in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)

### Container won't start

**Check logs**:
```bash
docker compose logs app
docker compose logs db
```

**Common fixes**:
```bash
# Restart services
docker compose down
docker compose up -d

# Reset everything (deletes data!)
docker compose down -v
docker compose up -d
```

### Events not syncing

**Checks**:
1. Verify both OAuth accounts connected (check Dashboard)
2. Check sync logs (Dashboard → View History)
3. Verify Google Calendar API is enabled in GCP
4. Check API logs: `docker compose logs app | grep ERROR`

---

## Updating Cal-Sync

```bash
# Pull latest image
docker pull ghcr.io/chriskoch/cal-sync:latest

# Restart
docker compose down
docker compose up -d
```

Database migrations run automatically on startup.

---

## Backup & Restore

### Backup

```bash
# Backup database
docker exec cal-sync-app sh -c "pg_dump -U postgres -d calsync" > backup.sql
```

### Restore

```bash
# Restore database
docker exec -i cal-sync-app sh -c "psql -U postgres -d calsync" < backup.sql
```

---

## Security Checklist

Before production deployment:

- [ ] Strong passwords generated (24+ characters)
- [ ] `ENVIRONMENT=production` and `DEBUG=false` set
- [ ] Using HTTPS (not HTTP)
- [ ] OAuth redirect URI uses HTTPS
- [ ] `.env.local` is NOT committed to git
- [ ] Firewall configured (only ports 80, 443 public)
- [ ] Regular backups scheduled
- [ ] Test users added in Google OAuth

---

## Advanced Configuration

### Change Port

Edit `.env.local`:
```bash
EXTERNAL_PORT=8080
API_URL=http://localhost:8080
FRONTEND_URL=http://localhost:8080
```

Update OAuth redirect URI to match.

### Database Connection

For external PostgreSQL:
```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### Sync Settings

```bash
# Days to sync ahead (default: 90)
SYNC_LOOKAHEAD_DAYS=120
```

---

## Need Help?

- **Documentation**: [README.md](README.md) for features
- **Development**: [DEVELOPMENT.md](DEVELOPMENT.md) for local dev
- **Technical Details**: [CLAUDE.md](CLAUDE.md) for architecture
- **Issues**: [GitHub Issues](https://github.com/chriskoch/cal-sync/issues)

---

**That's it!** Cal-Sync is ready. Happy syncing! 🎉
