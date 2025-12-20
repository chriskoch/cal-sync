"""
Test utilities and helper functions for common test patterns.
"""
from typing import Dict, Any
from app.models.user import User
from app.models.oauth_token import OAuthToken
from app.core.security import encrypt_token
from datetime import datetime, timedelta


def create_test_user(db, email: str = "test@example.com", **kwargs) -> User:
    """
    Helper function to create a test user.
    
    Args:
        db: Database session
        email: User email (default: "test@example.com")
        **kwargs: Additional user attributes
    
    Returns:
        Created User instance
    """
    user = User(
        email=email,
        full_name=kwargs.get("full_name", "Test User"),
        is_active=kwargs.get("is_active", True),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_oauth_token(
    db,
    user: User,
    account_type: str = "source",
    google_email: str = "test@example.com",
    **kwargs
) -> OAuthToken:
    """
    Helper function to create an OAuth token.
    
    Args:
        db: Database session
        user: User instance
        account_type: "source" or "destination"
        google_email: Google account email
        **kwargs: Additional token attributes
    
    Returns:
        Created OAuthToken instance
    """
    token = OAuthToken(
        user_id=user.id,
        account_type=account_type,
        google_email=google_email,
        access_token_encrypted=encrypt_token(kwargs.get("access_token", "test_access_token")),
        refresh_token_encrypted=encrypt_token(kwargs.get("refresh_token", "test_refresh_token")) if kwargs.get("refresh_token") else None,
        token_expiry=kwargs.get("token_expiry", datetime.utcnow() + timedelta(hours=1)),
        scopes=kwargs.get("scopes", ["https://www.googleapis.com/auth/calendar"]),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def assert_response_success(response, expected_status: int = 200):
    """
    Assert that a response is successful.
    
    Args:
        response: HTTP response object
        expected_status: Expected status code (default: 200)
    """
    assert response.status_code == expected_status, \
        f"Expected status {expected_status}, got {response.status_code}. Response: {response.text}"


def assert_response_error(response, expected_status: int, error_keyword: str = None):
    """
    Assert that a response is an error.
    
    Args:
        response: HTTP response object
        expected_status: Expected status code
        error_keyword: Optional keyword that should be in error message
    """
    assert response.status_code == expected_status, \
        f"Expected status {expected_status}, got {response.status_code}. Response: {response.text}"
    
    if error_keyword:
        error_text = response.json().get("detail", "").lower()
        assert error_keyword.lower() in error_text, \
            f"Expected '{error_keyword}' in error message, got: {error_text}"

