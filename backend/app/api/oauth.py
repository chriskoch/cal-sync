from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from typing import Literal, Optional
import secrets

from app.database import get_db
from app.models.user import User
from app.models.oauth_token import OAuthToken
from app.core.security import encrypt_token, decrypt_token
from app.api.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/oauth", tags=["oauth"])

# In-memory state storage (in production, use Redis)
oauth_states = {}


def create_flow(redirect_uri: str) -> Flow:
    """Create OAuth flow for Web application (migrated from auth.py Desktop flow)."""
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.oauth_client_id,
                "client_secret": settings.oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [f"{settings.api_url}/oauth/callback"],
            }
        },
        scopes=settings.google_calendar_scopes,
        redirect_uri=redirect_uri,
    )


class OAuthStartResponse(BaseModel):
    authorization_url: str


class OAuthStatusResponse(BaseModel):
    source_connected: bool
    source_email: Optional[str]
    destination_connected: bool
    destination_email: Optional[str]


@router.get("/start/{account_type}", response_model=OAuthStartResponse)
def start_oauth(
    account_type: Literal["source", "destination"],
    current_user: User = Depends(get_current_user),
):
    """
    Initiate Web OAuth flow for source or destination account.

    Migrated from auth.py lines 33-36 (Desktop OOB flow → Web redirect flow).
    """
    redirect_uri = f"{settings.api_url}/oauth/callback"
    flow = create_flow(redirect_uri)

    # Generate state token with user_id and account_type
    state_token = secrets.token_urlsafe(32)
    oauth_states[state_token] = {
        "user_id": str(current_user.id),
        "account_type": account_type,
    }

    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state_token,
    )

    return {"authorization_url": authorization_url}


@router.get("/callback")
def oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    """
    Handle OAuth callback from Google.

    Receives authorization code and exchanges it for tokens.
    Stores encrypted tokens in database.
    """
    # Validate state token
    state_data = oauth_states.pop(state, None)
    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state token",
        )

    user_id = state_data["user_id"]
    account_type = state_data["account_type"]

    # Exchange code for tokens
    redirect_uri = f"{settings.api_url}/oauth/callback"
    flow = create_flow(redirect_uri)
    flow.fetch_token(code=code)

    creds = flow.credentials

    # Get user email from Google
    from googleapiclient.discovery import build
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    calendar_list = service.calendarList().get(calendarId="primary").execute()
    google_email = calendar_list.get("id", "")

    # Encrypt tokens
    access_token_encrypted = encrypt_token(creds.token)
    refresh_token_encrypted = encrypt_token(creds.refresh_token) if creds.refresh_token else None

    # Store in database (upsert)
    existing_token = db.query(OAuthToken).filter(
        OAuthToken.user_id == user_id,
        OAuthToken.account_type == account_type,
    ).first()

    if existing_token:
        existing_token.google_email = google_email
        existing_token.access_token_encrypted = access_token_encrypted
        existing_token.refresh_token_encrypted = refresh_token_encrypted
        existing_token.token_expiry = creds.expiry
        existing_token.scopes = creds.scopes
    else:
        new_token = OAuthToken(
            user_id=user_id,
            account_type=account_type,
            google_email=google_email,
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_expiry=creds.expiry,
            scopes=creds.scopes,
        )
        db.add(new_token)

    db.commit()

    # Redirect to frontend success page
    return RedirectResponse(url=f"{settings.frontend_url}/dashboard?oauth_success={account_type}")


@router.get("/status", response_model=OAuthStatusResponse)
def get_oauth_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get OAuth connection status for source and destination accounts."""
    source_token = db.query(OAuthToken).filter(
        OAuthToken.user_id == current_user.id,
        OAuthToken.account_type == "source",
    ).first()

    dest_token = db.query(OAuthToken).filter(
        OAuthToken.user_id == current_user.id,
        OAuthToken.account_type == "destination",
    ).first()

    return {
        "source_connected": source_token is not None,
        "source_email": source_token.google_email if source_token else None,
        "destination_connected": dest_token is not None,
        "destination_email": dest_token.google_email if dest_token else None,
    }


def get_credentials_from_db(user_id: str, account_type: str, db: Session) -> Optional[Credentials]:
    """Helper to get Google Credentials from encrypted database tokens."""
    token_record = db.query(OAuthToken).filter(
        OAuthToken.user_id == user_id,
        OAuthToken.account_type == account_type,
    ).first()

    if not token_record:
        return None

    # Decrypt tokens
    access_token = decrypt_token(token_record.access_token_encrypted)
    refresh_token = decrypt_token(token_record.refresh_token_encrypted) if token_record.refresh_token_encrypted else None

    # Build Credentials object
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.oauth_client_id,
        client_secret=settings.oauth_client_secret,
        scopes=token_record.scopes,
    )

    return creds
