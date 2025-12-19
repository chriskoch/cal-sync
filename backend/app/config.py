from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    database_url: str = "postgresql://postgres:dev@localhost:5432/calsync"

    # Google OAuth
    oauth_client_id: str
    oauth_client_secret: str

    # Security
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    encryption_key: str  # Fernet key for OAuth token encryption

    # API URLs
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Calendar API scopes
    google_calendar_scopes: list[str] = ["https://www.googleapis.com/auth/calendar"]

    # Sync settings
    sync_lookahead_days: int = 90

    # Environment
    environment: str = "development"
    debug: bool = True


settings = Settings()
