import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]
# Bind on loopback to avoid permission issues; override via env if needed.
OAUTH_PORT = int(os.getenv("OAUTH_PORT", "8765"))
OAUTH_HOST = os.getenv("OAUTH_HOST", "127.0.0.1")


def load_credentials(creds_dir: str, label: str) -> Credentials:
    """Load or create credentials for a specific calendar."""
    creds_path = os.path.join(creds_dir, "credentials.json")
    token_path = os.path.join(creds_dir, "token.json")

    if not os.path.exists(creds_path):
        raise SystemExit(
            f"credentials.json not found in {creds_dir}/\n"
            f"Run: terraform output -raw client_secret > {creds_path}"
        )

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print(f"Refreshing expired token for {label}...")
            creds.refresh(Request())
        else:
            print(f"\nAuthenticating {label}...")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
            auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
            print(f"Open this URL to authorize {label}:\n{auth_url}")
            code = os.getenv("AUTH_CODE")
            if not code:
                try:
                    code = input("Enter the authorization code: ").strip()
                except EOFError:
                    raise SystemExit(
                        "No authorization code provided. Set AUTH_CODE env var or run interactively."
                    )
            if not code:
                raise SystemExit("Authorization code is required to continue.")
            flow.fetch_token(code=code)
            creds = flow.credentials
        with open(token_path, "w") as token:
            token.write(creds.to_json())
        print(f"✓ Token saved to {token_path}")

    return creds


def main():
    print("=" * 60)
    print("Calendar Sync - Dual OAuth Authentication")
    print("=" * 60)

    # Authenticate source calendar
    print("\n[1/2] SOURCE Calendar")
    print("Account: christian@livelyapps.com")
    load_credentials("creds/source", "SOURCE calendar (christian@livelyapps.com)")

    # Prompt before second authentication
    print("\n" + "=" * 60)
    input("Press Enter to authenticate DESTINATION calendar...")
    print("=" * 60)

    # Authenticate destination calendar
    print("\n[2/2] DESTINATION Calendar")
    print("Account: koch.chris@gmail.com")
    print("Calendar: 4bd46f6a...@group.calendar.google.com")
    load_credentials("creds/dest", "DESTINATION calendar (koch.chris@gmail.com)")

    print("\n" + "=" * 60)
    print("✓ Both calendars authenticated successfully!")
    print("=" * 60)
    print("\nYou can now run: python sync.py")


if __name__ == "__main__":
    main()
