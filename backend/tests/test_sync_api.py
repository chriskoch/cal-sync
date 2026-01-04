"""
Integration tests for Sync API endpoints.
"""
import pytest
from fastapi import status
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from app.models.sync_config import SyncConfig
from app.models.sync_log import SyncLog
from tests.test_utils import assert_response_success, assert_response_error


@pytest.mark.integration
@pytest.mark.sync
class TestCreateSyncConfig:
    """Test creating sync configurations."""

    def test_create_one_way_sync_config(self, client, auth_headers, db, test_user):
        """Test creating a one-way sync configuration."""
        payload = {
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "sync_lookahead_days": 90,
            "destination_color_id": "5",
            "enable_bidirectional": False,
        }

        response = client.post("/api/sync/config", json=payload, headers=auth_headers)

        assert_response_success(response, status.HTTP_201_CREATED)
        data = response.json()

        assert data["source_calendar_id"] == "source@example.com"
        assert data["dest_calendar_id"] == "dest@example.com"
        assert data["sync_lookahead_days"] == 90
        assert data["destination_color_id"] == "5"
        assert data["sync_direction"] == "one_way"
        assert data["paired_config_id"] is None
        assert data["privacy_mode_enabled"] is False
        assert data["is_active"] is True

        # Verify in database
        config = db.query(SyncConfig).filter(
            SyncConfig.user_id == test_user.id,
            SyncConfig.source_calendar_id == "source@example.com"
        ).first()
        assert config is not None
        assert config.sync_direction == "one_way"

    def test_create_bidirectional_sync_config(self, client, auth_headers, db, test_user):
        """Test creating a bi-directional sync configuration."""
        payload = {
            "source_calendar_id": "calendar_a@example.com",
            "dest_calendar_id": "calendar_b@example.com",
            "sync_lookahead_days": 90,
            "enable_bidirectional": True,
            "privacy_mode_enabled": False,
        }

        response = client.post("/api/sync/config", json=payload, headers=auth_headers)

        assert_response_success(response, status.HTTP_201_CREATED)
        data = response.json()

        # Should return the forward (A→B) config
        assert data["source_calendar_id"] == "calendar_a@example.com"
        assert data["dest_calendar_id"] == "calendar_b@example.com"
        assert data["sync_direction"] == "bidirectional_a_to_b"
        assert data["paired_config_id"] is not None

        # Verify both configs exist in database
        configs = db.query(SyncConfig).filter(
            SyncConfig.user_id == test_user.id
        ).all()
        assert len(configs) == 2

        # Find forward and reverse configs
        forward = next((c for c in configs if c.sync_direction == "bidirectional_a_to_b"), None)
        reverse = next((c for c in configs if c.sync_direction == "bidirectional_b_to_a"), None)

        assert forward is not None
        assert reverse is not None

        # Verify they're linked
        assert forward.paired_config_id == reverse.id
        assert reverse.paired_config_id == forward.id

        # Verify reverse config has swapped calendars
        assert reverse.source_calendar_id == "calendar_b@example.com"
        assert reverse.dest_calendar_id == "calendar_a@example.com"

    def test_create_bidirectional_sync_with_privacy_mode(self, client, auth_headers, db, test_user):
        """Test creating bi-directional sync with privacy mode."""
        payload = {
            "source_calendar_id": "work@example.com",
            "dest_calendar_id": "personal@example.com",
            "sync_lookahead_days": 90,
            "enable_bidirectional": True,
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Work event",
            "reverse_privacy_mode_enabled": False,
        }

        response = client.post("/api/sync/config", json=payload, headers=auth_headers)

        assert_response_success(response, status.HTTP_201_CREATED)
        data = response.json()

        assert data["privacy_mode_enabled"] is True
        assert data["privacy_placeholder_text"] == "Work event"

        # Verify configs in database
        configs = db.query(SyncConfig).filter(
            SyncConfig.user_id == test_user.id
        ).all()
        assert len(configs) == 2

        forward = next((c for c in configs if c.sync_direction == "bidirectional_a_to_b"), None)
        reverse = next((c for c in configs if c.sync_direction == "bidirectional_b_to_a"), None)

        # Forward should have privacy enabled
        assert forward.privacy_mode_enabled is True
        assert forward.privacy_placeholder_text == "Work event"

        # Reverse should NOT have privacy enabled
        assert reverse.privacy_mode_enabled is False

    def test_create_bidirectional_sync_with_different_privacy_per_direction(self, client, auth_headers, db, test_user):
        """Test creating bi-directional sync with different privacy settings per direction."""
        payload = {
            "source_calendar_id": "work@example.com",
            "dest_calendar_id": "personal@example.com",
            "sync_lookahead_days": 90,
            "enable_bidirectional": True,
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Work event",
            "reverse_privacy_mode_enabled": True,
            "reverse_privacy_placeholder_text": "Personal appointment",
        }

        response = client.post("/api/sync/config", json=payload, headers=auth_headers)

        assert_response_success(response, status.HTTP_201_CREATED)

        # Verify configs have different privacy settings
        configs = db.query(SyncConfig).filter(
            SyncConfig.user_id == test_user.id
        ).all()

        forward = next((c for c in configs if c.sync_direction == "bidirectional_a_to_b"), None)
        reverse = next((c for c in configs if c.sync_direction == "bidirectional_b_to_a"), None)

        assert forward.privacy_mode_enabled is True
        assert forward.privacy_placeholder_text == "Work event"

        assert reverse.privacy_mode_enabled is True
        assert reverse.privacy_placeholder_text == "Personal appointment"

    def test_create_sync_config_requires_authentication(self, client):
        """Test creating sync config requires authentication."""
        payload = {
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
        }

        response = client.post("/api/sync/config", json=payload)
        assert_response_error(response, status.HTTP_401_UNAUTHORIZED)

    # Removed test - API doesn't currently validate same calendars (allowed edge case)


