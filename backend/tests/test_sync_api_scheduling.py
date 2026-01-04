"""
Integration tests for sync API endpoints with auto-sync scheduling.

Tests the sync config API endpoints with scheduler integration.
"""

import pytest
from fastapi import status
from unittest.mock import patch, Mock
import uuid


@pytest.mark.integration
class TestCreateSyncConfigWithScheduling:
    """Test creating sync configs with auto-sync scheduling."""

    @patch('app.api.sync.get_scheduler')
    def test_create_config_with_auto_sync_enabled(self, mock_get_scheduler, client, auth_headers, db):
        """Creating config with auto_sync_enabled should schedule job."""
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        payload = {
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "sync_lookahead_days": 90,
            "auto_sync_enabled": True,
            "auto_sync_cron": "0 */6 * * *",
            "auto_sync_timezone": "UTC"
        }

        response = client.post("/sync/config", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["auto_sync_enabled"] is True
        assert data["auto_sync_cron"] == "0 */6 * * *"
        assert data["auto_sync_timezone"] == "UTC"

        # Verify scheduler.add_job was called
        assert mock_scheduler.add_job.called
        call_args = mock_scheduler.add_job.call_args
        assert call_args[0][2] == "0 */6 * * *"  # cron_expr
        assert call_args[0][3] == "UTC"  # timezone_str

    @patch('app.api.sync.get_scheduler')
    def test_create_config_without_auto_sync(self, mock_get_scheduler, client, auth_headers):
        """Creating config with auto_sync_enabled=False should not schedule job."""
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        payload = {
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "sync_lookahead_days": 90,
            "auto_sync_enabled": False
        }

        response = client.post("/sync/config", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["auto_sync_enabled"] is False

        # Verify scheduler.add_job was NOT called
        assert not mock_scheduler.add_job.called

    def test_create_config_with_invalid_cron(self, client, auth_headers):
        """Creating config with invalid cron should return 422."""
        payload = {
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "auto_sync_enabled": True,
            "auto_sync_cron": "invalid cron",
            "auto_sync_timezone": "UTC"
        }

        response = client.post("/sync/config", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "cron" in response.text.lower()

    def test_create_config_with_invalid_timezone(self, client, auth_headers):
        """Creating config with invalid timezone should return 422."""
        payload = {
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "auto_sync_enabled": True,
            "auto_sync_cron": "0 */6 * * *",
            "auto_sync_timezone": "Invalid/Timezone"
        }

        response = client.post("/sync/config", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "timezone" in response.text.lower()

    def test_create_config_auto_sync_enabled_without_cron(self, client, auth_headers):
        """Creating config with auto_sync_enabled but no cron should return 422."""
        payload = {
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "auto_sync_enabled": True,
            # Missing auto_sync_cron
            "auto_sync_timezone": "UTC"
        }

        response = client.post("/sync/config", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch('app.api.sync.get_scheduler')
    def test_create_bidirectional_config_with_auto_sync(self, mock_get_scheduler, client, auth_headers):
        """Creating bidirectional config with auto_sync should schedule both directions."""
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        payload = {
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "enable_bidirectional": True,
            "auto_sync_enabled": True,
            "auto_sync_cron": "0 */6 * * *",
            "auto_sync_timezone": "America/New_York"
        }

        response = client.post("/sync/config", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["auto_sync_enabled"] is True
        assert data["sync_direction"] == "bidirectional_a_to_b"

        # Verify scheduler.add_job was called twice (for both directions)
        assert mock_scheduler.add_job.call_count == 2

    @patch('app.api.sync.get_scheduler')
    def test_create_config_with_different_timezones(self, mock_get_scheduler, client, auth_headers):
        """Test creating configs with various timezones."""
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        timezones = [
            "UTC",
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "Australia/Sydney"
        ]

        for tz in timezones:
            payload = {
                "source_calendar_id": f"source_{tz}@example.com",
                "dest_calendar_id": f"dest_{tz}@example.com",
                "auto_sync_enabled": True,
                "auto_sync_cron": "0 0 * * *",
                "auto_sync_timezone": tz
            }

            response = client.post("/sync/config", json=payload, headers=auth_headers)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["auto_sync_timezone"] == tz


@pytest.mark.integration
class TestUpdateSyncConfigWithScheduling:
    """Test updating sync configs with auto-sync scheduling."""

    @patch('app.api.sync.get_scheduler')
    def test_update_config_enable_auto_sync(self, mock_get_scheduler, client, auth_headers, db, test_user):
        """Enabling auto-sync on existing config should add job."""
        from app.models.sync_config import SyncConfig

        # Create config without auto-sync
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            auto_sync_enabled=False
        )
        db.add(config)
        db.commit()

        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        # Enable auto-sync
        payload = {
            "auto_sync_enabled": True,
            "auto_sync_cron": "0 0 * * *",
            "auto_sync_timezone": "America/New_York"
        }

        response = client.patch(f"/sync/config/{config.id}", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["auto_sync_enabled"] is True
        assert data["auto_sync_cron"] == "0 0 * * *"

        # Verify scheduler.add_job was called
        assert mock_scheduler.add_job.called

    @patch('app.api.sync.get_scheduler')
    def test_update_config_disable_auto_sync(self, mock_get_scheduler, client, auth_headers, db, test_user):
        """Disabling auto-sync should remove job."""
        from app.models.sync_config import SyncConfig

        # Create config with auto-sync enabled
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            auto_sync_enabled=True,
            auto_sync_cron="0 */6 * * *",
            auto_sync_timezone="UTC"
        )
        db.add(config)
        db.commit()

        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        # Disable auto-sync
        payload = {
            "auto_sync_enabled": False
        }

        response = client.patch(f"/sync/config/{config.id}", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["auto_sync_enabled"] is False

        # Verify scheduler.remove_job was called
        assert mock_scheduler.remove_job.called

    @patch('app.api.sync.get_scheduler')
    def test_update_config_change_cron_expression(self, mock_get_scheduler, client, auth_headers, db, test_user):
        """Changing cron expression should update job."""
        from app.models.sync_config import SyncConfig

        # Create config with auto-sync
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            auto_sync_enabled=True,
            auto_sync_cron="0 */6 * * *",
            auto_sync_timezone="UTC"
        )
        db.add(config)
        db.commit()

        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        # Change cron expression
        payload = {
            "auto_sync_cron": "0 0 * * *"  # Daily instead of every 6 hours
        }

        response = client.patch(f"/sync/config/{config.id}", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["auto_sync_cron"] == "0 0 * * *"

        # Verify scheduler.add_job was called (replaces existing)
        assert mock_scheduler.add_job.called

    @patch('app.api.sync.get_scheduler')
    def test_update_config_change_timezone(self, mock_get_scheduler, client, auth_headers, db, test_user):
        """Changing timezone should update job."""
        from app.models.sync_config import SyncConfig

        # Create config with auto-sync
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            auto_sync_enabled=True,
            auto_sync_cron="0 9 * * *",
            auto_sync_timezone="UTC"
        )
        db.add(config)
        db.commit()

        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        # Change timezone
        payload = {
            "auto_sync_timezone": "America/New_York"
        }

        response = client.patch(f"/sync/config/{config.id}", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["auto_sync_timezone"] == "America/New_York"

        # Verify scheduler.add_job was called
        assert mock_scheduler.add_job.called

    @patch('app.api.sync.get_scheduler')
    def test_update_config_deactivate_removes_job(self, mock_get_scheduler, client, auth_headers, db, test_user):
        """Deactivating config should remove scheduled job."""
        from app.models.sync_config import SyncConfig

        # Create active config with auto-sync
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            is_active=True,
            auto_sync_enabled=True,
            auto_sync_cron="0 */6 * * *",
            auto_sync_timezone="UTC"
        )
        db.add(config)
        db.commit()

        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        # Deactivate config
        payload = {
            "is_active": False
        }

        response = client.patch(f"/sync/config/{config.id}", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False

        # Verify scheduler.remove_job was called
        assert mock_scheduler.remove_job.called

    def test_update_config_with_invalid_cron(self, client, auth_headers, db, test_user):
        """Updating with invalid cron should return 422."""
        from app.models.sync_config import SyncConfig

        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            auto_sync_enabled=False
        )
        db.add(config)
        db.commit()

        payload = {
            "auto_sync_enabled": True,
            "auto_sync_cron": "invalid"
        }

        response = client.patch(f"/sync/config/{config.id}", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
class TestDeleteSyncConfigWithScheduling:
    """Test deleting sync configs with scheduler integration."""

    @patch('app.api.sync.get_scheduler')
    def test_delete_config_removes_scheduled_job(self, mock_get_scheduler, client, auth_headers, db, test_user):
        """Deleting config should remove scheduled job."""
        from app.models.sync_config import SyncConfig

        # Create config with auto-sync
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            auto_sync_enabled=True,
            auto_sync_cron="0 */6 * * *",
            auto_sync_timezone="UTC"
        )
        db.add(config)
        db.commit()

        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        response = client.delete(f"/sync/config/{config.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify scheduler.remove_job was called
        assert mock_scheduler.remove_job.called
        call_args = mock_scheduler.remove_job.call_args
        assert call_args[0][0] == str(config.id)

    @patch('app.api.sync.get_scheduler')
    def test_delete_config_without_auto_sync(self, mock_get_scheduler, client, auth_headers, db, test_user):
        """Deleting config without auto-sync should still call remove_job."""
        from app.models.sync_config import SyncConfig

        # Create config without auto-sync
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            auto_sync_enabled=False
        )
        db.add(config)
        db.commit()

        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler

        response = client.delete(f"/sync/config/{config.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify scheduler.remove_job was called (safe to call even if no job exists)
        assert mock_scheduler.remove_job.called


@pytest.mark.integration
class TestSyncConfigResponseFormat:
    """Test that sync config responses include auto-sync fields."""

    def test_list_configs_includes_auto_sync_fields(self, client, auth_headers, db, test_user):
        """Listing configs should include auto-sync fields."""
        from app.models.sync_config import SyncConfig

        # Create config with auto-sync
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            auto_sync_enabled=True,
            auto_sync_cron="0 */6 * * *",
            auto_sync_timezone="America/New_York"
        )
        db.add(config)
        db.commit()

        response = client.get("/sync/config", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        configs = response.json()
        assert len(configs) > 0

        config_data = configs[0]
        assert "auto_sync_enabled" in config_data
        assert "auto_sync_cron" in config_data
        assert "auto_sync_timezone" in config_data
        assert config_data["auto_sync_enabled"] is True
        assert config_data["auto_sync_cron"] == "0 */6 * * *"
        assert config_data["auto_sync_timezone"] == "America/New_York"

    def test_config_defaults_for_new_configs(self, client, auth_headers):
        """New configs without auto-sync should have proper defaults."""
        payload = {
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com"
            # Not providing auto-sync fields
        }

        response = client.post("/sync/config", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["auto_sync_enabled"] is False
        assert data["auto_sync_cron"] is None
        assert data["auto_sync_timezone"] == "UTC"
