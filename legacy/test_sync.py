import os
from unittest.mock import Mock, patch, mock_open
import pytest
from sync import (
    build_payload_from_source,
    events_differ,
    load_credentials_from_dir,
    fetch_events,
)


class TestBuildPayloadFromSource:
    """Test event payload transformation."""

    def test_includes_all_supported_fields(self):
        """Verify all supported fields are copied from source event."""
        source_event = {
            "id": "event123",
            "summary": "Team Meeting",
            "description": "Weekly sync",
            "location": "Conference Room A",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "recurrence": ["RRULE:FREQ=WEEKLY"],
            "transparency": "opaque",
            "visibility": "default",
            "colorId": "1",
        }

        payload = build_payload_from_source(source_event)

        assert payload["summary"] == "Team Meeting"
        assert payload["description"] == "Weekly sync"
        assert payload["location"] == "Conference Room A"
        assert payload["start"] == {"dateTime": "2024-01-15T10:00:00Z"}
        assert payload["end"] == {"dateTime": "2024-01-15T11:00:00Z"}
        assert payload["recurrence"] == ["RRULE:FREQ=WEEKLY"]
        assert payload["transparency"] == "opaque"
        assert payload["visibility"] == "default"
        assert payload["colorId"] == "1"
        assert payload["extendedProperties"]["shared"]["source_id"] == "event123"
        assert payload["reminders"] == {"useDefault": False}

    def test_handles_minimal_event(self):
        """Verify minimal events work without optional fields."""
        source_event = {
            "id": "minimal123",
            "summary": "Simple Event",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        payload = build_payload_from_source(source_event)

        assert payload["summary"] == "Simple Event"
        assert "description" not in payload
        assert "location" not in payload
        assert "recurrence" not in payload
        assert payload["extendedProperties"]["shared"]["source_id"] == "minimal123"


class TestEventsDiffer:
    """Test change detection logic."""

    def test_identical_events_return_false(self):
        """Verify identical events are not considered different."""
        payload = {
            "summary": "Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }
        dest_event = {
            "summary": "Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        assert not events_differ(payload, dest_event)

    def test_summary_change_detected(self):
        """Verify summary changes are detected."""
        payload = {"summary": "New Title"}
        dest_event = {"summary": "Old Title"}

        assert events_differ(payload, dest_event)

    def test_time_change_detected(self):
        """Verify time changes are detected."""
        payload = {"start": {"dateTime": "2024-01-15T10:00:00Z"}}
        dest_event = {"start": {"dateTime": "2024-01-15T09:00:00Z"}}

        assert events_differ(payload, dest_event)

    def test_ignores_fields_not_in_comparable_list(self):
        """Verify non-comparable fields don't trigger changes."""
        payload = {"summary": "Meeting"}
        dest_event = {
            "summary": "Meeting",
            "id": "dest123",
            "etag": "different-etag",
            "updated": "2024-01-15T12:00:00Z",
        }

        assert not events_differ(payload, dest_event)


class TestLoadCredentialsFromDir:
    """Test credential loading and error handling."""

    def test_missing_token_raises_system_exit(self):
        """Verify missing token.json raises helpful error."""
        with patch("os.path.exists", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                load_credentials_from_dir("creds/source")

            assert "Token not found" in str(exc_info.value)
            assert "auth.py" in str(exc_info.value)

    @patch("sync.Credentials")
    @patch("builtins.open", new_callable=mock_open, read_data='{"token": "test"}')
    @patch("os.path.exists", return_value=True)
    def test_loads_valid_token(self, mock_exists, mock_file, mock_creds_class):
        """Verify valid token is loaded correctly."""
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        result = load_credentials_from_dir("creds/source")

        assert result == mock_creds
        mock_creds_class.from_authorized_user_file.assert_called_once()

    @patch("sync.Credentials")
    @patch("sync.Request")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_refreshes_expired_token(self, mock_exists, mock_file, mock_request, mock_creds_class):
        """Verify expired tokens with refresh_token are refreshed."""
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh123"
        mock_creds.to_json.return_value = '{"token": "refreshed"}'
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        result = load_credentials_from_dir("creds/source")

        mock_creds.refresh.assert_called_once()
        assert result == mock_creds


class TestFetchEventsPagination:
    """Test event fetching with pagination."""

    def test_fetches_single_page(self):
        """Verify single page of events is fetched correctly."""
        mock_service = Mock()
        mock_events_api = mock_service.events.return_value.list.return_value
        mock_events_api.execute.return_value = {
            "items": [{"id": "event1"}, {"id": "event2"}],
        }

        events = fetch_events(mock_service, "calendar@example.com", "2024-01-01T00:00:00Z", "2024-02-01T00:00:00Z")

        assert len(events) == 2
        assert events[0]["id"] == "event1"
        assert events[1]["id"] == "event2"

    def test_fetches_multiple_pages(self):
        """Verify pagination handles multiple pages correctly."""
        mock_service = Mock()
        mock_list = mock_service.events.return_value.list

        # First page with nextPageToken
        mock_list.return_value.execute.side_effect = [
            {"items": [{"id": "event1"}], "nextPageToken": "page2"},
            {"items": [{"id": "event2"}], "nextPageToken": "page3"},
            {"items": [{"id": "event3"}]},  # Last page, no token
        ]

        events = fetch_events(mock_service, "calendar@example.com", "2024-01-01T00:00:00Z", "2024-02-01T00:00:00Z")

        assert len(events) == 3
        assert events[0]["id"] == "event1"
        assert events[1]["id"] == "event2"
        assert events[2]["id"] == "event3"
        assert mock_list.call_count == 3


class TestSyncScenarios:
    """Test main sync scenarios with mocked services."""

    @patch("sync.load_credentials_from_dir")
    @patch("sync.build")
    @patch("sync.fetch_events")
    @patch.dict(os.environ, {"SOURCE_CALENDAR_ID": "src@example.com", "DEST_CALENDAR_ID": "dst@example.com"})
    def test_creates_new_event(self, mock_fetch, mock_build_service, mock_load_creds):
        """Verify new events are created in destination calendar."""
        from sync import main

        # Setup mocks
        mock_service_src = Mock()
        mock_service_dst = Mock()
        mock_build_service.side_effect = [mock_service_src, mock_service_dst]

        # Source has an event, destination is empty
        mock_fetch.side_effect = [
            [{"id": "src1", "summary": "New Event", "start": {}, "end": {}}],
            [],  # Empty destination
        ]

        mock_service_dst.events.return_value.insert.return_value.execute.return_value = {}

        main()

        # Verify insert was called
        mock_service_dst.events.return_value.insert.assert_called_once()

    @patch("sync.load_credentials_from_dir")
    @patch("sync.build")
    @patch("sync.fetch_events")
    @patch.dict(os.environ, {"SOURCE_CALENDAR_ID": "src@example.com", "DEST_CALENDAR_ID": "dst@example.com"})
    def test_deletes_cancelled_event(self, mock_fetch, mock_build_service, mock_load_creds):
        """Verify cancelled source events trigger deletion in destination."""
        from sync import main

        mock_service_src = Mock()
        mock_service_dst = Mock()
        mock_build_service.side_effect = [mock_service_src, mock_service_dst]

        # Source event is cancelled
        mock_fetch.side_effect = [
            [{"id": "src1", "status": "cancelled"}],
            # Destination has the synced event
            [{"id": "dst1", "extendedProperties": {"shared": {"source_id": "src1"}}}],
        ]

        mock_service_dst.events.return_value.delete.return_value.execute.return_value = {}

        main()

        # Verify delete was called
        mock_service_dst.events.return_value.delete.assert_called_once()

    @patch("sync.load_credentials_from_dir")
    @patch("sync.build")
    @patch("sync.fetch_events")
    @patch.dict(os.environ, {"SOURCE_CALENDAR_ID": "src@example.com", "DEST_CALENDAR_ID": "dst@example.com"})
    def test_updates_changed_event(self, mock_fetch, mock_build_service, mock_load_creds):
        """Verify changed events trigger update in destination."""
        from sync import main

        mock_service_src = Mock()
        mock_service_dst = Mock()
        mock_build_service.side_effect = [mock_service_src, mock_service_dst]

        # Source event with updated summary
        mock_fetch.side_effect = [
            [{"id": "src1", "summary": "Updated Title", "start": {}, "end": {}}],
            # Destination has old version
            [{"id": "dst1", "summary": "Old Title", "extendedProperties": {"shared": {"source_id": "src1"}}}],
        ]

        mock_service_dst.events.return_value.update.return_value.execute.return_value = {}

        main()

        # Verify update was called
        mock_service_dst.events.return_value.update.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
