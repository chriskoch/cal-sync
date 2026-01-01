#!/usr/bin/env python3
"""
E2E Test: Privacy Mode for One-Way Sync

This test validates that privacy mode correctly hides event details while preserving time slots
in one-way calendar synchronization.

Usage:
    python3 backend/tests/e2e/e2e_test_privacy_one_way.py <ACCESS_TOKEN>

Prerequisites:
    - User must have valid OAuth tokens for both source and destination accounts
    - Calendars 'test-4' (source) and 'test-5' (destination) must exist

Test Flow:
    1. Create source event with full details (title, description, location, attendees)
    2. Create one-way sync with privacy mode enabled
    3. Trigger sync
    4. Verify destination event has placeholder text instead of actual details
    5. Verify time/date are preserved exactly
    6. Update source event details
    7. Resync
    8. Verify privacy is maintained in updated event
    9. Clean up all created resources
"""

import requests
import sys
from datetime import datetime, timedelta, timezone
import time

BASE_URL = "http://localhost:8000"

def print_step(step_num, description):
    """Print test step with formatting."""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {description}")
    print('='*80)

def print_success(message):
    """Print success message."""
    print(f"✓ {message}")

def print_error(message):
    """Print error message."""
    print(f"✗ ERROR: {message}")

def find_calendars(headers):
    """Find test-4 and test-5 calendars by their summary names."""
    print_step(0, "Finding test calendars")

    # Find test-4 (source)
    response = requests.get(f"{BASE_URL}/calendars/source/list", headers=headers)
    if response.status_code != 200:
        print_error(f"Failed to list source calendars: {response.text}")
        sys.exit(1)

    source_cal_id = None
    for cal in response.json()['calendars']:
        if cal['summary'] == 'test-4':
            source_cal_id = cal['id']
            print_success(f"Found test-4: {cal['id'][:30]}...")
            break

    if not source_cal_id:
        print_error("Calendar 'test-4' not found in source account")
        sys.exit(1)

    # Find test-5 (destination)
    response = requests.get(f"{BASE_URL}/calendars/destination/list", headers=headers)
    if response.status_code != 200:
        print_error(f"Failed to list destination calendars: {response.text}")
        sys.exit(1)

    dest_cal_id = None
    for cal in response.json()['calendars']:
        if cal['summary'] == 'test-5':
            dest_cal_id = cal['id']
            print_success(f"Found test-5: {cal['id'][:30]}...")
            break

    if not dest_cal_id:
        print_error("Calendar 'test-5' not found in destination account")
        sys.exit(1)

    return source_cal_id, dest_cal_id

