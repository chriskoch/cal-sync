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
from app.models.sync_config import SyncConfig


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
        assert shared["synced_by_system"] == "true"  # Loop prevention flag
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

        # Create sync config first (required for foreign key)
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            sync_lookahead_days=90,
        )
        db.add(sync_config)
        db.commit()
        sync_config_id = str(sync_config.id)

        # Run sync
        engine = SyncEngine(db)
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

        # Create sync config first (required for foreign key)
        from app.models.user import User
        test_user = User(email="test@example.com", is_active=True)
        db.add(test_user)
        db.flush()
        
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            sync_lookahead_days=90,
        )
        db.add(sync_config)
        db.flush()
        sync_config_id = str(sync_config.id)

        # Create existing event mapping
        existing_mapping = EventMapping(
            sync_config_id=sync_config.id,
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

        # Create sync config first (required for foreign key)
        from app.models.user import User
        test_user = User(email="test@example.com", is_active=True)
        db.add(test_user)
        db.flush()
        
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            sync_lookahead_days=90,
        )
        db.add(sync_config)
        db.commit()
        sync_config_id = str(sync_config.id)

        # Run sync
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


@pytest.mark.unit
class TestBidirectionalSyncHelpers:
    """Test bi-directional sync helper methods."""

    def test_build_payload_with_privacy_mode(self):
        """Test privacy mode hides event details but preserves time."""
        source_event = {
            "id": "event123",
            "summary": "Confidential Meeting",
            "description": "Secret discussion about project X",
            "location": "Private Office",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "attendees": [
                {"email": "person1@example.com"},
                {"email": "person2@example.com"},
            ],
        }

        payload = build_payload_from_source(
            source_event,
            privacy_mode_enabled=True,
            privacy_placeholder_text="Personal appointment"
        )

        # Privacy mode should hide details
        assert payload["summary"] == "Personal appointment"
        assert payload["description"] == ""
        assert payload["location"] == ""
        assert "attendees" not in payload

        # But preserve time information
        assert payload["start"] == source_event["start"]
        assert payload["end"] == source_event["end"]

        # Should mark as privacy mode in extended properties
        assert payload["extendedProperties"]["shared"]["privacy_mode"] == "true"
        assert payload["extendedProperties"]["shared"]["synced_by_system"] == "true"

    def test_build_payload_without_privacy_mode(self):
        """Test normal sync preserves all event details."""
        source_event = {
            "id": "event123",
            "summary": "Team Meeting",
            "description": "Weekly sync",
            "location": "Conference Room A",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        payload = build_payload_from_source(
            source_event,
            privacy_mode_enabled=False
        )

        # All details should be preserved
        assert payload["summary"] == "Team Meeting"
        assert payload["description"] == "Weekly sync"
        assert payload["location"] == "Conference Room A"

        # Should NOT mark as privacy mode
        assert "privacy_mode" not in payload["extendedProperties"]["shared"]

    def test_build_payload_with_origin_tracking(self):
        """Test origin tracking metadata is included."""
        source_event = {
            "id": "event123",
            "summary": "Test Event",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        sync_config_id = str(uuid.uuid4())
        origin_calendar_id = "original@example.com"

        payload = build_payload_from_source(
            source_event,
            origin_calendar_id=origin_calendar_id,
            sync_config_id=sync_config_id
        )

        shared = payload["extendedProperties"]["shared"]
        assert shared["origin_calendar_id"] == origin_calendar_id
        assert shared["origin_event_id"] == "event123"
        assert shared["sync_config_id"] == sync_config_id
        assert shared["synced_by_system"] == "true"

    def test_build_payload_with_all_bidirectional_metadata(self):
        """Test all bi-directional sync metadata fields."""
        source_event = {
            "id": "event123",
            "summary": "Test Event",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        sync_cluster_id = str(uuid.uuid4())
        sync_config_id = str(uuid.uuid4())
        origin_calendar_id = "origin@example.com"
        dest_event_id = "dest_456"

        payload = build_payload_from_source(
            source_event,
            sync_cluster_id=sync_cluster_id,
            dest_event_id=dest_event_id,
            origin_calendar_id=origin_calendar_id,
            sync_config_id=sync_config_id,
            privacy_mode_enabled=True,
            privacy_placeholder_text="Busy"
        )

        shared = payload["extendedProperties"]["shared"]
        assert shared["source_id"] == "event123"
        assert shared["synced_by_system"] == "true"
        assert shared["sync_cluster_id"] == sync_cluster_id
        assert shared["origin_calendar_id"] == origin_calendar_id
        assert shared["origin_event_id"] == "event123"
        assert shared["sync_config_id"] == sync_config_id
        assert shared["dest_event_id"] == dest_event_id
        assert shared["privacy_mode"] == "true"
        assert "last_sync_timestamp" in shared

    def test_should_skip_event_with_synced_flag(self, db):
        """Test loop prevention skips events created by sync system."""
        engine = SyncEngine(db)

        # Event created by sync system
        synced_event = {
            "id": "event123",
            "summary": "Synced Event",
            "extendedProperties": {
                "shared": {
                    "synced_by_system": "true"
                }
            }
        }

        should_skip, reason = engine.should_skip_event(synced_event, "config_123")
        assert should_skip is True
        assert reason == "synced_by_system"

    def test_should_skip_event_without_synced_flag(self, db):
        """Test normal events are not skipped."""
        engine = SyncEngine(db)

        # Regular event
        normal_event = {
            "id": "event123",
            "summary": "Normal Event",
        }

        should_skip, reason = engine.should_skip_event(normal_event, "config_123")
        assert should_skip is False
        assert reason == ""

    def test_should_skip_event_with_other_metadata(self, db):
        """Test events with other metadata but no synced flag are not skipped."""
        engine = SyncEngine(db)

        event = {
            "id": "event123",
            "summary": "Event",
            "extendedProperties": {
                "shared": {
                    "source_id": "original_123",
                    "some_other_field": "value"
                }
            }
        }

        should_skip, reason = engine.should_skip_event(event, "config_123")
        assert should_skip is False
        assert reason == ""

    def test_get_origin_calendar_id_from_mapping(self, db):
        """Test origin is retrieved from existing mapping first."""
        engine = SyncEngine(db)

        event = {
            "id": "event123",
            "extendedProperties": {
                "shared": {
                    "origin_calendar_id": "wrong@example.com"  # Should be ignored
                }
            }
        }

        # Create mapping with origin
        mapping = EventMapping(
            sync_config_id=uuid.uuid4(),
            source_event_id="event123",
            dest_event_id="dest_123",
            sync_cluster_id=uuid.uuid4(),
            content_hash="hash",
            origin_calendar_id="correct@example.com"
        )

        origin = engine.get_origin_calendar_id(event, mapping, "source@example.com")
        assert origin == "correct@example.com"

    def test_get_origin_calendar_id_from_extended_properties(self, db):
        """Test origin is retrieved from extended properties if no mapping."""
        engine = SyncEngine(db)

        event = {
            "id": "event123",
            "extendedProperties": {
                "shared": {
                    "origin_calendar_id": "origin@example.com"
                }
            }
        }

        origin = engine.get_origin_calendar_id(event, None, "source@example.com")
        assert origin == "origin@example.com"

    def test_get_origin_calendar_id_defaults_to_source(self, db):
        """Test origin defaults to source calendar if first time seeing event."""
        engine = SyncEngine(db)

        event = {
            "id": "event123",
            "summary": "New Event"
        }

        origin = engine.get_origin_calendar_id(event, None, "source@example.com")
        assert origin == "source@example.com"

    def test_resolve_conflict_source_wins(self, db):
        """Test conflict resolution when source is origin."""
        engine = SyncEngine(db)

        source_event = {"id": "src_1", "summary": "Source Version"}
        dest_event = {"id": "dst_1", "summary": "Dest Version"}

        mapping = EventMapping(
            sync_config_id=uuid.uuid4(),
            source_event_id="src_1",
            dest_event_id="dst_1",
            sync_cluster_id=uuid.uuid4(),
            content_hash="hash",
            origin_calendar_id="source@example.com"
        )

        winner = engine.resolve_conflict(
            source_event,
            dest_event,
            mapping,
            source_calendar_id="source@example.com"
        )

        assert winner == "source_wins"

    def test_resolve_conflict_dest_wins(self, db):
        """Test conflict resolution when destination is origin."""
        engine = SyncEngine(db)

        source_event = {"id": "src_1", "summary": "Source Version"}
        dest_event = {"id": "dst_1", "summary": "Dest Version"}

        mapping = EventMapping(
            sync_config_id=uuid.uuid4(),
            source_event_id="src_1",
            dest_event_id="dst_1",
            sync_cluster_id=uuid.uuid4(),
            content_hash="hash",
            origin_calendar_id="destination@example.com"
        )

        winner = engine.resolve_conflict(
            source_event,
            dest_event,
            mapping,
            source_calendar_id="source@example.com"
        )

        assert winner == "dest_wins"


@pytest.mark.unit
class TestBidirectionalSyncFlow:
    """Test complete bi-directional sync flows."""

    @patch('app.core.sync_engine.build')
    def test_bidirectional_sync_loop_prevention(self, mock_build, db, test_user):
        """Test bi-directional sync prevents infinite loops."""
        # Setup mocks
        mock_src_service = Mock()
        mock_dst_service = Mock()
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        # Event in source calendar that was created by sync system
        source_event_synced = {
            "id": "src_event_1",
            "summary": "Event from B→A sync",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T09:00:00Z",
            "extendedProperties": {
                "shared": {
                    "synced_by_system": "true",  # CRITICAL: Loop prevention flag
                    "source_id": "original_from_b"
                }
            }
        }

        # Normal event in source calendar
        source_event_normal = {
            "id": "src_event_2",
            "summary": "Normal Event",
            "start": {"dateTime": "2024-01-15T14:00:00Z"},
            "end": {"dateTime": "2024-01-15T15:00:00Z"},
            "updated": "2024-01-15T13:00:00Z",
        }

        # Mock fetch_events
        mock_src_service.events.return_value.list.return_value.execute.return_value = {
            "items": [source_event_synced, source_event_normal],
            "nextPageToken": None,
        }
        mock_dst_service.events.return_value.list.return_value.execute.return_value = {
            "items": [],
            "nextPageToken": None,
        }

        # Mock insert response
        mock_dst_service.events.return_value.insert.return_value.execute.return_value = {
            "id": "dest_event_1",
            "updated": "2024-01-15T14:00:00Z",
        }

        # Create sync config
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_a_to_b",
        )
        db.add(sync_config)
        db.commit()

        # Run sync
        engine = SyncEngine(db)
        result = engine.sync_calendars(
            sync_config_id=str(sync_config.id),
            source_creds=Mock(),
            dest_creds=Mock(),
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            lookahead_days=90,
        )

        # Only normal event should be synced, synced event should be skipped
        assert result["created"] == 1  # Only src_event_2
        assert result["updated"] == 0
        assert result["deleted"] == 0

        # Verify only normal event was mapped
        mappings = db.query(EventMapping).filter(
            EventMapping.sync_config_id == sync_config.id
        ).all()
        assert len(mappings) == 1
        assert mappings[0].source_event_id == "src_event_2"

    @patch('app.core.sync_engine.build')
    def test_sync_with_privacy_mode_creates_placeholder(self, mock_build, db, test_user):
        """Test privacy mode creates placeholder events."""
        # Setup mocks
        mock_src_service = Mock()
        mock_dst_service = Mock()
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        # Confidential source event
        source_event = {
            "id": "src_event_1",
            "summary": "Secret Client Meeting",
            "description": "Discuss confidential matters",
            "location": "Executive Suite",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T09:00:00Z",
            "attendees": [{"email": "ceo@example.com"}],
        }

        # Mock fetch_events
        mock_src_service.events.return_value.list.return_value.execute.return_value = {
            "items": [source_event],
            "nextPageToken": None,
        }
        mock_dst_service.events.return_value.list.return_value.execute.return_value = {
            "items": [],
            "nextPageToken": None,
        }

        # Mock insert
        inserted_payload = None
        def capture_insert(*args, **kwargs):
            nonlocal inserted_payload
            inserted_payload = kwargs.get('body')
            return Mock(execute=Mock(return_value={
                "id": "dest_event_1",
                "updated": "2024-01-15T10:00:00Z",
            }))

        mock_dst_service.events.return_value.insert.side_effect = capture_insert

        # Create sync config with privacy mode
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            sync_lookahead_days=90,
            privacy_mode_enabled=True,
            privacy_placeholder_text="Personal appointment",
        )
        db.add(sync_config)
        db.commit()

        # Run sync
        engine = SyncEngine(db)
        result = engine.sync_calendars(
            sync_config_id=str(sync_config.id),
            source_creds=Mock(),
            dest_creds=Mock(),
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            lookahead_days=90,
            privacy_mode_enabled=True,
            privacy_placeholder_text="Personal appointment",
        )

        assert result["created"] == 1

        # Verify privacy transformation was applied
        assert inserted_payload is not None
        assert inserted_payload["summary"] == "Personal appointment"
        assert inserted_payload["description"] == ""
        assert inserted_payload["location"] == ""
        assert "attendees" not in inserted_payload

        # Time should be preserved
        assert inserted_payload["start"] == source_event["start"]
        assert inserted_payload["end"] == source_event["end"]

        # Should be marked as privacy mode
        assert inserted_payload["extendedProperties"]["shared"]["privacy_mode"] == "true"

        # Verify mapping was created with privacy flag
        mapping = db.query(EventMapping).filter(
            EventMapping.source_event_id == "src_event_1"
        ).first()
        assert mapping is not None
        assert mapping.is_privacy_mode is True

    @patch('app.core.sync_engine.build')
    def test_conflict_resolution_origin_wins(self, mock_build, db, test_user):
        """Test conflict resolution when both sides modified the same event."""
        # Setup mocks
        mock_src_service = Mock()
        mock_dst_service = Mock()
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        # Source event modified recently
        source_event = {
            "id": "src_event_1",
            "summary": "Source Modified Version",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T10:30:00Z",  # More recent
        }

        # Destination event also modified (but destination is origin)
        dest_event = {
            "id": "dest_event_1",
            "summary": "Dest Modified Version",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T10:25:00Z",  # Also recent
            "extendedProperties": {
                "shared": {
                    "source_id": "src_event_1",
                    "origin_calendar_id": "dst@example.com"  # Destination is origin
                }
            }
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

        # Create sync config and existing mapping
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_a_to_b",
        )
        db.add(sync_config)
        db.flush()

        # Create mapping with origin = destination and old timestamps
        # Note: SQLite doesn't support timezone-aware datetimes, so we store as UTC naive
        existing_mapping = EventMapping(
            sync_config_id=sync_config.id,
            source_event_id="src_event_1",
            dest_event_id="dest_event_1",
            sync_cluster_id=uuid.uuid4(),
            content_hash="old_hash",
            origin_calendar_id="dst@example.com",  # Origin is destination
            source_last_modified=datetime.datetime(2024, 1, 15, 9, 0, 0),
            dest_last_modified=datetime.datetime(2024, 1, 15, 9, 0, 0),
        )
        db.add(existing_mapping)
        db.commit()

        # Run sync
        engine = SyncEngine(db)
        result = engine.sync_calendars(
            sync_config_id=str(sync_config.id),
            source_creds=Mock(),
            dest_creds=Mock(),
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            lookahead_days=90,
        )

        # Destination is origin, so destination wins - no update should occur
        assert result["created"] == 0
        assert result["updated"] == 0  # Origin wins, so no update
        assert result["deleted"] == 0


@pytest.mark.unit
class TestBidirectionalEdgeCases:
    """Test edge cases in bi-directional sync."""

    @patch('app.core.sync_engine.build')
    def test_sync_handles_event_without_extended_properties(self, mock_build, db):
        """Test sync handles events that don't have extended properties."""
        engine = SyncEngine(db)

        # Event without any extended properties
        event = {
            "id": "event123",
            "summary": "Normal Event"
        }

        should_skip, reason = engine.should_skip_event(event, "config_123")
        assert should_skip is False
        assert reason == ""

        origin = engine.get_origin_calendar_id(event, None, "source@example.com")
        assert origin == "source@example.com"

    @patch('app.core.sync_engine.build')
    def test_sync_handles_event_with_empty_shared_properties(self, mock_build, db):
        """Test sync handles events with empty shared properties."""
        engine = SyncEngine(db)

        event = {
            "id": "event123",
            "summary": "Event",
            "extendedProperties": {
                "shared": {}
            }
        }

        should_skip, reason = engine.should_skip_event(event, "config_123")
        assert should_skip is False

        origin = engine.get_origin_calendar_id(event, None, "source@example.com")
        assert origin == "source@example.com"

    @patch('app.core.sync_engine.build')
    def test_privacy_mode_toggle_updates_existing_event(self, mock_build, db, test_user):
        """Test toggling privacy mode updates existing synced events."""
        # Setup mocks
        mock_src_service = Mock()
        mock_dst_service = Mock()
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        # Source event (non-private)
        source_event = {
            "id": "src_event_1",
            "summary": "Meeting Title",
            "description": "Meeting details",
            "location": "Room A",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T09:00:00Z",
        }

        # Existing destination event (was synced with details)
        dest_event = {
            "id": "dest_event_1",
            "summary": "Meeting Title",
            "description": "Meeting details",
            "location": "Room A",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T09:00:00Z",
            "extendedProperties": {
                "shared": {
                    "source_id": "src_event_1"
                }
            }
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

        # Mock update
        updated_payload = None
        def capture_update(*args, **kwargs):
            nonlocal updated_payload
            updated_payload = kwargs.get('body')
            return Mock(execute=Mock(return_value={
                "id": "dest_event_1",
                "updated": "2024-01-15T10:00:00Z",
            }))

        mock_dst_service.events.return_value.update.side_effect = capture_update

        # Create sync config with privacy mode NOW enabled
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            sync_lookahead_days=90,
            privacy_mode_enabled=True,
            privacy_placeholder_text="Busy",
        )
        db.add(sync_config)
        db.commit()

        # Run sync with privacy mode enabled
        engine = SyncEngine(db)
        result = engine.sync_calendars(
            sync_config_id=str(sync_config.id),
            source_creds=Mock(),
            dest_creds=Mock(),
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            lookahead_days=90,
            privacy_mode_enabled=True,
            privacy_placeholder_text="Busy",
        )

        # Should update existing event to privacy placeholder
        assert result["created"] == 0
        assert result["updated"] == 1
        assert result["deleted"] == 0

        # Verify privacy was applied
        assert updated_payload is not None
        assert updated_payload["summary"] == "Busy"
        assert updated_payload["description"] == ""
        assert updated_payload["location"] == ""

    @patch('app.core.sync_engine.build')
    def test_sync_with_mixed_privacy_settings(self, mock_build, db, test_user):
        """Test that different privacy settings can be used for forward and reverse directions."""
        # This is a conceptual test showing different configs can have different privacy settings

        # Create A→B config with privacy enabled
        config_a_to_b = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_a@example.com",
            dest_calendar_id="calendar_b@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_a_to_b",
            privacy_mode_enabled=True,
            privacy_placeholder_text="Work event",
        )
        db.add(config_a_to_b)
        db.flush()

        # Create B→A config with privacy disabled
        config_b_to_a = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_b@example.com",
            dest_calendar_id="calendar_a@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_b_to_a",
            paired_config_id=config_a_to_b.id,
            privacy_mode_enabled=False,  # No privacy in reverse direction
        )
        db.add(config_b_to_a)
        db.flush()

        # Link them
        config_a_to_b.paired_config_id = config_b_to_a.id
        db.commit()

        # Verify configs are created correctly
        assert config_a_to_b.privacy_mode_enabled is True
        assert config_b_to_a.privacy_mode_enabled is False
        assert config_a_to_b.paired_config_id == config_b_to_a.id
        assert config_b_to_a.paired_config_id == config_a_to_b.id

    @patch('app.core.sync_engine.build')
    def test_sync_preserves_origin_across_updates(self, mock_build, db, test_user):
        """Test that origin_calendar_id is preserved across multiple syncs."""
        # Setup mocks
        mock_src_service = Mock()
        mock_dst_service = Mock()
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        # Source event
        source_event = {
            "id": "src_event_1",
            "summary": "Event Version 1",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T09:00:00Z",
        }

        # Mock fetch - no destination events yet (first sync)
        mock_src_service.events.return_value.list.return_value.execute.return_value = {
            "items": [source_event],
            "nextPageToken": None,
        }
        mock_dst_service.events.return_value.list.return_value.execute.return_value = {
            "items": [],
            "nextPageToken": None,
        }

        # Mock insert
        mock_dst_service.events.return_value.insert.return_value.execute.return_value = {
            "id": "dest_event_1",
            "updated": "2024-01-15T10:00:00Z",
        }

        # Create sync config
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            sync_lookahead_days=90,
        )
        db.add(sync_config)
        db.commit()

        # First sync - creates event
        engine = SyncEngine(db)
        result1 = engine.sync_calendars(
            sync_config_id=str(sync_config.id),
            source_creds=Mock(),
            dest_creds=Mock(),
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            lookahead_days=90,
        )

        assert result1["created"] == 1

        # Verify mapping has origin set
        mapping = db.query(EventMapping).filter(
            EventMapping.source_event_id == "src_event_1"
        ).first()
        assert mapping is not None
        assert mapping.origin_calendar_id == "src@example.com"

        # Now simulate second sync with updated event
        mock_build.side_effect = [mock_src_service, mock_dst_service]

        source_event["summary"] = "Event Version 2"
        source_event["updated"] = "2024-01-15T11:00:00Z"

        dest_event = {
            "id": "dest_event_1",
            "summary": "Event Version 1",  # Old version
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "updated": "2024-01-15T10:00:00Z",
            "extendedProperties": {
                "shared": {
                    "source_id": "src_event_1",
                    "origin_calendar_id": "src@example.com"
                }
            }
        }

        mock_src_service.events.return_value.list.return_value.execute.return_value = {
            "items": [source_event],
            "nextPageToken": None,
        }
        mock_dst_service.events.return_value.list.return_value.execute.return_value = {
            "items": [dest_event],
            "nextPageToken": None,
        }

        mock_dst_service.events.return_value.update.return_value.execute.return_value = {
            "id": "dest_event_1",
            "updated": "2024-01-15T11:05:00Z",
        }

        # Second sync - updates event
        result2 = engine.sync_calendars(
            sync_config_id=str(sync_config.id),
            source_creds=Mock(),
            dest_creds=Mock(),
            source_calendar_id="src@example.com",
            dest_calendar_id="dst@example.com",
            lookahead_days=90,
        )

        assert result2["updated"] == 1

        # Verify origin is still preserved
        db.refresh(mapping)
        assert mapping.origin_calendar_id == "src@example.com"
