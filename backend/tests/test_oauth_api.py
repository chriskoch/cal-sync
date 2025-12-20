"""
Integration tests for OAuth API endpoints.
"""
import pytest
from fastapi import status
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from app.models.oauth_token import OAuthToken
from app.core.security import encrypt_token
from tests.test_utils import assert_response_success, assert_response_error


@pytest.mark.integration
@pytest.mark.oauth
class TestStartOAuth:
    """Test OAuth initiation endpoint."""

    @patch('app.api.oauth.create_flow')
    def test_start_oauth_for_source_account(self, mock_create_flow, client, auth_headers, mock_oauth_flow):
        """Test starting OAuth flow for source account."""
        mock_create_flow.return_value = mock_oauth_flow

        response = client.get("/oauth/start/source", headers=auth_headers)

        assert_response_success(response)
        data = response.json()
        assert "authorization_url" in data
        assert "accounts.google.com" in data["authorization_url"]
        assert "state=" in data["authorization_url"]

    @patch('app.api.oauth.create_flow')
    def test_start_oauth_for_destination_account(self, mock_create_flow, client, auth_headers, mock_oauth_flow):
        """Test starting OAuth flow for destination account."""
        mock_create_flow.return_value = mock_oauth_flow

        response = client.get("/oauth/start/destination", headers=auth_headers)

        assert_response_success(response)
        data = response.json()
        assert "authorization_url" in data

    def test_start_oauth_requires_authentication(self, client):
        """Test OAuth start requires authentication for source/destination."""
        response = client.get("/oauth/start/source")
        assert_response_error(response, status.HTTP_401_UNAUTHORIZED)

    @patch('app.api.oauth.create_flow')
    def test_start_oauth_register_no_auth_required(self, mock_create_flow, client, mock_oauth_flow):
        """Test OAuth registration doesn't require authentication."""
        mock_create_flow.return_value = mock_oauth_flow

        response = client.get("/oauth/start/register")

        assert_response_success(response)
        data = response.json()
        assert "authorization_url" in data

    @patch('app.api.oauth.create_flow')
    def test_start_oauth_invalid_account_type(self, mock_create_flow, client, auth_headers):
        """Test OAuth start with invalid account type."""
        response = client.get("/oauth/start/invalid", headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
@pytest.mark.oauth
class TestOAuthCallback:
    """Test OAuth callback endpoint."""

    @patch('googleapiclient.discovery.build')
    @patch('app.api.oauth.create_flow')
    @patch('app.api.oauth.oauth_states')
    def test_oauth_callback_creates_new_token(
        self, mock_states, mock_create_flow, mock_build, 
        client, db, test_user, mock_oauth_credentials, mock_google_calendar_api
    ):
        """Test OAuth callback creates new token record."""
        # Setup state
        state_token = "test_state_123"
        mock_states.__getitem__ = Mock(return_value={
            "user_id": str(test_user.id),
            "account_type": "source",
        })
        mock_states.pop = Mock(return_value={
            "user_id": str(test_user.id),
            "account_type": "source",
        })

        # Mock OAuth flow
        mock_flow = Mock()
        mock_flow.credentials = mock_oauth_credentials
        mock_create_flow.return_value = mock_flow

        # Mock Google Calendar API
        mock_build.return_value = mock_google_calendar_api

        response = client.get(
            f"/oauth/callback?code=test_code&state={state_token}",
            follow_redirects=False
        )

        # Should redirect to frontend
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert "dashboard?oauth_success=source" in response.headers["location"]

        # Verify token was saved
        token = db.query(OAuthToken).filter(
            OAuthToken.user_id == test_user.id,
            OAuthToken.account_type == "source"
        ).first()
        assert token is not None
        assert token.google_email == "test@example.com"
        assert token.access_token_encrypted is not None
        assert token.refresh_token_encrypted is not None

    @patch('googleapiclient.discovery.build')
    @patch('app.api.oauth.create_flow')
    @patch('app.api.oauth.oauth_states')
    def test_oauth_callback_updates_existing_token(
        self, mock_states, mock_create_flow, mock_build, 
        client, db, test_user, mock_oauth_credentials, mock_google_calendar_api
    ):
        """Test OAuth callback updates existing token record."""
        # Create existing token
        existing_token = OAuthToken(
            user_id=test_user.id,
            account_type="source",
            google_email="old@example.com",
            access_token_encrypted=encrypt_token("old_access_token"),
            refresh_token_encrypted=encrypt_token("old_refresh_token"),
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        db.add(existing_token)
        db.commit()

        # Setup state
        state_token = "test_state_456"
        mock_states.pop = Mock(return_value={
            "user_id": str(test_user.id),
            "account_type": "source",
        })

        # Mock OAuth flow
        mock_flow = Mock()
        mock_oauth_credentials.token = "new_access_token"
        mock_oauth_credentials.refresh_token = "new_refresh_token"
        mock_flow.credentials = mock_oauth_credentials
        mock_create_flow.return_value = mock_flow

        # Mock Google Calendar API with different email
        mock_google_calendar_api.calendarList().get().execute.return_value = {
            "id": "new@example.com"
        }
        mock_build.return_value = mock_google_calendar_api

        response = client.get(
            f"/oauth/callback?code=new_code&state={state_token}",
            follow_redirects=False
        )

        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT

        # Verify token was updated (not duplicated)
        tokens = db.query(OAuthToken).filter(
            OAuthToken.user_id == test_user.id,
            OAuthToken.account_type == "source"
        ).all()
        assert len(tokens) == 1
        assert tokens[0].google_email == "new@example.com"

    def test_oauth_callback_invalid_state(self, client):
        """Test OAuth callback with invalid state token."""
        response = client.get(
            "/oauth/callback?code=test_code&state=invalid_state",
            follow_redirects=False
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid state token" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.oauth
class TestOAuthStatus:
    """Test OAuth status endpoint."""

    def test_oauth_status_no_connections(self, client, auth_headers, db, test_user):
        """Test status when no OAuth tokens exist."""
        response = client.get("/oauth/status", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["source_connected"] is False
        assert data["source_email"] is None
        assert data["destination_connected"] is False
        assert data["destination_email"] is None

    def test_oauth_status_source_connected(self, client, auth_headers, db, test_user):
        """Test status when source account is connected."""
        source_token = OAuthToken(
            user_id=test_user.id,
            account_type="source",
            google_email="source@example.com",
            access_token_encrypted=encrypt_token("test_token"),
            refresh_token_encrypted=encrypt_token("test_refresh"),
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        db.add(source_token)
        db.commit()

        response = client.get("/oauth/status", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["source_connected"] is True
        assert data["source_email"] == "source@example.com"
        assert data["destination_connected"] is False
        assert data["destination_email"] is None

    def test_oauth_status_both_connected(self, client, auth_headers, db, test_user):
        """Test status when both accounts are connected."""
        source_token = OAuthToken(
            user_id=test_user.id,
            account_type="source",
            google_email="source@example.com",
            access_token_encrypted=encrypt_token("source_token"),
            refresh_token_encrypted=encrypt_token("source_refresh"),
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        dest_token = OAuthToken(
            user_id=test_user.id,
            account_type="destination",
            google_email="dest@example.com",
            access_token_encrypted=encrypt_token("dest_token"),
            refresh_token_encrypted=encrypt_token("dest_refresh"),
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        db.add(source_token)
        db.add(dest_token)
        db.commit()

        response = client.get("/oauth/status", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["source_connected"] is True
        assert data["source_email"] == "source@example.com"
        assert data["destination_connected"] is True
        assert data["destination_email"] == "dest@example.com"

    def test_oauth_status_requires_authentication(self, client):
        """Test OAuth status requires authentication."""
        response = client.get("/oauth/status")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
@pytest.mark.oauth
class TestGetCredentialsFromDB:
    """Test get_credentials_from_db helper function."""

    def test_get_credentials_from_db_success(self, db, test_user):
        """Test successfully loading credentials from database."""
        from app.api.oauth import get_credentials_from_db

        # Create token in database
        token = OAuthToken(
            user_id=test_user.id,
            account_type="source",
            google_email="test@example.com",
            access_token_encrypted=encrypt_token("test_access"),
            refresh_token_encrypted=encrypt_token("test_refresh"),
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        db.add(token)
        db.commit()

        # Load credentials
        creds = get_credentials_from_db(str(test_user.id), "source", db)

        assert creds is not None
        assert creds.token == "test_access"
        assert creds.refresh_token == "test_refresh"
        assert creds.scopes == ["https://www.googleapis.com/auth/calendar"]

    def test_get_credentials_from_db_not_found(self, db, test_user):
        """Test loading credentials when token doesn't exist."""
        from app.api.oauth import get_credentials_from_db

        creds = get_credentials_from_db(str(test_user.id), "source", db)

        assert creds is None

    def test_get_credentials_from_db_handles_no_refresh_token(self, db, test_user):
        """Test loading credentials when refresh token is None."""
        from app.api.oauth import get_credentials_from_db

        token = OAuthToken(
            user_id=test_user.id,
            account_type="source",
            google_email="test@example.com",
            access_token_encrypted=encrypt_token("test_access"),
            refresh_token_encrypted=None,  # No refresh token
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        db.add(token)
        db.commit()

        creds = get_credentials_from_db(str(test_user.id), "source", db)

        assert creds is not None
        assert creds.token == "test_access"
        assert creds.refresh_token is None


@pytest.mark.integration
@pytest.mark.oauth
class TestOAuthRegistration:
    """Test OAuth registration flow."""

    @patch('googleapiclient.discovery.build')
    @patch('app.api.oauth.create_flow')
    @patch('app.api.oauth.oauth_states')
    def test_oauth_registration_creates_user_and_source_token(
        self, mock_states, mock_create_flow, mock_build, 
        client, db, mock_oauth_credentials, mock_google_calendar_api
    ):
        """Test OAuth registration creates new user and source OAuth token."""
        from app.models.user import User
        
        # Setup state for registration
        state_token = "test_registration_state"
        mock_states.pop = Mock(return_value={
            "account_type": "register",
        })

        # Mock OAuth flow
        mock_flow = Mock()
        mock_flow.credentials = mock_oauth_credentials
        mock_create_flow.return_value = mock_flow

        # Mock Google Calendar API with new user email
        mock_google_calendar_api.calendarList().get().execute.return_value = {
            "id": "newuser@example.com"
        }
        mock_build.return_value = mock_google_calendar_api

        # Verify user doesn't exist
        existing_user = db.query(User).filter(User.email == "newuser@example.com").first()
        assert existing_user is None

        response = client.get(
            f"/oauth/callback?code=test_code&state={state_token}",
            follow_redirects=False
        )

        # Should redirect to frontend with token
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert "dashboard?token=" in response.headers["location"]

        # Verify user was created
        user = db.query(User).filter(User.email == "newuser@example.com").first()
        assert user is not None
        assert user.is_active is True

        # Verify source token was created
        token = db.query(OAuthToken).filter(
            OAuthToken.user_id == user.id,
            OAuthToken.account_type == "source"
        ).first()
        assert token is not None
        assert token.google_email == "newuser@example.com"

    @patch('googleapiclient.discovery.build')
    @patch('app.api.oauth.create_flow')
    @patch('app.api.oauth.oauth_states')
    def test_oauth_registration_existing_user_updates_source_token(
        self, mock_states, mock_create_flow, mock_build, 
        client, db, test_user, mock_oauth_credentials, mock_google_calendar_api
    ):
        """Test OAuth registration with existing user updates source token."""
        # Setup state for registration
        state_token = "test_registration_state_existing"
        mock_states.pop = Mock(return_value={
            "account_type": "register",
        })

        # Mock OAuth flow
        mock_flow = Mock()
        mock_oauth_credentials.token = "new_access_token"
        mock_oauth_credentials.refresh_token = "new_refresh_token"
        mock_flow.credentials = mock_oauth_credentials
        mock_create_flow.return_value = mock_flow

        # Mock Google Calendar API (return test_user email)
        mock_google_calendar_api.calendarList().get().execute.return_value = {
            "id": test_user.email
        }
        mock_build.return_value = mock_google_calendar_api

        response = client.get(
            f"/oauth/callback?code=test_code&state={state_token}",
            follow_redirects=False
        )

        # Should redirect to frontend with token
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert "dashboard?token=" in response.headers["location"]

        # Verify source token was created/updated
        token = db.query(OAuthToken).filter(
            OAuthToken.user_id == test_user.id,
            OAuthToken.account_type == "source"
        ).first()
        assert token is not None
        assert token.google_email == test_user.email
