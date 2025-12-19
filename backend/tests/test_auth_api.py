"""
Integration tests for authentication API endpoints.
"""
import pytest
from fastapi import status


@pytest.mark.integration
@pytest.mark.auth
class TestUserRegistration:
    """Test user registration endpoint."""

    def test_register_new_user(self, client):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User"
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["is_active"] is True
        assert "id" in data
        assert "hashed_password" not in data  # Password should not be returned

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": test_user.email,
                "password": "anotherpassword",
                "full_name": "Another User"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Test registration with invalid email fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepassword123",
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_without_password(self, client):
        """Test registration without password fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
@pytest.mark.auth
class TestUserLogin:
    """Test user login endpoint."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/auth/token",
            data={
                "username": test_user.email,
                "password": "testpassword123"
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password fails."""
        response = client.post(
            "/auth/token",
            data={
                "username": test_user.email,
                "password": "wrongpassword"
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user fails."""
        response = client.post(
            "/auth/token",
            data={
                "username": "nonexistent@example.com",
                "password": "somepassword"
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_credentials(self, client):
        """Test login without credentials fails."""
        response = client.post("/auth/token", data={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
@pytest.mark.auth
class TestGetCurrentUser:
    """Test get current user endpoint."""

    def test_get_current_user_authenticated(self, client, test_user, auth_headers):
        """Test getting current user when authenticated."""
        response = client.get("/auth/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert data["id"] == str(test_user.id)
        assert "hashed_password" not in data

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token fails."""
        response = client.get("/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token fails."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_malformed_header(self, client):
        """Test getting current user with malformed auth header fails."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "NotBearer token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.auth
class TestAuthenticationFlow:
    """Test complete authentication flow."""

    def test_register_login_get_user_flow(self, client):
        """Test complete flow: register -> login -> get user."""
        # 1. Register new user
        register_response = client.post(
            "/auth/register",
            json={
                "email": "flowtest@example.com",
                "password": "testpass123",
                "full_name": "Flow Test User"
            }
        )
        assert register_response.status_code == status.HTTP_201_CREATED
        user_id = register_response.json()["id"]

        # 2. Login with new user
        login_response = client.post(
            "/auth/token",
            data={
                "username": "flowtest@example.com",
                "password": "testpass123"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]

        # 3. Get current user with token
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == status.HTTP_200_OK
        user_data = me_response.json()
        assert user_data["id"] == user_id
        assert user_data["email"] == "flowtest@example.com"
        assert user_data["full_name"] == "Flow Test User"
