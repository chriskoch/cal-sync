"""
Unit tests for sync engine core business logic.
"""
import pytest
import datetime
import uuid
from unittest.mock import Mock, MagicMock, patch
from app.core.sync_engine import (
    iso_utc,
    build_payload_from_source,
    events_differ,
    compute_content_hash,
    fetch_events,
    SyncEngine,
)
from app.models.event_mapping import EventMapping


@pytest.mark.unit
class TestHelperFunctions:
    """Test pure helper functions."""

    def test_iso_utc_converts_datetime_correctly(self):
        """Test ISO UTC datetime formatting."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45, 123456, tzinfo=datetime.timezone.utc)
        result = iso_utc(dt)

        assert result == "2024-01-15T10:30:45Z"
        assert result.endswith("Z")
        # Verify microseconds are removed
        assert "123456" not in result

    def test_iso_utc_handles_no_timezone(self):
        """Test ISO UTC with naive datetime."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45)
        result = iso_utc(dt)

        assert result == "2024-01-15T10:30:45Z"

    def test_build_payload_basic_event(self):
        """Test building payload from source event."""
        source_event = {
            "id": "event123",
            "summary": "Team Meeting",
            "description": "Weekly sync",
            "location": "Conference Room A",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        payload = build_payload_from_source(source_event)

        assert payload["summary"] == "Team Meeting"
        assert payload["description"] == "Weekly sync"
        assert payload["location"] == "Conference Room A"
        assert payload["start"] == source_event["start"]
        assert payload["end"] == source_event["end"]
        assert payload["extendedProperties"]["shared"]["source_id"] == "event123"
        assert payload["reminders"] == {"useDefault": False}

    def test_build_payload_with_sync_metadata(self):
        """Test building payload with bidirectional sync metadata."""
        source_event = {
            "id": "event123",
            "summary": "Test Event",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        sync_cluster_id = str(uuid.uuid4())
        dest_event_id = "dest_event_456"

        payload = build_payload_from_source(source_event, sync_cluster_id, dest_event_id)

        shared = payload["extendedProperties"]["shared"]
        assert shared["source_id"] == "event123"
        assert shared["sync_cluster_id"] == sync_cluster_id
        assert shared["dest_event_id"] == dest_event_id
        assert shared["sync_direction"] == "source_to_dest"
        assert "last_sync_timestamp" in shared

    def test_build_payload_removes_none_values(self):
        """Test that None values are removed from payload."""
        source_event = {
            "id": "event123",
            "summary": "Test Event",
            "description": None,  # Should be removed
            "location": None,  # Should be removed
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        payload = build_payload_from_source(source_event)

        assert "description" not in payload
        assert "location" not in payload
        assert "summary" in payload

    def test_build_payload_includes_optional_fields(self):
        """Test payload includes all optional event fields."""
        source_event = {
            "id": "event123",
            "summary": "Test Event",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "recurrence": ["RRULE:FREQ=WEEKLY"],
            "transparency": "transparent",
            "visibility": "private",
            "colorId": "5",
        }

        payload = build_payload_from_source(source_event)

        assert payload["recurrence"] == ["RRULE:FREQ=WEEKLY"]
        assert payload["transparency"] == "transparent"
        assert payload["visibility"] == "private"
        assert payload["colorId"] == "5"

    def test_events_differ_when_summary_changes(self):
        """Test change detection for summary field."""
        src_body = {
            "summary": "Updated Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }
        dest_event = {
            "summary": "Old Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        assert events_differ(src_body, dest_event) is True

    def test_events_differ_when_start_time_changes(self):
        """Test change detection for start time."""
        src_body = {
            "summary": "Meeting",
            "start": {"dateTime": "2024-01-15T11:00:00Z"},
            "end": {"dateTime": "2024-01-15T12:00:00Z"},
        }
        dest_event = {
            "summary": "Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T12:00:00Z"},
        }

        assert events_differ(src_body, dest_event) is True

    def test_events_differ_returns_false_when_identical(self):
        """Test no change when events are identical."""
        event = {
            "summary": "Meeting",
            "description": "Team sync",
            "location": "Room A",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        assert events_differ(event, event) is False

    def test_events_differ_ignores_metadata_fields(self):
        """Test that metadata fields are ignored in comparison."""
        src_body = {
            "summary": "Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }
        dest_event = {
            "summary": "Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "id": "different_id",  # Should be ignored
            "updated": "2024-01-15T12:00:00Z",  # Should be ignored
            "etag": "different_etag",  # Should be ignored
        }

        assert events_differ(src_body, dest_event) is False

    def test_compute_content_hash_same_for_identical_events(self):
        """Test content hash is consistent for identical events."""
        event1 = {
            "summary": "Meeting",
            "description": "Team sync",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }
        event2 = {
            "summary": "Meeting",
            "description": "Team sync",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        hash1 = compute_content_hash(event1)
        hash2 = compute_content_hash(event2)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters

    def test_compute_content_hash_different_for_changed_events(self):
        """Test content hash changes when event content changes."""
        event1 = {
            "summary": "Meeting",
            "description": "Team sync",
        }
        event2 = {
            "summary": "Meeting",
            "description": "Different description",
        }

        hash1 = compute_content_hash(event1)
        hash2 = compute_content_hash(event2)

        assert hash1 != hash2


@pytest.mark.unit
class TestFetchEvents:
    """Test event fetching with pagination."""

    def test_fetch_events_single_page(self):
        """Test fetching events without pagination."""
        mock_service = Mock()
        mock_events_list = Mock()
        mock_service.events.return_value.list.return_value = mock_events_list

        events_data = [
            {"id": "event1", "summary": "Event 1"},
            {"id": "event2", "summary": "Event 2"},
        ]
        mock_events_list.execute.return_value = {
            "items": events_data,
            "nextPageToken": None,
        }

        result = fetch_events(
            mock_service,
            "calendar@example.com",
            "2024-01-01T00:00:00Z",
            "2024-12-31T23:59:59Z"
        )

        assert len(result) == 2
        assert result[0]["id"] == "event1"
        assert result[1]["id"] == "event2"

    def test_fetch_events_multiple_pages(self):
        """Test fetching events with pagination."""
        mock_service = Mock()
        mock_events_list = Mock()
        mock_service.events.return_value.list.return_value = mock_events_list

        # Simulate pagination
        page1 = {
            "items": [{"id": "event1"}, {"id": "event2"}],
            "nextPageToken": "token1",
        }
        page2 = {
            "items": [{"id": "event3"}, {"id": "event4"}],
            "nextPageToken": "token2",
        }
        page3 = {
            "items": [{"id": "event5"}],
            "nextPageToken": None,
        }

        mock_events_list.execute.side_effect = [page1, page2, page3]

        result = fetch_events(
            mock_service,
            "calendar@example.com",
            "2024-01-01T00:00:00Z",
            "2024-12-31T23:59:59Z"
        )

        assert len(result) == 5
        assert mock_events_list.execute.call_count == 3

    def test_fetch_events_with_empty_response(self):
        """Test fetching when no events exist."""
        mock_service = Mock()
        mock_events_list = Mock()
        mock_service.events.return_value.list.return_value = mock_events_list

        mock_events_list.execute.return_value = {
            "items": [],
            "nextPageToken": None,
        }

        result = fetch_events(
            mock_service,
            "calendar@example.com",
            "2024-01-01T00:00:00Z",
            "2024-12-31T23:59:59Z"
        )

        assert result == []


@pytest.mark.unit
class TestSyncEngine:
    """Test SyncEngine class methods."""

    def test_sync_engine_initialization(self, db):
        """Test SyncEngine can be initialized with database session."""
        engine = SyncEngine(db)
        assert engine.db == db

    @patch('app.core.sync_engine.build')
    def test_sync_creates_new_event(self, mock_build, db, test_user):
        """Test sync creates new event in destination calendar."""
        # Setup mocks
        mock_src_service = Mock()
        mock_dst_service = Mock()
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        # Mock source event
        source_event = {
            "id": "src_event_1",
            "summary": "New Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T09:00:00Z",
        }

        # Mock fetch_events to return source event
        mock_src_service.events.return_value.list.return_value.execute.return_value = {
            "items": [source_event],
            "nextPageToken": None,
        }

        # Mock dest has no events
        mock_dst_service.events.return_value.list.return_value.execute.return_value = {
            "items": [],
            "nextPageToken": None,
        }

        # Mock insert response
        mock_dst_service.events.return_value.insert.return_value.execute.return_value = {
            "id": "dest_event_1",
            "updated": "2024-01-15T10:00:00Z",
        }

        # Create mock credentials
        mock_src_creds = Mock()
        mock_dst_creds = Mock()

        # Run sync
        engine = SyncEngine(db)
        sync_config_id = str(uuid.uuid4())
        result = engine.sync_calendars(
            sync_config_id=sync_config_id,
            source_creds=mock_src_creds,
            dest_creds=mock_dst_creds,
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            lookahead_days=90,
        )

        # Verify results
        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["deleted"] == 0

        # Verify event mapping was created
        mapping = db.query(EventMapping).filter(
            EventMapping.source_event_id == "src_event_1"
        ).first()
        assert mapping is not None
        assert mapping.dest_event_id == "dest_event_1"

    @patch('app.core.sync_engine.build')
    def test_sync_updates_existing_event(self, mock_build, db):
        """Test sync updates existing event when content changes."""
        # Setup mocks
        mock_src_service = Mock()
        mock_dst_service = Mock()
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        # Mock source event with updated summary
        source_event = {
            "id": "src_event_1",
            "summary": "Updated Meeting Title",  # Changed
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T10:30:00Z",
        }

        # Mock destination event with old summary
        dest_event = {
            "id": "dest_event_1",
            "summary": "Old Meeting Title",  # Different
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "extendedProperties": {
                "shared": {"source_id": "src_event_1"}
            },
        }

        # Mock fetch_events
        mock_src_service.events.return_value.list.return_value.execute.return_value = {
            "items": [source_event],
            "nextPageToken": None,
        }
        mock_dst_service.events.return_value.list.return_value.execute.return_value = {
            "items": [dest_event],
            "nextPageToken": None,
        }

        # Mock update response
        mock_dst_service.events.return_value.update.return_value.execute.return_value = {
            "id": "dest_event_1",
            "updated": "2024-01-15T10:31:00Z",
        }

        # Run sync
        engine = SyncEngine(db)
        sync_config_id = str(uuid.uuid4())
        result = engine.sync_calendars(
            sync_config_id=sync_config_id,
            source_creds=Mock(),
            dest_creds=Mock(),
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
        )

        # Verify results
        assert result["created"] == 0
        assert result["updated"] == 1
        assert result["deleted"] == 0

    @patch('app.core.sync_engine.build')
    def test_sync_deletes_cancelled_event(self, mock_build, db):
        """Test sync deletes destination event when source is cancelled."""
        # Setup mocks
        mock_src_service = Mock()
        mock_dst_service = Mock()
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        # Mock cancelled source event
        source_event = {
            "id": "src_event_1",
            "status": "cancelled",
            "summary": "Cancelled Meeting",
        }

        # Mock existing destination event
        dest_event = {
            "id": "dest_event_1",
            "summary": "Cancelled Meeting",
            "extendedProperties": {
                "shared": {"source_id": "src_event_1"}
            },
        }

        # Mock fetch_events
        mock_src_service.events.return_value.list.return_value.execute.return_value = {
            "items": [source_event],
            "nextPageToken": None,
        }
        mock_dst_service.events.return_value.list.return_value.execute.return_value = {
            "items": [dest_event],
            "nextPageToken": None,
        }

        # Mock delete
        mock_dst_service.events.return_value.delete.return_value.execute.return_value = {}

        # Create existing event mapping
        sync_config_id = str(uuid.uuid4())
        existing_mapping = EventMapping(
            sync_config_id=sync_config_id,
            source_event_id="src_event_1",
            dest_event_id="dest_event_1",
            sync_cluster_id=uuid.uuid4(),
            content_hash="old_hash",
        )
        db.add(existing_mapping)
        db.commit()

        # Run sync
        engine = SyncEngine(db)
        result = engine.sync_calendars(
            sync_config_id=sync_config_id,
            source_creds=Mock(),
            dest_creds=Mock(),
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
        )

        # Verify results
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["deleted"] == 1

        # Verify event mapping was deleted
        mapping = db.query(EventMapping).filter(
            EventMapping.source_event_id == "src_event_1"
        ).first()
        assert mapping is None

    @patch('app.core.sync_engine.build')
    def test_sync_handles_410_on_delete(self, mock_build, db):
        """Test sync handles 410 error when deleting already-deleted event."""
        from googleapiclient.errors import HttpError
        from httplib2 import Response

        # Setup mock services
        mock_src_service = Mock()
        mock_dst_service = Mock()
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        # Mock cancelled source event
        source_event = {
            "id": "src_event_1",
            "status": "cancelled",
            "summary": "Cancelled Meeting",
        }

        # Mock existing destination event
        dest_event = {
            "id": "dest_event_1",
            "summary": "Cancelled Meeting",
            "extendedProperties": {
                "shared": {"source_id": "src_event_1"}
            },
        }

        # Mock fetch_events
        mock_src_service.events.return_value.list.return_value.execute.return_value = {
            "items": [source_event],
            "nextPageToken": None,
        }
        mock_dst_service.events.return_value.list.return_value.execute.return_value = {
            "items": [dest_event],
            "nextPageToken": None,
        }

        # Mock delete to raise 410 error (event already deleted on Google's side)
        http_error = HttpError(
            resp=Response({'status': '410'}),
            content=b'{"error": {"message": "Resource has been deleted"}}'
        )
        mock_dst_service.events.return_value.delete.return_value.execute.side_effect = http_error

        # Run sync
        sync_config_id = str(uuid.uuid4())
        engine = SyncEngine(db)
        result = engine.sync_calendars(
            sync_config_id=sync_config_id,
            source_creds=Mock(),
            dest_creds=Mock(),
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
        )

        # Should still count as deleted and not crash
        assert result["deleted"] == 1
        assert result["created"] == 0
        assert result["updated"] == 0

    @patch('app.core.sync_engine.build')
    def test_sync_handles_410_on_update(self, mock_build, db):
        """Test sync handles 410 error when updating already-deleted event."""
        from googleapiclient.errors import HttpError
        from httplib2 import Response

        # Setup mock services
        mock_src_service = Mock()
        mock_dst_service = Mock()
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        # Mock source event
        source_event = {
            "id": "src_event_1",
            "status": "confirmed",
            "summary": "Updated Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T10:00:00Z",
        }

        # Mock existing destination event
        dest_event = {
            "id": "dest_event_1",
            "summary": "Old Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T09:00:00Z",
            "extendedProperties": {
                "shared": {"source_id": "src_event_1"}
            },
        }

        # Mock fetch_events
        mock_src_service.events.return_value.list.return_value.execute.return_value = {
            "items": [source_event],
            "nextPageToken": None,
        }
        mock_dst_service.events.return_value.list.return_value.execute.return_value = {
            "items": [dest_event],
            "nextPageToken": None,
        }

        # Mock update to raise 410 error
        http_error = HttpError(
            resp=Response({'status': '410'}),
            content=b'{"error": {"message": "Resource has been deleted"}}'
        )
        mock_dst_service.events.return_value.update.return_value.execute.side_effect = http_error

        # Mock insert to succeed (recreating the event)
        mock_dst_service.events.return_value.insert.return_value.execute.return_value = {
            "id": "new_dest_event_1",
            "updated": "2024-01-15T10:30:00Z",
        }

        # Run sync
        sync_config_id = str(uuid.uuid4())
        engine = SyncEngine(db)
        result = engine.sync_calendars(
            sync_config_id=sync_config_id,
            source_creds=Mock(),
            dest_creds=Mock(),
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
        )

        # Should recreate as new event
        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["deleted"] == 0

        # Verify new event mapping was created
        mapping = db.query(EventMapping).filter(
            EventMapping.source_event_id == "src_event_1"
        ).first()
        assert mapping is not None
        assert mapping.dest_event_id == "new_dest_event_1"

    @patch('app.core.sync_engine.build')
    def test_sync_handles_404_on_delete(self, mock_build, db):
        """Test sync handles 404 error when deleting non-existent event."""
        from googleapiclient.errors import HttpError
        from httplib2 import Response

        # Setup mock services
        mock_src_service = Mock()
        mock_dst_service = Mock()
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        # Mock cancelled source event
        source_event = {
            "id": "src_event_1",
            "status": "cancelled",
        }

        # Mock existing destination event in our index
        dest_event = {
            "id": "dest_event_1",
            "extendedProperties": {
                "shared": {"source_id": "src_event_1"}
            },
        }

        # Mock fetch_events
        mock_src_service.events.return_value.list.return_value.execute.return_value = {
            "items": [source_event],
            "nextPageToken": None,
        }
        mock_dst_service.events.return_value.list.return_value.execute.return_value = {
            "items": [dest_event],
            "nextPageToken": None,
        }

        # Mock delete to raise 404 error
        http_error = HttpError(
            resp=Response({'status': '404'}),
            content=b'{"error": {"message": "Not found"}}'
        )
        mock_dst_service.events.return_value.delete.return_value.execute.side_effect = http_error

        # Run sync
        sync_config_id = str(uuid.uuid4())
        engine = SyncEngine(db)
        result = engine.sync_calendars(
            sync_config_id=sync_config_id,
            source_creds=Mock(),
            dest_creds=Mock(),
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
        )

        # Should still count as deleted
        assert result["deleted"] == 1
        assert result["created"] == 0
        assert result["updated"] == 0
