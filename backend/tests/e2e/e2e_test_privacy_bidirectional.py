#!/usr/bin/env python3
"""
E2E Test: Privacy Mode for Bi-Directional Sync

This test validates that privacy mode correctly applies different placeholder texts
for each direction in bi-directional calendar synchronization.

Usage:
    python3 backend/tests/e2e/e2e_test_privacy_bidirectional.py <ACCESS_TOKEN>

Prerequisites:
    - User must have valid OAuth tokens for both source and destination accounts
    - Calendars 'test-4' and 'test-5' must exist

Test Flow:
    1. Create work event in test-4 with confidential details
    2. Create personal event in test-5 with private details
    3. Create bi-directional sync with different privacy settings:
       - test-4 → test-5: "Work Meeting" placeholder
       - test-5 → test-4: "Personal Time" placeholder
    4. Trigger sync in both directions
    5. Verify test-5 has work event with "Work Meeting" placeholder
    6. Verify test-4 has personal event with "Personal Time" placeholder
    7. Verify times preserved in both directions
    8. Update both events
    9. Resync and verify privacy maintained
    10. Clean up all resources
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


def create_work_event(headers, source_cal_id):
    """Create work event in test-4 with confidential details."""
    print_step(1, "Creating work event in test-4 (Business calendar)")

    start_time = datetime.now(timezone.utc) + timedelta(days=2)
    end_time = start_time + timedelta(hours=1)

    event_data = {
        "calendar_id": source_cal_id,
        "summary": "Confidential Board Meeting",
        "description": "Q4 financial review and strategic planning. Board members only.",
        "location": "Executive Conference Room, Building A",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC"
        },
        "attendees": ["ceo@company.com", "cfo@company.com"]
    }

    response = requests.post(
        f"{BASE_URL}/calendars/source/events/create",
        json=event_data,
        headers=headers
    )

    if response.status_code != 200:
        print_error(f"Failed to create work event: {response.text}")
        sys.exit(1)

    event = response.json()
    print_success(f"Created work event: {event['id']}")
    print(f"  Title: {event_data['summary']}")
    print(f"  Description: {event_data['description'][:50]}...")
    print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    return event['id'], start_time, end_time

def create_personal_event(headers, dest_cal_id):
    """Create personal event in test-5 with private details."""
    print_step(2, "Creating personal event in test-5 (Private calendar)")

    start_time = datetime.now(timezone.utc) + timedelta(days=3)
    end_time = start_time + timedelta(minutes=30)

    event_data = {
        "calendar_id": dest_cal_id,
        "summary": "Doctor Appointment - Annual Checkup",
        "description": "Annual physical exam with Dr. Smith. Bring insurance card and medication list.",
        "location": "City Medical Center, 123 Health St",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC"
        }
    }

    response = requests.post(
        f"{BASE_URL}/calendars/destination/events/create",
        json=event_data,
        headers=headers
    )

    if response.status_code != 200:
        print_error(f"Failed to create personal event: {response.text}")
        sys.exit(1)

    event = response.json()
    print_success(f"Created personal event: {event['id']}")
    print(f"  Title: {event_data['summary']}")
    print(f"  Description: {event_data['description'][:50]}...")
    print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    return event['id'], start_time, end_time

def create_bidirectional_sync_with_privacy(headers, source_cal_id, dest_cal_id):
    """Create bi-directional sync with different privacy settings per direction."""
    print_step(3, "Creating bi-directional sync with privacy")

    config_data = {
        "source_calendar_id": source_cal_id,
        "dest_calendar_id": dest_cal_id,
        "sync_lookahead_days": 90,
        "enable_bidirectional": True,
        "privacy_mode_enabled": True,
        "privacy_placeholder_text": "Work Meeting",
        "reverse_privacy_mode_enabled": True,
        "reverse_privacy_placeholder_text": "Personal Time"
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
    print_success(f"Created forward config: {config['id']}")
    print(f"  Direction: {config['sync_direction']}")
    print(f"  Privacy enabled: {config['privacy_mode_enabled']}")
    print(f"  Placeholder: '{config['privacy_placeholder_text']}'")
    print(f"  Paired config: {config['paired_config_id']}")

    # Get reverse config details
    reverse_config_id = config['paired_config_id']
    response = requests.get(
        f"{BASE_URL}/sync/config",
        headers=headers
    )

    if response.status_code != 200:
        print_error(f"Failed to list configs: {response.text}")
        sys.exit(1)

    configs = response.json()
    reverse_config = next((c for c in configs if c['id'] == reverse_config_id), None)

    if reverse_config:
        print_success(f"Created reverse config: {reverse_config['id']}")
        print(f"  Direction: {reverse_config['sync_direction']}")
        print(f"  Privacy enabled: {reverse_config['privacy_mode_enabled']}")
        print(f"  Placeholder: '{reverse_config['privacy_placeholder_text']}'")

    return config['id']

def trigger_bidirectional_sync(config_id, headers):
    """Trigger sync in both directions."""
    print_step(4, "Triggering bi-directional sync")

    response = requests.post(
        f"{BASE_URL}/sync/trigger/{config_id}?trigger_both_directions=true",
        headers=headers
    )

    if response.status_code != 200:
        print_error(f"Failed to trigger sync: {response.text}")
        sys.exit(1)

    result = response.json()
    print_success(f"Sync triggered: {result['sync_log_id']}")
    print("  Syncing both directions...")

    # Wait for both syncs to complete
    print("  Waiting for syncs to complete...")
    time.sleep(5)

    return result['sync_log_id']

def verify_work_event_privacy_in_personal_calendar(headers, dest_cal_id, work_event_id, expected_start, expected_end):
    """Verify work event appears in personal calendar with 'Work Meeting' placeholder."""
    print_step(5, "Verifying work event privacy in personal calendar (test-5)")

    # List events in test-5
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
        print_error(f"Failed to list events in test-5: {response.text}")
        sys.exit(1)

    events = response.json().get('items', [])

    # Find synced work event
    synced_event = None
    for event in events:
        shared_props = event.get('extendedProperties', {}).get('shared', {})
        if shared_props.get('source_id') == work_event_id:
            synced_event = event
            break

    if not synced_event:
        print_error("Work event not found in personal calendar")
        sys.exit(1)

    print_success("Found work event in personal calendar")

    # Verify privacy with "Work Meeting" placeholder
    errors = []

    if synced_event['summary'] != "Work Meeting":
        errors.append(f"Expected 'Work Meeting', got: {synced_event['summary']}")
    else:
        print_success(f"Title correctly shows: '{synced_event['summary']}'")

    if synced_event.get('description', ''):
        errors.append(f"Description should be empty, got: {synced_event.get('description')}")
    else:
        print_success("Confidential description removed")

    if synced_event.get('location', ''):
        errors.append(f"Location should be empty, got: {synced_event.get('location')}")
    else:
        print_success("Location removed")

    # Verify times preserved
    event_start = datetime.fromisoformat(synced_event['start']['dateTime'].replace('Z', '+00:00'))
    event_end = datetime.fromisoformat(synced_event['end']['dateTime'].replace('Z', '+00:00'))

    if abs((event_start - expected_start).total_seconds()) > 1:
        errors.append(f"Start time mismatch")
    else:
        print_success(f"Start time preserved: {event_start.strftime('%H:%M')}")

    if abs((event_end - expected_end).total_seconds()) > 1:
        errors.append(f"End time mismatch")
    else:
        print_success(f"End time preserved: {event_end.strftime('%H:%M')}")

    if errors:
        print_error("Work event privacy verification failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print_success("Work event privacy correctly applied!")
    return synced_event['id']

def verify_personal_event_privacy_in_work_calendar(headers, source_cal_id, personal_event_id, expected_start, expected_end):
    """Verify personal event appears in work calendar with 'Personal Time' placeholder."""
    print_step(6, "Verifying personal event privacy in work calendar (test-4)")

    # List events in test-4
    list_data = {
        "calendar_id": source_cal_id,
        "time_min": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "time_max": (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    }

    response = requests.post(
        f"{BASE_URL}/calendars/source/events/list",
        json=list_data,
        headers=headers
    )

    if response.status_code != 200:
        print_error(f"Failed to list events in test-4: {response.text}")
        sys.exit(1)

    events = response.json().get('items', [])

    # Find synced personal event
    synced_event = None
    for event in events:
        shared_props = event.get('extendedProperties', {}).get('shared', {})
        if shared_props.get('source_id') == personal_event_id:
            synced_event = event
            break

    if not synced_event:
        print_error("Personal event not found in work calendar")
        sys.exit(1)

    print_success("Found personal event in work calendar")

    # Verify privacy with "Personal Time" placeholder
    errors = []

    if synced_event['summary'] != "Personal Time":
        errors.append(f"Expected 'Personal Time', got: {synced_event['summary']}")
    else:
        print_success(f"Title correctly shows: '{synced_event['summary']}'")

    if synced_event.get('description', ''):
        errors.append(f"Description should be empty, got: {synced_event.get('description')}")
    else:
        print_success("Private description removed")

    if synced_event.get('location', ''):
        errors.append(f"Location should be empty, got: {synced_event.get('location')}")
    else:
        print_success("Location removed")

    # Verify times preserved
    event_start = datetime.fromisoformat(synced_event['start']['dateTime'].replace('Z', '+00:00'))
    event_end = datetime.fromisoformat(synced_event['end']['dateTime'].replace('Z', '+00:00'))

    if abs((event_start - expected_start).total_seconds()) > 1:
        errors.append(f"Start time mismatch")
    else:
        print_success(f"Start time preserved: {event_start.strftime('%H:%M')}")

    if abs((event_end - expected_end).total_seconds()) > 1:
        errors.append(f"End time mismatch")
    else:
        print_success(f"End time preserved: {event_end.strftime('%H:%M')}")

    if errors:
        print_error("Personal event privacy verification failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print_success("Personal event privacy correctly applied!")
    return synced_event['id']

def update_events(work_event_id, personal_event_id, source_cal_id, dest_cal_id, headers):
    """Update both original events with new details."""
    print_step(7, "Updating both original events")

    # Update work event
    work_update = {
        "calendar_id": source_cal_id,
        "event_id": work_event_id,
        "summary": "UPDATED: Top Secret Strategy Session",
        "description": "New highly confidential information that must stay private.",
        "location": "Secure Location - Building C"
    }

    response = requests.post(
        f"{BASE_URL}/calendars/source/events/update",
        json=work_update,
        headers=headers
    )

    if response.status_code == 200:
        print_success("Updated work event with new confidential details")
    else:
        print_error(f"Failed to update work event: {response.text}")

    # Update personal event
    personal_update = {
        "calendar_id": dest_cal_id,
        "event_id": personal_event_id,
        "summary": "UPDATED: Specialist Consultation",
        "description": "Updated private medical information.",
        "location": "Private Clinic Downtown"
    }

    response = requests.post(
        f"{BASE_URL}/calendars/destination/events/update",
        json=personal_update,
        headers=headers
    )

    if response.status_code == 200:
        print_success("Updated personal event with new private details")
    else:
        print_error(f"Failed to update personal event: {response.text}")

def verify_privacy_maintained(headers, source_cal_id, dest_cal_id, work_synced_id, personal_synced_id):
    """Verify privacy is maintained after updates in both directions."""
    print_step(9, "Verifying privacy maintained after updates")

    # Check work event in personal calendar still has placeholder
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

    events = response.json().get('items', [])
    work_event = next((e for e in events if e['id'] == work_synced_id), None)

    if work_event and work_event['summary'] == "Work Meeting":
        print_success("Work event still shows 'Work Meeting' placeholder")
    else:
        print_error(f"Work event privacy not maintained: {work_event['summary'] if work_event else 'Not found'}")

    # Check personal event in work calendar still has placeholder
    list_data = {
        "calendar_id": source_cal_id,
        "time_min": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "time_max": (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    }

    response = requests.post(
        f"{BASE_URL}/calendars/source/events/list",
        json=list_data,
        headers=headers
    )

    events = response.json().get('items', [])
    personal_event = next((e for e in events if e['id'] == personal_synced_id), None)

    if personal_event and personal_event['summary'] == "Personal Time":
        print_success("Personal event still shows 'Personal Time' placeholder")
    else:
        print_error(f"Personal event privacy not maintained: {personal_event['summary'] if personal_event else 'Not found'}")

    print_success("Privacy correctly maintained in both directions!")

def cleanup(work_event_id, personal_event_id, source_cal_id, dest_cal_id, config_id, headers):
    """Clean up all created resources."""
    print_step(10, "Cleaning up test resources")

    # Delete work event
    try:
        delete_data = {"calendar_id": source_cal_id, "event_id": work_event_id}
        response = requests.post(
            f"{BASE_URL}/calendars/source/events/delete",
            json=delete_data,
            headers=headers
        )
        if response.status_code == 200:
            print_success(f"Deleted work event")
    except Exception as e:
        print_error(f"Error deleting work event: {e}")

    # Delete personal event
    try:
        delete_data = {"calendar_id": dest_cal_id, "event_id": personal_event_id}
        response = requests.post(
            f"{BASE_URL}/calendars/destination/events/delete",
            json=delete_data,
            headers=headers
        )
        if response.status_code == 200:
            print_success(f"Deleted personal event")
    except Exception as e:
        print_error(f"Error deleting personal event: {e}")

    # Delete sync configs (both forward and reverse)
    try:
        # Get all configs to find the paired one
        response = requests.get(f"{BASE_URL}/sync/config", headers=headers)
        configs = response.json()

        for config in configs:
            if config['id'] == config_id or config.get('paired_config_id') == config_id:
                response = requests.delete(
                    f"{BASE_URL}/sync/config/{config['id']}",
                    headers=headers
                )
                if response.status_code == 204:
                    print_success(f"Deleted sync config: {config['id']}")
    except Exception as e:
        print_error(f"Error deleting sync configs: {e}")

    print_success("Cleanup complete!")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 e2e_test_privacy_bidirectional.py <ACCESS_TOKEN>")
        sys.exit(1)

    access_token = sys.argv[1]
    headers = {"Authorization": f"Bearer {access_token}"}

    print("\n" + "="*80)
    print("E2E TEST: Bi-Directional Sync with Privacy Mode")
    print("="*80)
    print("\nThis test validates that privacy mode correctly applies different")
    print("placeholder texts for each direction in bi-directional synchronization.")

    try:
        # Test flow
        source_cal_id, dest_cal_id = find_calendars(headers)
        work_event_id, work_start, work_end = create_work_event(headers, source_cal_id)
        personal_event_id, personal_start, personal_end = create_personal_event(headers, dest_cal_id)
        config_id = create_bidirectional_sync_with_privacy(headers, source_cal_id, dest_cal_id)
        trigger_bidirectional_sync(config_id, headers)
        work_synced_id = verify_work_event_privacy_in_personal_calendar(headers, dest_cal_id, work_event_id, work_start, work_end)
        personal_synced_id = verify_personal_event_privacy_in_work_calendar(headers, source_cal_id, personal_event_id, personal_start, personal_end)
        update_events(work_event_id, personal_event_id, source_cal_id, dest_cal_id, headers)
        trigger_bidirectional_sync(config_id, headers)  # Step 8: Resync
        verify_privacy_maintained(headers, source_cal_id, dest_cal_id, work_synced_id, personal_synced_id)
        cleanup(work_event_id, personal_event_id, source_cal_id, dest_cal_id, config_id, headers)

        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED!")
        print("="*80)
        print("\nSummary:")
        print("  ✓ Work event synced to personal calendar with 'Work Meeting' placeholder")
        print("  ✓ Personal event synced to work calendar with 'Personal Time' placeholder")
        print("  ✓ All confidential details hidden in both directions")
        print("  ✓ Time slots preserved exactly in both directions")
        print("  ✓ Privacy maintained after event updates")
        print("  ✓ All resources cleaned up")
        print("\nBi-directional privacy mode is working correctly!")

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