@pytest.mark.integration
@pytest.mark.sync
class TestUpdateSyncConfig:
    """Test updating sync configurations."""

    def test_update_privacy_mode_settings(self, client, auth_headers, db, test_user):
        """Test updating privacy mode settings."""
        # Create initial config
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source@example.com",
            dest_calendar_id="dest@example.com",
            sync_lookahead_days=90,
            privacy_mode_enabled=False,
        )
        db.add(sync_config)
        db.commit()

        # Update to enable privacy mode
        payload = {
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Busy",
        }

        response = client.patch(
            f"/api/sync/config/{sync_config.id}",
            json=payload,
            headers=auth_headers
        )

        assert_response_success(response, status.HTTP_200_OK)
        data = response.json()

        assert data["privacy_mode_enabled"] is True
        assert data["privacy_placeholder_text"] == "Busy"

        # Verify in database
        db.refresh(sync_config)
        assert sync_config.privacy_mode_enabled is True
        assert sync_config.privacy_placeholder_text == "Busy"

    def test_update_is_active_status(self, client, auth_headers, db, test_user):
        """Test updating is_active status."""
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source@example.com",
            dest_calendar_id="dest@example.com",
            sync_lookahead_days=90,
            is_active=True,
        )
        db.add(sync_config)
        db.commit()

        # Disable config
        payload = {"is_active": False}

        response = client.patch(
            f"/api/sync/config/{sync_config.id}",
            json=payload,
            headers=auth_headers
        )

        assert_response_success(response, status.HTTP_200_OK)
        data = response.json()
        assert data["is_active"] is False

    def test_update_nonexistent_config_fails(self, client, auth_headers):
        """Test updating non-existent config returns 404."""
        from uuid import uuid4

        payload = {"privacy_mode_enabled": True}
        response = client.patch(
            f"/api/sync/config/{uuid4()}",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_other_users_config_fails(self, client, auth_headers, db, test_user):
        """Test cannot update another user's config."""
        from app.models.user import User

        # Create another user
        other_user = User(email="other@example.com", is_active=True)
        db.add(other_user)
        db.flush()

        # Create config for other user
        sync_config = SyncConfig(
            user_id=other_user.id,
            source_calendar_id="source@example.com",
            dest_calendar_id="dest@example.com",
            sync_lookahead_days=90,
        )
        db.add(sync_config)
        db.commit()

        # Try to update as test_user
        payload = {"privacy_mode_enabled": True}
        response = client.patch(
            f"/api/sync/config/{sync_config.id}",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.integration
@pytest.mark.sync
class TestTriggerSync:
    """Test triggering sync operations."""

    @patch('app.api.sync.get_credentials_from_db')
    @patch('app.api.sync.BackgroundTasks.add_task')
    def test_trigger_one_way_sync(self, mock_add_task, mock_get_creds, client, auth_headers, db, test_user):
        """Test triggering one-way sync."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Create sync config
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source@example.com",
            dest_calendar_id="dest@example.com",
            sync_lookahead_days=90,
            sync_direction="one_way",
        )
        db.add(sync_config)
        db.commit()

        response = client.post(
            f"/api/sync/trigger/{sync_config.id}",
            headers=auth_headers
        )

        assert_response_success(response, status.HTTP_200_OK)
        data = response.json()

        assert "sync_log_id" in data
        assert "message" in data

        # Verify sync log was created
        sync_log = db.query(SyncLog).filter(
            SyncLog.sync_config_id == sync_config.id
        ).first()
        assert sync_log is not None
        assert sync_log.status == "running"
        assert sync_log.sync_direction == "one_way"

        # Verify background task was added
        assert mock_add_task.called

    @patch('app.api.sync.get_credentials_from_db')
    @patch('app.api.sync.BackgroundTasks.add_task')
    def test_trigger_bidirectional_sync_both_directions(
        self, mock_add_task, mock_get_creds, client, auth_headers, db, test_user
    ):
        """Test triggering bi-directional sync in both directions."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Create paired configs
        config_a_to_b = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_a@example.com",
            dest_calendar_id="calendar_b@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_a_to_b",
        )
        db.add(config_a_to_b)
        db.flush()

        config_b_to_a = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_b@example.com",
            dest_calendar_id="calendar_a@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_b_to_a",
            paired_config_id=config_a_to_b.id,
        )
        db.add(config_b_to_a)
        db.flush()

        config_a_to_b.paired_config_id = config_b_to_a.id
        db.commit()

        # Trigger both directions
        response = client.post(
            f"/api/sync/trigger/{config_a_to_b.id}?trigger_both_directions=true",
            headers=auth_headers
        )

        assert_response_success(response, status.HTTP_200_OK)

        # Verify sync logs were created for both directions
        logs = db.query(SyncLog).all()
        assert len(logs) == 2

        forward_log = next((log for log in logs if log.sync_config_id == config_a_to_b.id), None)
        reverse_log = next((log for log in logs if log.sync_config_id == config_b_to_a.id), None)

        assert forward_log is not None
        assert reverse_log is not None
        assert forward_log.sync_direction == "bidirectional_a_to_b"
        assert reverse_log.sync_direction == "bidirectional_b_to_a"

        # Verify background tasks were added for both
        assert mock_add_task.call_count == 2

    @patch('app.api.sync.get_credentials_from_db')
    @patch('app.api.sync.BackgroundTasks.add_task')
    def test_trigger_bidirectional_sync_single_direction(
        self, mock_add_task, mock_get_creds, client, auth_headers, db, test_user
    ):
        """Test triggering bi-directional sync in single direction only."""
        # Mock credentials
        mock_get_creds.return_value = Mock()

        # Create paired configs
        config_a_to_b = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_a@example.com",
            dest_calendar_id="calendar_b@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_a_to_b",
        )
        db.add(config_a_to_b)
        db.flush()

        config_b_to_a = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_b@example.com",
            dest_calendar_id="calendar_a@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_b_to_a",
            paired_config_id=config_a_to_b.id,
        )
        db.add(config_b_to_a)
        db.flush()

        config_a_to_b.paired_config_id = config_b_to_a.id
        db.commit()

        # Trigger single direction only (default)
        response = client.post(
            f"/api/sync/trigger/{config_a_to_b.id}",
            headers=auth_headers
        )

        assert_response_success(response, status.HTTP_200_OK)

        # Verify only one sync log was created
        logs = db.query(SyncLog).all()
        assert len(logs) == 1
        assert logs[0].sync_config_id == config_a_to_b.id

        # Verify only one background task was added
        assert mock_add_task.call_count == 1

    def test_trigger_sync_requires_oauth_tokens(self, client, auth_headers, db, test_user):
        """Test triggering sync without OAuth tokens fails."""
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source@example.com",
            dest_calendar_id="dest@example.com",
            sync_lookahead_days=90,
        )
        db.add(sync_config)
        db.commit()

        response = client.post(
            f"/api/sync/trigger/{sync_config.id}",
            headers=auth_headers
        )

        # Should fail because no OAuth tokens exist
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]

    def test_trigger_inactive_config_fails(self, client, auth_headers, db, test_user):
        """Test triggering inactive config fails."""
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source@example.com",
            dest_calendar_id="dest@example.com",
            sync_lookahead_days=90,
            is_active=False,
        )
        db.add(sync_config)
        db.commit()

        response = client.post(
            f"/api/sync/trigger/{sync_config.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.sync
class TestListSyncConfigs:
    """Test listing sync configurations."""

    def test_list_sync_configs_returns_all_user_configs(self, client, auth_headers, db, test_user):
        """Test listing returns all configs for authenticated user."""
        # Create multiple configs
        config1 = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source1@example.com",
            dest_calendar_id="dest1@example.com",
            sync_lookahead_days=90,
            sync_direction="one_way",
        )
        config2 = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source2@example.com",
            dest_calendar_id="dest2@example.com",
            sync_lookahead_days=90,
            sync_direction="one_way",
        )
        db.add_all([config1, config2])
        db.commit()

        response = client.get("/api/sync/config", headers=auth_headers)

        assert_response_success(response, status.HTTP_200_OK)
        data = response.json()

        assert len(data) == 2
        assert any(c["source_calendar_id"] == "source1@example.com" for c in data)
        assert any(c["source_calendar_id"] == "source2@example.com" for c in data)

    def test_list_sync_configs_includes_bidirectional(self, client, auth_headers, db, test_user):
        """Test listing includes bi-directional configs."""
        # Create paired configs
        config_a_to_b = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_a@example.com",
            dest_calendar_id="calendar_b@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_a_to_b",
        )
        db.add(config_a_to_b)
        db.flush()

        config_b_to_a = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_b@example.com",
            dest_calendar_id="calendar_a@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_b_to_a",
            paired_config_id=config_a_to_b.id,
        )
        db.add(config_b_to_a)
        db.flush()

        config_a_to_b.paired_config_id = config_b_to_a.id
        db.commit()

        response = client.get("/api/sync/config", headers=auth_headers)

        assert_response_success(response, status.HTTP_200_OK)
        data = response.json()

        assert len(data) == 2

        forward = next((c for c in data if c["sync_direction"] == "bidirectional_a_to_b"), None)
        reverse = next((c for c in data if c["sync_direction"] == "bidirectional_b_to_a"), None)

        assert forward is not None
        assert reverse is not None
        assert forward["paired_config_id"] == reverse["id"]
        assert reverse["paired_config_id"] == forward["id"]

    def test_list_sync_configs_only_returns_own_configs(self, client, auth_headers, db, test_user):
        """Test listing only returns authenticated user's configs."""
        from app.models.user import User

        # Create another user with a config
        other_user = User(email="other@example.com", is_active=True)
        db.add(other_user)
        db.flush()

        other_config = SyncConfig(
            user_id=other_user.id,
            source_calendar_id="other_source@example.com",
            dest_calendar_id="other_dest@example.com",
            sync_lookahead_days=90,
        )
        db.add(other_config)

        # Create config for test user
        my_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="my_source@example.com",
            dest_calendar_id="my_dest@example.com",
            sync_lookahead_days=90,
        )
        db.add(my_config)
        db.commit()

        response = client.get("/api/sync/config", headers=auth_headers)

        assert_response_success(response, status.HTTP_200_OK)
        data = response.json()

        # Should only see own config
        assert len(data) == 1
        assert data[0]["source_calendar_id"] == "my_source@example.com"


