"""Tests for privacy settings in sync configurations."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.sync_config import SyncConfig


def test_create_one_way_sync_with_privacy_enabled(
    client: TestClient, auth_headers: dict, db: Session
):
    """Test creating one-way sync with privacy mode enabled."""
    response = client.post(
        "/sync/config",
        json={
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "sync_lookahead_days": 90,
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Busy",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    # Verify privacy settings in response
    assert data["privacy_mode_enabled"] is True
    assert data["privacy_placeholder_text"] == "Busy"

    # Verify privacy settings in database
    config = db.query(SyncConfig).filter_by(id=data["id"]).first()
    assert config is not None
    assert config.privacy_mode_enabled is True
    assert config.privacy_placeholder_text == "Busy"


def test_create_one_way_sync_with_privacy_disabled(
    client: TestClient, auth_headers: dict, db: Session
):
    """Test creating one-way sync with privacy mode disabled."""
    response = client.post(
        "/sync/config",
        json={
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "sync_lookahead_days": 90,
            "privacy_mode_enabled": False,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    # Verify privacy settings in response
    assert data["privacy_mode_enabled"] is False
    # When privacy is disabled, placeholder text should still have a default
    assert data["privacy_placeholder_text"] is not None

    # Verify privacy settings in database
    config = db.query(SyncConfig).filter_by(id=data["id"]).first()
    assert config is not None
    assert config.privacy_mode_enabled is False
    assert config.privacy_placeholder_text is not None


def test_create_bidirectional_sync_with_privacy_both_directions(
    client: TestClient, auth_headers: dict, db: Session
):
    """Test creating bidirectional sync with privacy enabled in both directions."""
    response = client.post(
        "/sync/config",
        json={
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "sync_lookahead_days": 90,
            "enable_bidirectional": True,
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Work meeting",
            "reverse_privacy_mode_enabled": True,
            "reverse_privacy_placeholder_text": "Personal time",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    # Verify forward config (A→B) privacy settings
    assert data["privacy_mode_enabled"] is True
    assert data["privacy_placeholder_text"] == "Work meeting"

    # Get both configs from database
    forward_config = db.query(SyncConfig).filter_by(id=data["id"]).first()
    reverse_config = db.query(SyncConfig).filter_by(id=data["paired_config_id"]).first()

    assert forward_config is not None
    assert reverse_config is not None

    # Verify forward config (A→B) privacy
    assert forward_config.privacy_mode_enabled is True
    assert forward_config.privacy_placeholder_text == "Work meeting"

    # Verify reverse config (B→A) privacy
    assert reverse_config.privacy_mode_enabled is True
    assert reverse_config.privacy_placeholder_text == "Personal time"


def test_create_bidirectional_sync_with_privacy_one_direction(
    client: TestClient, auth_headers: dict, db: Session
):
    """Test creating bidirectional sync with privacy only in forward direction."""
    response = client.post(
        "/sync/config",
        json={
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "sync_lookahead_days": 90,
            "enable_bidirectional": True,
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Work meeting",
            "reverse_privacy_mode_enabled": False,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    # Get both configs from database
    forward_config = db.query(SyncConfig).filter_by(id=data["id"]).first()
    reverse_config = db.query(SyncConfig).filter_by(id=data["paired_config_id"]).first()

    assert forward_config is not None
    assert reverse_config is not None

    # Verify forward config (A→B) has privacy enabled
    assert forward_config.privacy_mode_enabled is True
    assert forward_config.privacy_placeholder_text == "Work meeting"

    # Verify reverse config (B→A) has privacy disabled
    assert reverse_config.privacy_mode_enabled is False


def test_create_bidirectional_sync_privacy_defaults_to_forward_when_not_specified(
    client: TestClient, auth_headers: dict, db: Session
):
    """Test that reverse privacy defaults to forward privacy settings when not specified."""
    response = client.post(
        "/sync/config",
        json={
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "sync_lookahead_days": 90,
            "enable_bidirectional": True,
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Busy",
            # reverse_privacy_mode_enabled not specified
            # reverse_privacy_placeholder_text not specified
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    # Get both configs from database
    forward_config = db.query(SyncConfig).filter_by(id=data["id"]).first()
    reverse_config = db.query(SyncConfig).filter_by(id=data["paired_config_id"]).first()

    assert forward_config is not None
    assert reverse_config is not None

    # Both should have same privacy settings
    assert forward_config.privacy_mode_enabled is True
    assert forward_config.privacy_placeholder_text == "Busy"
    assert reverse_config.privacy_mode_enabled is True
    assert reverse_config.privacy_placeholder_text == "Busy"


def test_update_privacy_settings(
    client: TestClient, auth_headers: dict, db: Session
):
    """Test updating privacy settings on an existing sync config."""
    # Create a config first
    response = client.post(
        "/sync/config",
        json={
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "sync_lookahead_days": 90,
            "privacy_mode_enabled": False,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    config_id = response.json()["id"]

    # Update privacy settings
    update_response = client.patch(
        f"/sync/config/{config_id}",
        json={
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Out of office",
        },
        headers=auth_headers,
    )

    assert update_response.status_code == 200
    updated_data = update_response.json()

    # Verify updated privacy settings in response
    assert updated_data["privacy_mode_enabled"] is True
    assert updated_data["privacy_placeholder_text"] == "Out of office"

    # Verify in database
    config = db.query(SyncConfig).filter_by(id=config_id).first()
    assert config is not None
    assert config.privacy_mode_enabled is True
    assert config.privacy_placeholder_text == "Out of office"


def test_privacy_placeholder_text_persists_when_mode_disabled(
    client: TestClient, auth_headers: dict, db: Session
):
    """Test that privacy placeholder text is preserved even when privacy mode is disabled."""
    # Create config with privacy enabled
    response = client.post(
        "/sync/config",
        json={
            "source_calendar_id": "source@example.com",
            "dest_calendar_id": "dest@example.com",
            "sync_lookahead_days": 90,
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Custom placeholder",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    config_id = response.json()["id"]

    # Disable privacy mode
    update_response = client.patch(
        f"/sync/config/{config_id}",
        json={
            "privacy_mode_enabled": False,
        },
        headers=auth_headers,
    )

    assert update_response.status_code == 200
    updated_data = update_response.json()

    # Privacy mode should be disabled but placeholder text should persist
    assert updated_data["privacy_mode_enabled"] is False
    assert updated_data["privacy_placeholder_text"] == "Custom placeholder"

    # Verify in database
    config = db.query(SyncConfig).filter_by(id=config_id).first()
    assert config is not None
    assert config.privacy_mode_enabled is False
    assert config.privacy_placeholder_text == "Custom placeholder"
