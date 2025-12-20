from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from typing import Literal, Optional
import secrets
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.oauth_token import OAuthToken
from app.core.security import encrypt_token, decrypt_token, create_access_token, decode_access_token
from app.api.auth import get_current_user
from app.config import settings

# Optional OAuth2 scheme for registration endpoint
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/oauth/start/register", auto_error=False)

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


def get_current_user_optional(
    token: Optional[str] = Security(oauth2_scheme_optional),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional dependency to get current authenticated user.
    
    Returns None if no token provided or token is invalid.
    Used for endpoints that work with or without authentication.
    """
    if token is None:
        return None
    try:
        # Reuse get_current_user logic but return None instead of raising
        payload = decode_access_token(token)
        if payload is None:
            return None
        user_id = payload.get("sub")
        if user_id is None:
            return None
        try:
            user_uuid = UUID(user_id)
        except (ValueError, AttributeError):
            return None
        user = db.query(User).filter(User.id == user_uuid).first()
        if user is None or not user.is_active:
            return None
        return user
    except Exception:
        return None


@router.get("/start/{account_type}", response_model=OAuthStartResponse)
def start_oauth(
    account_type: Literal["source", "destination", "register"],
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Initiate Web OAuth flow for registration, source, or destination account.
    
    - "register": Unauthenticated registration/login via Google OAuth
    - "source": Connect source account (requires authentication)
    - "destination": Connect destination account (requires authentication)
    """
    # For source/destination, require authentication
    if account_type != "register":
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
    
    redirect_uri = f"{settings.api_url}/oauth/callback"
    flow = create_flow(redirect_uri)

    # Generate state token with user_id and account_type
    state_token = secrets.token_urlsafe(32)
    state_data = {
        "account_type": account_type,
    }
    
    # Only include user_id if authenticated (for source/destination)
    if account_type != "register" and current_user:
        state_data["user_id"] = str(current_user.id)
    
    oauth_states[state_token] = state_data

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
    For registration: Creates user and source OAuth token, generates JWT.
    For source/destination: Stores encrypted tokens in database.
    """
    # Validate state token
    state_data = oauth_states.pop(state, None)
    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state token",
        )

    account_type = state_data["account_type"]
    user_id = state_data.get("user_id")  # May not exist for registration

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

    # Handle registration flow
    if account_type == "register":
        # Check if user already exists by email
        existing_user = db.query(User).filter(User.email == google_email).first()
        
        if existing_user:
            # Security: Reject registration attempts for existing users
            # This prevents attackers from overwriting OAuth tokens by gaining access to a victim's Google account
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with email {google_email} already exists. Please sign in instead.",
            )
        
        # Create new user
        user = User(
            email=google_email,
            full_name=None,  # Could be extracted from Google profile if needed
            is_active=True,
        )
        db.add(user)
        db.flush()  # Flush to get user.id
        
        # Create source OAuth token for new user
        _upsert_oauth_token(
            db=db,
            user_id=str(user.id),
            account_type="source",
            google_email=google_email,
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_expiry=creds.expiry,
            scopes=creds.scopes,
        )
        db.commit()

        # Generate JWT token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        # Redirect to frontend with JWT token
        return RedirectResponse(url=f"{settings.frontend_url}/dashboard?token={access_token}")
    
    # Handle source/destination connection (existing flow)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID missing from state",
        )

    # Store in database (upsert)
    _upsert_oauth_token(
        db=db,
        user_id=user_id,
        account_type=account_type,
        google_email=google_email,
        access_token_encrypted=access_token_encrypted,
        refresh_token_encrypted=refresh_token_encrypted,
        token_expiry=creds.expiry,
        scopes=creds.scopes,
    )
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


def _upsert_oauth_token(
    db: Session,
    user_id: str,
    account_type: str,
    google_email: str,
    access_token_encrypted: str,
    refresh_token_encrypted: Optional[str],
    token_expiry,
    scopes: list,
) -> OAuthToken:
    """Helper function to create or update OAuth token.
    
    Args:
        user_id: User ID as string (will be converted to UUID)
        account_type: "source" or "destination"
        google_email: Google account email
        access_token_encrypted: Encrypted access token
        refresh_token_encrypted: Encrypted refresh token (optional)
        token_expiry: Token expiration datetime
        scopes: OAuth scopes list
    """
    # Convert string user_id to UUID
    user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
    
    existing_token = db.query(OAuthToken).filter(
        OAuthToken.user_id == user_uuid,
        OAuthToken.account_type == account_type,
    ).first()

    if existing_token:
        existing_token.google_email = google_email
        existing_token.access_token_encrypted = access_token_encrypted
        existing_token.refresh_token_encrypted = refresh_token_encrypted
        existing_token.token_expiry = token_expiry
        existing_token.scopes = scopes
        return existing_token
    else:
        new_token = OAuthToken(
            user_id=user_uuid,
            account_type=account_type,
            google_email=google_email,
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_expiry=token_expiry,
            scopes=scopes,
        )
        db.add(new_token)
        return new_token


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