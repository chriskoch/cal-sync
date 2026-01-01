"""E2E test for privacy settings - simulates actual user flow."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_privacy_settings_full_user_flow(
    client: TestClient, auth_headers: dict, db: Session
):
    """
    Simulate the exact user flow:
    1. Create sync config with privacy enabled
    2. List configs to see if privacy settings are returned
    3. Trigger sync to see if privacy is applied
    """
    # Step 1: Create sync config with privacy enabled
    create_response = client.post(
        "/sync/config",
        json={
            "source_calendar_id": "business@example.com",
            "dest_calendar_id": "personal@example.com",
            "sync_lookahead_days": 90,
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Busy - Work",
        },
        headers=auth_headers,
    )

    assert create_response.status_code == 201
    created_config = create_response.json()

    print("\n=== Step 1: Created Config ===")
    print(f"Config ID: {created_config['id']}")
    print(f"Privacy Enabled in Response: {created_config.get('privacy_mode_enabled')}")
    print(f"Privacy Placeholder in Response: {created_config.get('privacy_placeholder_text')}")

    # Verify privacy settings are in the creation response
    assert created_config["privacy_mode_enabled"] is True, "Privacy mode should be enabled in create response"
    assert created_config["privacy_placeholder_text"] == "Busy - Work", "Privacy placeholder should be in create response"

    # Step 2: List configs (this is what Dashboard does after creation)
    list_response = client.get("/sync/config", headers=auth_headers)

    assert list_response.status_code == 200
    configs = list_response.json()

    print("\n=== Step 2: Listed Configs ===")
    print(f"Number of configs: {len(configs)}")

    # Find our config in the list
    our_config = None
    for config in configs:
        if config["id"] == created_config["id"]:
            our_config = config
            break

    assert our_config is not None, "Created config should be in the list"

    print(f"Privacy Enabled in List: {our_config.get('privacy_mode_enabled')}")
    print(f"Privacy Placeholder in List: {our_config.get('privacy_placeholder_text')}")

    # THIS IS THE KEY TEST - verify privacy settings are in the list response
    assert our_config["privacy_mode_enabled"] is True, "Privacy mode should be enabled in list response"
    assert our_config["privacy_placeholder_text"] == "Busy - Work", "Privacy placeholder should be in list response"


def test_bidirectional_with_only_forward_privacy_enabled(
    client: TestClient, auth_headers: dict, db: Session
):
    """
    Test bidirectional sync with privacy ONLY on forward direction.
    This replicates the user's scenario.
    """
    # Create bidirectional sync with privacy only on forward direction
    create_response = client.post(
        "/sync/config",
        json={
            "source_calendar_id": "business@example.com",
            "dest_calendar_id": "personal@example.com",
            "sync_lookahead_days": 90,
            "enable_bidirectional": True,
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Work Meeting",
            "reverse_privacy_mode_enabled": False,  # Explicitly disabled
        },
        headers=auth_headers,
    )

    assert create_response.status_code == 201
    forward_config = create_response.json()

    print("\n=== Bidirectional with Forward Privacy Only ==")
    print(f"Forward Config ID: {forward_config['id']}")
    print(f"Forward Privacy Enabled: {forward_config.get('privacy_mode_enabled')}")
    print(f"Forward Placeholder: {forward_config.get('privacy_placeholder_text')}")

    # Verify forward config has privacy enabled
    assert forward_config["privacy_mode_enabled"] is True
    assert forward_config["privacy_placeholder_text"] == "Work Meeting"

    # List configs to get both
    list_response = client.get("/sync/config", headers=auth_headers)
    assert list_response.status_code == 200
    configs = list_response.json()

    # Find reverse config
    reverse_in_list = None
    for config in configs:
        if config["id"] == forward_config.get("paired_config_id"):
            reverse_in_list = config
            break

    print(f"\nReverse Config Found: {reverse_in_list is not None}")
    if reverse_in_list:
        print(f"Reverse Privacy Enabled: {reverse_in_list.get('privacy_mode_enabled')}")
        print(f"Reverse Placeholder: {reverse_in_list.get('privacy_placeholder_text')}")

    assert reverse_in_list is not None
    assert reverse_in_list["privacy_mode_enabled"] is False
    # Reverse should have a placeholder text (either default or fallback)
    assert reverse_in_list["privacy_placeholder_text"] is not None


def test_bidirectional_privacy_settings_full_user_flow(
    client: TestClient, auth_headers: dict, db: Session
):
    """
    Test bidirectional sync with different privacy settings for each direction.
    """
    # Create bidirectional sync with privacy
    create_response = client.post(
        "/sync/config",
        json={
            "source_calendar_id": "business@example.com",
            "dest_calendar_id": "personal@example.com",
            "sync_lookahead_days": 90,
            "enable_bidirectional": True,
            "privacy_mode_enabled": True,
            "privacy_placeholder_text": "Work Meeting",
            "reverse_privacy_mode_enabled": True,
            "reverse_privacy_placeholder_text": "Personal Time",
        },
        headers=auth_headers,
    )

    assert create_response.status_code == 201
    forward_config = create_response.json()

    print("\n=== Bidirectional Config Creation ===")
    print(f"Forward Config ID: {forward_config['id']}")
    print(f"Forward Privacy: {forward_config.get('privacy_mode_enabled')}")
    print(f"Forward Placeholder: {forward_config.get('privacy_placeholder_text')}")
    print(f"Paired Config ID: {forward_config.get('paired_config_id')}")

    # Verify forward config has correct privacy settings
    assert forward_config["privacy_mode_enabled"] is True
    assert forward_config["privacy_placeholder_text"] == "Work Meeting"

    # List configs to get both forward and reverse
    list_response = client.get("/sync/config", headers=auth_headers)
    assert list_response.status_code == 200
    configs = list_response.json()

    # Find both configs
    forward_in_list = None
    reverse_in_list = None

    for config in configs:
        if config["id"] == forward_config["id"]:
            forward_in_list = config
        elif config["id"] == forward_config.get("paired_config_id"):
            reverse_in_list = config

    print("\n=== Bidirectional Configs in List ===")
    print(f"Forward in list: {forward_in_list is not None}")
    print(f"Reverse in list: {reverse_in_list is not None}")

    if forward_in_list:
        print(f"Forward Privacy in List: {forward_in_list.get('privacy_mode_enabled')}")
        print(f"Forward Placeholder in List: {forward_in_list.get('privacy_placeholder_text')}")

    if reverse_in_list:
        print(f"Reverse Privacy in List: {reverse_in_list.get('privacy_mode_enabled')}")
        print(f"Reverse Placeholder in List: {reverse_in_list.get('privacy_placeholder_text')}")

    # Verify both configs have correct privacy settings
    assert forward_in_list is not None
    assert forward_in_list["privacy_mode_enabled"] is True
    assert forward_in_list["privacy_placeholder_text"] == "Work Meeting"

    assert reverse_in_list is not None
    assert reverse_in_list["privacy_mode_enabled"] is True
    assert reverse_in_list["privacy_placeholder_text"] == "Personal Time"
