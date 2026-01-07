"""
Tests for calendars API endpoints.

Focused on testing error handling, validation, and authentication requirements.
Google API success paths require complex mocking and are better tested via E2E scripts.
"""
import pytest
from fastapi import status


@pytest.mark.integration
@pytest.mark.calendars
class TestListCalendars:
    """Test list calendars endpoint."""

    def test_list_calendars_requires_authentication(self, client):
        """Test list calendars requires authentication."""
        response = client.get("/api/calendars/source/list")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_calendars_no_oauth_token(self, client, auth_headers):
        """Test list calendars fails when no OAuth token exists."""
        response = client.get("/api/calendars/source/list", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No OAuth connection found" in response.json()["detail"]

    def test_list_calendars_invalid_account_type(self, client, auth_headers):
        """Test list calendars with invalid account type."""
        response = client.get("/api/calendars/invalid/list", headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
@pytest.mark.calendars
class TestCreateEvent:
    """Test create event endpoint."""

    def test_create_event_requires_authentication(self, client):
        """Test create event requires authentication."""
        request_data = {
            "calendar_id": "test@example.com",
            "summary": "Test Event",
            "start": {"dateTime": "2026-01-10T10:00:00Z", "timeZone": "UTC"},
            "end": {"dateTime": "2026-01-10T11:00:00Z", "timeZone": "UTC"}
        }

        response = client.post("/api/calendars/source/events/create", json=request_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_event_no_oauth_token(self, client, auth_headers):
        """Test create event fails when no OAuth token exists."""
        request_data = {
            "calendar_id": "test@example.com",
            "summary": "Test Event",
            "start": {"dateTime": "2026-01-10T10:00:00Z", "timeZone": "UTC"},
            "end": {"dateTime": "2026-01-10T11:00:00Z", "timeZone": "UTC"}
        }

        response = client.post("/api/calendars/source/events/create",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No OAuth connection found" in response.json()["detail"]

    def test_create_event_invalid_request_body(self, client, auth_headers):
        """Test create event with invalid request body."""
        # Missing required fields
        request_data = {
            "calendar_id": "test@example.com",
            # Missing summary, start, end
        }

        response = client.post("/api/calendars/source/events/create",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_event_invalid_account_type(self, client, auth_headers):
        """Test create event with invalid account type."""
        request_data = {
            "calendar_id": "test@example.com",
            "summary": "Test Event",
            "start": {"dateTime": "2026-01-10T10:00:00Z", "timeZone": "UTC"},
            "end": {"dateTime": "2026-01-10T11:00:00Z", "timeZone": "UTC"}
        }

        response = client.post("/api/calendars/invalid/events/create",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
@pytest.mark.calendars
class TestUpdateEvent:
    """Test update event endpoint."""

    def test_update_event_requires_authentication(self, client):
        """Test update event requires authentication."""
        request_data = {
            "calendar_id": "test@example.com",
            "event_id": "event123",
            "summary": "Updated"
        }

        response = client.post("/api/calendars/source/events/update", json=request_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_event_no_oauth_token(self, client, auth_headers):
        """Test update event fails when no OAuth token exists."""
        request_data = {
            "calendar_id": "test@example.com",
            "event_id": "event123",
            "summary": "Updated"
        }

        response = client.post("/api/calendars/source/events/update",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No OAuth connection found" in response.json()["detail"]

    def test_update_event_invalid_request_body(self, client, auth_headers):
        """Test update event with missing required fields."""
        # Missing event_id
        request_data = {
            "calendar_id": "test@example.com",
            "summary": "Updated"
        }

        response = client.post("/api/calendars/source/events/update",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
@pytest.mark.calendars
class TestDeleteEvent:
    """Test delete event endpoint."""

    def test_delete_event_requires_authentication(self, client):
        """Test delete event requires authentication."""
        request_data = {
            "calendar_id": "test@example.com",
            "event_id": "event123"
        }

        response = client.post("/api/calendars/source/events/delete", json=request_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_event_no_oauth_token(self, client, auth_headers):
        """Test delete event fails when no OAuth token exists."""
        request_data = {
            "calendar_id": "test@example.com",
            "event_id": "event123"
        }

        response = client.post("/api/calendars/source/events/delete",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No OAuth connection found" in response.json()["detail"]

    def test_delete_event_invalid_request_body(self, client, auth_headers):
        """Test delete event with invalid request body."""
        # Missing required fields
        request_data = {
            "calendar_id": "test@example.com"
            # Missing event_id
        }

        response = client.post("/api/calendars/source/events/delete",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
@pytest.mark.calendars
class TestListEvents:
    """Test list events endpoint."""

    def test_list_events_requires_authentication(self, client):
        """Test list events requires authentication."""
        request_data = {
            "calendar_id": "test@example.com",
            "time_min": "2026-01-10T00:00:00Z",
            "time_max": "2026-01-31T23:59:59Z"
        }

        response = client.post("/api/calendars/source/events/list", json=request_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_events_no_oauth_token(self, client, auth_headers):
        """Test list events fails when no OAuth token exists."""
        request_data = {
            "calendar_id": "test@example.com",
            "time_min": "2026-01-10T00:00:00Z",
            "time_max": "2026-01-31T23:59:59Z"
        }

        response = client.post("/api/calendars/source/events/list",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No OAuth connection found" in response.json()["detail"]

    def test_list_events_invalid_request_body(self, client, auth_headers):
        """Test list events with missing required fields."""
        # Missing required fields
        request_data = {
            "calendar_id": "test@example.com"
            # Missing time_min, time_max
        }

        response = client.post("/api/calendars/source/events/list",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
