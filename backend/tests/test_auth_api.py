"""
Integration tests for authentication API endpoints.
"""
import pytest
from fastapi import status


@pytest.mark.integration
@pytest.mark.auth
class TestGetCurrentUser:
    """Test get current user endpoint."""

    def test_get_current_user_authenticated(self, client, test_user, auth_headers):
        """Test getting current user when authenticated."""
        response = client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert data["id"] == str(test_user.id)
        assert "hashed_password" not in data

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token fails."""
        response = client.get("/api/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token fails."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_malformed_header(self, client):
        """Test getting current user with malformed auth header fails."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "NotBearer token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