def create_source_event(headers, source_cal_id):
    """Create a source event with full details for privacy testing."""
    print_step(1, "Creating source event with full details")

    start_time = datetime.now(timezone.utc) + timedelta(days=2)
    end_time = start_time + timedelta(hours=1)

    event_data = {
        "calendar_id": source_cal_id,
        "summary": "Confidential Client Meeting",
        "description": "Discuss Q4 sales projections with ACME Corp. Bring latest financial reports.",
        "location": "Conference Room B, 5th Floor, Main Office",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC"
        },
        "attendees": ["colleague@example.com", "manager@example.com"]
    }

    response = requests.post(
        f"{BASE_URL}/calendars/source/events/create",
        json=event_data,
        headers=headers
    )

    if response.status_code != 200:
        print_error(f"Failed to create source event: {response.text}")
        sys.exit(1)

    event = response.json()
    print_success(f"Created source event: {event['id']}")
    print(f"  Title: {event_data['summary']}")
    print(f"  Description: {event_data['description']}")
    print(f"  Location: {event_data['location']}")
    print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  End: {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    return event['id'], start_time, end_time

def create_sync_config_with_privacy(headers, source_cal_id, dest_cal_id):
    """Create one-way sync configuration with privacy mode enabled."""
    print_step(2, "Creating one-way sync with privacy mode enabled")

    config_data = {
        "source_calendar_id": source_cal_id,
        "dest_calendar_id": dest_cal_id,
        "sync_lookahead_days": 90,
        "enable_bidirectional": False,
        "privacy_mode_enabled": True,
        "privacy_placeholder_text": "Busy - Personal appointment"
    }

    response = requests.post(
        f"{BASE_URL}/sync/config",
        json=config_data,
        headers=headers
    )

    if response.status_code != 201:
        print_error(f"Failed to create sync config: {response.text}")
        sys.exit(1)

    config = response.json()
    print_success(f"Created sync config: {config['id']}")
    print(f"  Privacy mode: {config['privacy_mode_enabled']}")
    print(f"  Placeholder text: {config['privacy_placeholder_text']}")
    print(f"  Direction: {config['sync_direction']}")

    return config['id']

def trigger_sync(config_id, headers):
    """Trigger manual sync."""
    print_step(3, "Triggering sync")

    response = requests.post(
        f"{BASE_URL}/sync/trigger/{config_id}",
        headers=headers
    )

    if response.status_code != 200:
        print_error(f"Failed to trigger sync: {response.text}")
        sys.exit(1)

    result = response.json()
    print_success(f"Sync triggered: {result['sync_log_id']}")

    # Wait for sync to complete
    print("  Waiting for sync to complete...")
    time.sleep(3)

    return result['sync_log_id']

def verify_privacy_applied(headers, dest_cal_id, source_event_id, expected_start, expected_end):
    """Verify that privacy mode was applied to destination event."""
    print_step(4, "Verifying privacy mode was applied")

    # List events in destination calendar
    list_data = {
        "calendar_id": dest_cal_id,
        "time_min": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "time_max": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    }

    response = requests.post(
        f"{BASE_URL}/calendars/destination/events/list",
        json=list_data,
        headers=headers
    )

    if response.status_code != 200:
        print_error(f"Failed to list destination events: {response.text}")
        sys.exit(1)

    events = response.json().get('items', [])

    # Find synced event by source_id in extended properties
    synced_event = None
    for event in events:
        shared_props = event.get('extendedProperties', {}).get('shared', {})
        if shared_props.get('source_id') == source_event_id:
            synced_event = event
            break

    if not synced_event:
        print_error(f"Synced event not found in destination calendar")
        sys.exit(1)

    print_success("Found synced event in destination calendar")
    print(f"  Event ID: {synced_event['id']}")

    # Verify privacy was applied
    errors = []

    # Check title is placeholder
    if synced_event['summary'] != "Busy - Personal appointment":
        errors.append(f"Title should be placeholder, got: {synced_event['summary']}")
    else:
        print_success(f"Title correctly replaced with placeholder: '{synced_event['summary']}'")

    # Check description is empty
    description = synced_event.get('description', '')
    if description:
        errors.append(f"Description should be empty, got: {description}")
    else:
        print_success("Description correctly removed")

    # Check location is empty
    location = synced_event.get('location', '')
    if location:
        errors.append(f"Location should be empty, got: {location}")
    else:
        print_success("Location correctly removed")

    # Check attendees are removed
    attendees = synced_event.get('attendees', [])
    if attendees:
        errors.append(f"Attendees should be removed, got: {attendees}")
    else:
        print_success("Attendees correctly removed")

    # Verify times are preserved
    event_start = datetime.fromisoformat(synced_event['start']['dateTime'].replace('Z', '+00:00'))
    event_end = datetime.fromisoformat(synced_event['end']['dateTime'].replace('Z', '+00:00'))

    # Allow 1 second tolerance for time comparison
    if abs((event_start - expected_start).total_seconds()) > 1:
        errors.append(f"Start time mismatch: expected {expected_start}, got {event_start}")
    else:
        print_success(f"Start time preserved: {event_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    if abs((event_end - expected_end).total_seconds()) > 1:
        errors.append(f"End time mismatch: expected {expected_end}, got {event_end}")
    else:
        print_success(f"End time preserved: {event_end.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Check privacy_mode flag in extended properties
    privacy_flag = shared_props.get('privacy_mode')
    if privacy_flag != 'true':
        errors.append(f"privacy_mode flag should be 'true', got: {privacy_flag}")
    else:
        print_success("Privacy mode flag correctly set in extended properties")

    if errors:
        print_error("Privacy verification failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print_success("All privacy checks passed!")
    return synced_event['id']

def update_source_event(event_id, source_cal_id, headers):
    """Update source event with new details."""
    print_step(5, "Updating source event with new details")

    update_data = {
        "calendar_id": source_cal_id,
        "event_id": event_id,
        "summary": "Updated: Super Confidential Strategy Meeting",
        "description": "New description with secret information that should be hidden.",
        "location": "Executive Suite, Top Floor"
    }

    response = requests.post(
        f"{BASE_URL}/calendars/source/events/update",
        json=update_data,
        headers=headers
    )

    if response.status_code != 200:
        print_error(f"Failed to update source event: {response.text}")
        sys.exit(1)

    print_success("Updated source event with new details")
    print(f"  New title: {update_data['summary']}")
    print(f"  New description: {update_data['description']}")
    print(f"  New location: {update_data['location']}")

def verify_privacy_maintained_after_update(headers, dest_cal_id, source_event_id, dest_event_id):
    """Verify privacy is maintained after source event update."""
    print_step(7, "Verifying privacy maintained after update")

    # List destination events
    list_data = {
        "calendar_id": dest_cal_id,
        "time_min": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "time_max": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    }

    response = requests.post(
        f"{BASE_URL}/calendars/destination/events/list",
        json=list_data,
        headers=headers
    )

    if response.status_code != 200:
        print_error(f"Failed to list destination events: {response.text}")
        sys.exit(1)

    events = response.json().get('items', [])

    # Find synced event
    synced_event = None
    for event in events:
        if event['id'] == dest_event_id:
            synced_event = event
            break

    if not synced_event:
        print_error("Updated event not found in destination")
        sys.exit(1)

    # Verify privacy still applied
    errors = []

    if synced_event['summary'] != "Busy - Personal appointment":
        errors.append(f"Title should still be placeholder, got: {synced_event['summary']}")
    else:
        print_success("Title still shows placeholder after update")

    if synced_event.get('description', ''):
        errors.append(f"Description should be empty, got: {synced_event.get('description')}")
    else:
        print_success("Description still removed after update")

    if synced_event.get('location', ''):
        errors.append(f"Location should be empty, got: {synced_event.get('location')}")
    else:
        print_success("Location still removed after update")

    if errors:
        print_error("Privacy not maintained after update:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print_success("Privacy correctly maintained after source event update!")

def cleanup(source_event_id, source_cal_id, config_id, headers):
    """Clean up all created resources."""
    print_step(8, "Cleaning up test resources")

    # Delete source event
    try:
        delete_data = {
            "calendar_id": source_cal_id,
            "event_id": source_event_id
        }
        response = requests.post(
            f"{BASE_URL}/calendars/source/events/delete",
            json=delete_data,
            headers=headers
        )
        if response.status_code == 200:
            print_success(f"Deleted source event: {source_event_id}")
        else:
            print_error(f"Failed to delete source event: {response.text}")
    except Exception as e:
        print_error(f"Error deleting source event: {e}")

    # Delete sync config (will cascade delete destination event via sync)
    try:
        response = requests.delete(
            f"{BASE_URL}/sync/config/{config_id}",
            headers=headers
        )
        if response.status_code == 204:
            print_success(f"Deleted sync config: {config_id}")
        else:
            print_error(f"Failed to delete sync config: {response.text}")
    except Exception as e:
        print_error(f"Error deleting sync config: {e}")

    print_success("Cleanup complete!")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 e2e_test_privacy_one_way.py <ACCESS_TOKEN>")
        sys.exit(1)

    access_token = sys.argv[1]
    headers = {"Authorization": f"Bearer {access_token}"}

    print("\n" + "="*80)
    print("E2E TEST: One-Way Sync with Privacy Mode")
    print("="*80)
    print("\nThis test validates that privacy mode correctly hides event details")
    print("while preserving time slots in one-way synchronization.")

    try:
        # Test flow
        source_cal_id, dest_cal_id = find_calendars(headers)
        source_event_id, start_time, end_time = create_source_event(headers, source_cal_id)
        config_id = create_sync_config_with_privacy(headers, source_cal_id, dest_cal_id)
        sync_log_id = trigger_sync(config_id, headers)
        dest_event_id = verify_privacy_applied(headers, dest_cal_id, source_event_id, start_time, end_time)
        update_source_event(source_event_id, source_cal_id, headers)
        trigger_sync(config_id, headers)  # Step 6: Resync after update
        verify_privacy_maintained_after_update(headers, dest_cal_id, source_event_id, dest_event_id)
        cleanup(source_event_id, source_cal_id, config_id, headers)

        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED!")
        print("="*80)
        print("\nSummary:")
        print("  ✓ Source event created with full details")
        print("  ✓ Privacy mode correctly hides title, description, location, attendees")
        print("  ✓ Time slots preserved exactly")
        print("  ✓ Privacy maintained after source event updates")
        print("  ✓ All resources cleaned up")
        print("\nOne-way privacy mode is working correctly!")

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
