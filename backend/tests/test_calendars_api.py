"""
Tests for calendars API endpoints.

Tests all calendar helper endpoints including list calendars,
create/update/delete events, and list events functionality.
"""
import pytest
from fastapi import status
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from app.models.oauth_token import OAuthToken
from app.core.security import encrypt_token


@pytest.fixture
def oauth_token_in_db(db, test_user):
    """Create an OAuth token in the database for testing."""
    token = OAuthToken(
        user_id=test_user.id,
        account_type="source",
        google_email="test@example.com",
        access_token_encrypted=encrypt_token("test_access_token"),
        refresh_token_encrypted=encrypt_token("test_refresh_token"),
        token_expiry=datetime.utcnow() + timedelta(hours=1),
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


@pytest.fixture
def dest_oauth_token_in_db(db, test_user):
    """Create a destination OAuth token in the database for testing."""
    token = OAuthToken(
        user_id=test_user.id,
        account_type="destination",
        google_email="dest@example.com",
        access_token_encrypted=encrypt_token("test_access_token"),
        refresh_token_encrypted=encrypt_token("test_refresh_token"),
        token_expiry=datetime.utcnow() + timedelta(hours=1),
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


@pytest.mark.integration
@pytest.mark.calendars
class TestListCalendars:
    """Test list calendars endpoint."""

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_list_calendars_source_success(self, mock_get_creds, mock_build, client, auth_headers):
        """Test listing source calendars successfully."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock Google Calendar API response
        mock_service = Mock()
        mock_calendar_list = Mock()
        mock_calendar_list.list.return_value.execute.return_value = {
            "items": [
                {
                    "id": "cal1@example.com",
                    "summary": "Test Calendar 1",
                    "description": "Test Description",
                    "timeZone": "America/New_York",
                    "accessRole": "owner",
                    "primary": True,
                    "backgroundColor": "#9fe1e7",
                    "colorId": "1",
                },
                {
                    "id": "cal2@example.com",
                    "summary": "Test Calendar 2",
                    "description": "",
                    "timeZone": "UTC",
                    "accessRole": "writer",
                    "primary": False,
                    "backgroundColor": "#b3dc6c",
                    "colorId": "2",
                }
            ]
        }
        mock_service.calendarList.return_value = mock_calendar_list
        mock_build.return_value = mock_service

        response = client.get("/api/calendars/source/list", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "calendars" in data
        assert len(data["calendars"]) == 2
        assert data["calendars"][0]["id"] == "cal1@example.com"
        assert data["calendars"][0]["summary"] == "Test Calendar 1"
        assert data["calendars"][0]["is_primary"] is True
        assert data["calendars"][0]["color_id"] == "1"
        assert data["calendars"][1]["id"] == "cal2@example.com"

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_list_calendars_destination_success(self, mock_get_creds, mock_build, client, auth_headers):
        """Test listing destination calendars successfully."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock Google Calendar API response
        mock_service = Mock()
        mock_calendar_list = Mock()
        mock_calendar_list.list.return_value.execute.return_value = {
            "items": [
                {
                    "id": "dest@example.com",
                    "summary": "Destination Calendar",
                    "description": "Dest Description",
                    "timeZone": "UTC",
                    "accessRole": "owner",
                    "primary": False,
                    "backgroundColor": "#ffad46",
                    "colorId": "6",
                }
            ]
        }
        mock_service.calendarList.return_value = mock_calendar_list
        mock_build.return_value = mock_service

        response = client.get("/api/calendars/destination/list", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["calendars"]) == 1
        assert data["calendars"][0]["id"] == "dest@example.com"

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

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_list_calendars_empty_result(self, mock_get_creds, mock_build, client, auth_headers):
        """Test listing calendars when user has no calendars."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock empty response
        mock_service = Mock()
        mock_calendar_list = Mock()
        mock_calendar_list.list.return_value.execute.return_value = {"items": []}
        mock_service.calendarList.return_value = mock_calendar_list
        mock_build.return_value = mock_service

        response = client.get("/api/calendars/source/list", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["calendars"] == []

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_list_calendars_api_error(self, mock_get_creds, mock_build, client, auth_headers):
        """Test list calendars handles Google API errors."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock API error
        mock_service = Mock()
        mock_calendar_list = Mock()
        mock_calendar_list.list.return_value.execute.side_effect = Exception("API Error")
        mock_service.calendarList.return_value = mock_calendar_list
        mock_build.return_value = mock_service

        response = client.get("/api/calendars/source/list", headers=auth_headers)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to fetch calendars" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.calendars
class TestCreateEvent:
    """Test create event endpoint."""

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_create_event_success(self, mock_get_creds, mock_build, client, auth_headers):
        """Test creating an event successfully."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock Google Calendar API response
        mock_service = Mock()
        mock_events = Mock()
        mock_insert = Mock()
        mock_insert.execute.return_value = {
            "id": "event123",
            "summary": "Test Event",
            "start": {"dateTime": "2026-01-10T10:00:00Z"},
            "end": {"dateTime": "2026-01-10T11:00:00Z"},
        }
        mock_events.insert.return_value = mock_insert
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "summary": "Test Event",
            "description": "Test Description",
            "start": {
                "dateTime": "2026-01-10T10:00:00Z",
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": "2026-01-10T11:00:00Z",
                "timeZone": "UTC"
            }
        }

        response = client.post("/api/calendars/source/events/create",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "event123"
        assert data["summary"] == "Test Event"

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

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_create_event_api_error(self, mock_get_creds, mock_build, client, auth_headers):
        """Test create event handles Google API errors."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock API error
        mock_service = Mock()
        mock_events = Mock()
        mock_insert = Mock()
        mock_insert.execute.side_effect = Exception("API Error")
        mock_events.insert.return_value = mock_insert
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "summary": "Test Event",
            "start": {"dateTime": "2026-01-10T10:00:00Z", "timeZone": "UTC"},
            "end": {"dateTime": "2026-01-10T11:00:00Z", "timeZone": "UTC"}
        }

        response = client.post("/api/calendars/source/events/create",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to create event" in response.json()["detail"]

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


@pytest.mark.integration
@pytest.mark.calendars
class TestUpdateEvent:
    """Test update event endpoint."""

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_update_event_success(self, mock_get_creds, mock_build, client, auth_headers):
        """Test updating an event successfully."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock Google Calendar API response
        mock_service = Mock()
        mock_events = Mock()
        mock_patch = Mock()
        mock_patch.execute.return_value = {
            "id": "event123",
            "summary": "Updated Event",
            "description": "Updated Description",
        }
        mock_events.patch.return_value = mock_patch
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "event_id": "event123",
            "summary": "Updated Event",
            "description": "Updated Description"
        }

        response = client.post("/api/calendars/source/events/update",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["summary"] == "Updated Event"
        assert data["description"] == "Updated Description"

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_update_event_partial_update(self, mock_get_creds, mock_build, client, auth_headers):
        """Test updating only specific fields of an event."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock Google Calendar API response
        mock_service = Mock()
        mock_events = Mock()
        mock_patch = Mock()
        mock_patch.execute.return_value = {
            "id": "event123",
            "summary": "New Summary",
        }
        mock_events.patch.return_value = mock_patch
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "event_id": "event123",
            "summary": "New Summary"
            # Not updating description, start, or end
        }

        response = client.post("/api/calendars/source/events/update",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_200_OK
        # Verify patch was called with only summary
        mock_events.patch.assert_called_once()
        call_kwargs = mock_events.patch.call_args.kwargs
        assert "summary" in call_kwargs["body"]
        assert "description" not in call_kwargs["body"]

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

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_update_event_api_error(self, mock_get_creds, mock_build, client, auth_headers):
        """Test update event handles Google API errors."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock API error
        mock_service = Mock()
        mock_events = Mock()
        mock_patch = Mock()
        mock_patch.execute.side_effect = Exception("API Error")
        mock_events.patch.return_value = mock_patch
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "event_id": "event123",
            "summary": "Updated"
        }

        response = client.post("/api/calendars/source/events/update",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to update event" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.calendars
class TestDeleteEvent:
    """Test delete event endpoint."""

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_delete_event_success(self, mock_get_creds, mock_build, client, auth_headers):
        """Test deleting an event successfully."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock Google Calendar API response
        mock_service = Mock()
        mock_events = Mock()
        mock_delete = Mock()
        mock_delete.execute.return_value = {}
        mock_events.delete.return_value = mock_delete
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "event_id": "event123"
        }

        response = client.post("/api/calendars/source/events/delete",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "deleted"

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

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_delete_event_api_error(self, mock_get_creds, mock_build, client, auth_headers):
        """Test delete event handles Google API errors."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock API error
        mock_service = Mock()
        mock_events = Mock()
        mock_delete = Mock()
        mock_delete.execute.side_effect = Exception("API Error")
        mock_events.delete.return_value = mock_delete
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "event_id": "event123"
        }

        response = client.post("/api/calendars/source/events/delete",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to delete event" in response.json()["detail"]

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

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_list_events_success(self, mock_get_creds, mock_build, client, auth_headers):
        """Test listing events successfully."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock Google Calendar API response
        mock_service = Mock()
        mock_events = Mock()
        mock_list = Mock()
        mock_list.execute.return_value = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Event 1",
                    "start": {"dateTime": "2026-01-10T10:00:00Z"},
                    "end": {"dateTime": "2026-01-10T11:00:00Z"},
                },
                {
                    "id": "event2",
                    "summary": "Event 2",
                    "start": {"dateTime": "2026-01-11T10:00:00Z"},
                    "end": {"dateTime": "2026-01-11T11:00:00Z"},
                }
            ]
        }
        mock_events.list.return_value = mock_list
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "time_min": "2026-01-10T00:00:00Z",
            "time_max": "2026-01-31T23:59:59Z"
        }

        response = client.post("/api/calendars/source/events/list",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] == "event1"

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_list_events_with_query(self, mock_get_creds, mock_build, client, auth_headers):
        """Test listing events with search query."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock Google Calendar API response
        mock_service = Mock()
        mock_events = Mock()
        mock_list = Mock()
        mock_list.execute.return_value = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Meeting with John",
                }
            ]
        }
        mock_events.list.return_value = mock_list
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "time_min": "2026-01-10T00:00:00Z",
            "time_max": "2026-01-31T23:59:59Z",
            "query": "Meeting"
        }

        response = client.post("/api/calendars/source/events/list",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_200_OK
        # Verify query parameter was passed
        mock_events.list.assert_called_once()
        call_kwargs = mock_events.list.call_args.kwargs
        assert call_kwargs["q"] == "Meeting"

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_list_events_empty_result(self, mock_get_creds, mock_build, client, auth_headers):
        """Test listing events when no events exist."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock empty response
        mock_service = Mock()
        mock_events = Mock()
        mock_list = Mock()
        mock_list.execute.return_value = {"items": []}
        mock_events.list.return_value = mock_list
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "time_min": "2026-01-10T00:00:00Z",
            "time_max": "2026-01-31T23:59:59Z"
        }

        response = client.post("/api/calendars/source/events/list",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []

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

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_list_events_api_error(self, mock_get_creds, mock_build, client, auth_headers):
        """Test list events handles Google API errors."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock API error
        mock_service = Mock()
        mock_events = Mock()
        mock_list = Mock()
        mock_list.execute.side_effect = Exception("API Error")
        mock_events.list.return_value = mock_list
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "time_min": "2026-01-10T00:00:00Z",
            "time_max": "2026-01-31T23:59:59Z"
        }

        response = client.post("/api/calendars/source/events/list",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to list events" in response.json()["detail"]

    @patch('app.api.calendars.get_credentials_from_db')
    @patch('googleapiclient.discovery.build')
    def test_list_events_verifies_ordering(self, mock_get_creds, mock_build, client, auth_headers):
        """Test list events uses correct ordering and single events parameters."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Mock Google Calendar API response
        mock_service = Mock()
        mock_events = Mock()
        mock_list = Mock()
        mock_list.execute.return_value = {"items": []}
        mock_events.list.return_value = mock_list
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        request_data = {
            "calendar_id": "test@example.com",
            "time_min": "2026-01-10T00:00:00Z",
            "time_max": "2026-01-31T23:59:59Z"
        }

        response = client.post("/api/calendars/source/events/list",
                              headers=auth_headers,
                              json=request_data)

        assert response.status_code == status.HTTP_200_OK
        # Verify correct parameters were passed
        mock_events.list.assert_called_once()
        call_kwargs = mock_events.list.call_args.kwargs
        assert call_kwargs["singleEvents"] is True
        assert call_kwargs["orderBy"] == "startTime"
