#!/usr/bin/env python3
"""Simple OAuth test - just generate the auth URL without opening browser."""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDS_PATH = "creds/source/credentials.json"

print("Testing OAuth configuration...")
print(f"Using credentials from: {CREDS_PATH}\n")

try:
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)

    # Get the authorization URL without starting the server
    auth_url, _ = flow.authorization_url(prompt='consent')

    print("✓ Credentials file is valid")
    print("✓ OAuth flow initialized successfully")
    print(f"\nAuthorization URL generated:\n{auth_url}\n")
    print("If you open this URL in your browser, you should see:")
    print("- The OAuth consent screen for 'Calendar Sync'")
    print("- Option to sign in with christian@livelyapps.com")
    print("\nIf you see an error page instead, the consent screen isn't configured properly.")

except Exception as e:
    print(f"✗ Error: {e}")
