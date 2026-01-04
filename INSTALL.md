# Installation Guide

Simple guide to get Calendar Sync running in 15 minutes.

## Prerequisites

- Docker and Docker Compose installed
- A Google account
- (Optional) A custom domain with HTTPS if deploying to production

## Step 1: Google OAuth Setup

### 1.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Enter project name: `Calendar Sync`
4. Click **"Create"**

### 1.2 Enable Google Calendar API

1. In your new project, go to **"APIs & Services"** → **"Library"**
2. Search for **"Google Calendar API"**
3. Click on it and press **"Enable"**

### 1.3 Configure OAuth Consent Screen

1. Go to **"APIs & Services"** → **"OAuth consent screen"**
2. Select **"External"** user type
3. Click **"Create"**
4. Fill in required fields:
   - **App name:** `Calendar Sync`
   - **User support email:** Your email
   - **Developer contact email:** Your email
5. Click **"Save and Continue"**
6. On **"Scopes"** page:
   - Click **"Add or Remove Scopes"**
   - Search for: `https://www.googleapis.com/auth/calendar`
   - Check the box next to **"Google Calendar API"**
   - Click **"Update"**
   - Click **"Save and Continue"**
7. On **"Test users"** page:
   - Click **"Add Users"**
   - Add your Google email addresses (the ones you'll sync calendars for)
   - Click **"Save and Continue"**
8. Review and click **"Back to Dashboard"**

### 1.4 Create OAuth Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. Select **"Web application"**
4. Enter name: `Calendar Sync Web Client`
5. Under **"Authorized redirect URIs"**, click **"Add URI"** and add:
   - For local testing: `http://localhost:8033/api/oauth/callback`
   - For production: `https://your-domain.com/api/oauth/callback`
6. Click **"Create"**
7. **Important:** Copy your **Client ID** and **Client Secret** - you'll need these next!

## Step 2: Install Calendar Sync

### 2.1 Clone Repository

```bash
git clone https://github.com/yourusername/cal-sync.git
cd cal-sync
```

### 2.2 Create Configuration File

Copy the example configuration:

```bash
cp .env.example .env.local
```

Edit `.env.local` with your favorite text editor:

```bash
nano .env.local
```

### 2.3 Add Your Credentials

Paste your Google OAuth credentials from Step 1.4:

```bash
# Google OAuth Credentials (from Step 1.4)
OAUTH_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
OAUTH_CLIENT_SECRET=your-client-secret-here

# Generate secure secrets (run these commands in terminal)
# Linux/Mac: openssl rand -base64 32
# Windows: use an online base64 generator
JWT_SECRET=paste-your-random-jwt-secret-here
ENCRYPTION_KEY=paste-your-random-encryption-key-here

# Database password (choose a strong password)
POSTGRES_PASSWORD=your-secure-database-password

# Production settings (optional - for HTTPS deployment)
# ENVIRONMENT=production
# DEBUG=false
# API_URL=https://your-domain.com
# FRONTEND_URL=https://your-domain.com
```

**To generate secure secrets:**

```bash
# Run these commands twice to get two different secrets
openssl rand -base64 32
```

Copy the output for `JWT_SECRET` and `ENCRYPTION_KEY`.

Save the file (Ctrl+X, then Y, then Enter in nano).

## Step 3: Deploy

### Option A: Local Testing (localhost)

```bash
# Build the Docker image
docker build -t cal-sync:latest .

# Start the application
docker compose up -d

# Check logs to ensure it started successfully
docker compose logs -f app
```

Access the app at: **http://localhost:8033**

### Option B: Production (with HTTPS domain)

If you're using nginx proxy manager or another reverse proxy:

1. Update `.env.local` with your domain:
   ```bash
   API_URL=https://cal-sync.yourdomain.com
   FRONTEND_URL=https://cal-sync.yourdomain.com
   ENVIRONMENT=production
   DEBUG=false
   ```

2. Deploy:
   ```bash
   docker build -t cal-sync:latest .
   docker compose up -d
   ```

3. Configure your reverse proxy (nginx proxy manager):
   - **Domain:** `cal-sync.yourdomain.com`
   - **Forward to:** `localhost:8033`
   - **Enable SSL:** Yes (Let's Encrypt)
   - **Enable WebSockets:** Yes

## Step 4: First Use

1. Open your Calendar Sync URL in a browser
2. Click **"Sign in with Google"**
3. Authorize with your Google account (the one you added as test user)
4. Your account is automatically connected as the **source calendar**
5. Click **"Connect Destination Account"** to add a second Google account
6. Create your first sync configuration:
   - Select source calendar
   - Select destination calendar
   - Choose event color
   - Enable auto-sync (optional)
7. Click **"Run Sync Now"** to test

## Troubleshooting

### "Error 400: redirect_uri_mismatch"

**Problem:** OAuth redirect URI doesn't match Google Cloud Console settings.

**Solution:**
1. Check your `.env.local` file - what is your `API_URL`?
2. Go to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials)
3. Edit your OAuth client
4. Ensure redirect URI matches: `{API_URL}/api/oauth/callback`
   - Example: `http://localhost:8033/api/oauth/callback`
   - Or: `https://cal-sync.yourdomain.com/api/oauth/callback`

### "Access blocked: This app's request is invalid"

**Problem:** Redirect URI is missing from Google OAuth client.

**Solution:**
1. Go to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials)
2. Edit your OAuth client
3. Add the redirect URI: `http://localhost:8033/api/oauth/callback`

### Container won't start

**Check logs:**
```bash
docker compose logs app
```

**Common issues:**
- Missing environment variables in `.env.local`
- Invalid `ENCRYPTION_KEY` format (must be base64, 32 bytes)
- Database connection failed (check `POSTGRES_PASSWORD`)

**Restart services:**
```bash
docker compose down
docker compose up -d
```

### Database errors

**Reset database:**
```bash
docker compose down -v  # WARNING: This deletes all data!
docker compose up -d
```

## Update Calendar Sync

```bash
# Pull latest code
git pull origin main

# Rebuild Docker image
docker build -t cal-sync:latest .

# Restart containers
docker compose down
docker compose up -d
```

## Need Help?

- Check the [README.md](README.md) for detailed documentation
- Review [DEVELOPMENT.md](DEVELOPMENT.md) for development setup
- Open an issue on GitHub

## Security Checklist

Before going to production:

- [ ] Generated strong random secrets for `JWT_SECRET` and `ENCRYPTION_KEY`
- [ ] Set a strong `POSTGRES_PASSWORD`
- [ ] Set `ENVIRONMENT=production` and `DEBUG=false` in `.env.local`
- [ ] Using HTTPS (not HTTP) in production
- [ ] OAuth redirect URI uses HTTPS
- [ ] `.env.local` is NOT committed to git (it's in `.gitignore`)
- [ ] Firewall configured (only ports 80, 443 exposed publicly)
- [ ] Regular database backups configured

---

**That's it!** Your Calendar Sync should now be running. Happy syncing! 🎉