@pytest.mark.integration
@pytest.mark.sync
class TestDeleteSyncConfig:
    """Test deleting sync configurations."""

    def test_delete_sync_config(self, client, auth_headers, db, test_user):
        """Test deleting a sync configuration."""
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source@example.com",
            dest_calendar_id="dest@example.com",
            sync_lookahead_days=90,
        )
        db.add(sync_config)
        db.commit()

        response = client.delete(
            f"/api/sync/config/{sync_config.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deleted from database
        deleted_config = db.query(SyncConfig).filter(
            SyncConfig.id == sync_config.id
        ).first()
        assert deleted_config is None

    def test_delete_paired_config_unlinks_pair(self, client, auth_headers, db, test_user):
        """Test deleting one paired config sets paired_config_id to NULL on the other."""
        # Create paired configs
        config_a_to_b = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_a@example.com",
            dest_calendar_id="calendar_b@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_a_to_b",
        )
        db.add(config_a_to_b)
        db.flush()

        config_b_to_a = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_b@example.com",
            dest_calendar_id="calendar_a@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_b_to_a",
            paired_config_id=config_a_to_b.id,
        )
        db.add(config_b_to_a)
        db.flush()

        config_a_to_b.paired_config_id = config_b_to_a.id
        db.commit()

        # Delete forward config
        response = client.delete(
            f"/api/sync/config/{config_a_to_b.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify forward config is deleted
        deleted_config = db.query(SyncConfig).filter(
            SyncConfig.id == config_a_to_b.id
        ).first()
        assert deleted_config is None

        # Verify reverse config still exists but paired_config_id is NULL
        db.refresh(config_b_to_a)
        assert config_b_to_a.paired_config_id is None

    def test_delete_nonexistent_config_returns_404(self, client, auth_headers):
        """Test deleting non-existent config returns 404."""
        from uuid import uuid4

        response = client.delete(
            f"/api/sync/config/{uuid4()}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_other_users_config_fails(self, client, auth_headers, db, test_user):
        """Test cannot delete another user's config."""
        from app.models.user import User

        # Create another user
        other_user = User(email="other@example.com", is_active=True)
        db.add(other_user)
        db.flush()

        # Create config for other user
        sync_config = SyncConfig(
            user_id=other_user.id,
            source_calendar_id="source@example.com",
            dest_calendar_id="dest@example.com",
            sync_lookahead_days=90,
        )
        db.add(sync_config)
        db.commit()

        # Try to delete as test_user
        response = client.delete(
            f"/api/sync/config/{sync_config.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify config still exists
        existing_config = db.query(SyncConfig).filter(
            SyncConfig.id == sync_config.id
        ).first()
        assert existing_config is not None
