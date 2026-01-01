#!/usr/bin/env python3
"""
End-to-end sync test with real Google Calendar account.

Tests:
- Account: koch.chris@gmail.com
- Calendars: test-4 (source) → test-5 (destination)
- Operations: Create, Move, Rename, Delete

Usage:
    python3 e2e_sync_test.py [ACCESS_TOKEN]

    If no token provided, will prompt interactively.
"""
import requests
import time
import json
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3033"

# Test configuration
SOURCE_CALENDAR_NAME = "test-4"
DEST_CALENDAR_NAME = "test-5"
TEST_EVENT_SUMMARY = f"[E2E Test] Test Event {datetime.now().strftime('%Y%m%d_%H%M%S')}"
TEST_DATE = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)


class Colors:
    """Terminal colors for output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(msg: str):
    """Print section header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(msg: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")


def print_error(msg: str):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")


def print_info(msg: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")


def print_warning(msg: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")


class E2ESyncTest:
    """End-to-end sync test runner."""

    def __init__(self):
        self.token: Optional[str] = None
        self.source_calendar_id: Optional[str] = None
        self.dest_calendar_id: Optional[str] = None
        self.sync_config_id: Optional[str] = None
        self.test_event_id: Optional[str] = None
        self.synced_event_id: Optional[str] = None

    def get_auth_token(self, token_arg: Optional[str] = None) -> bool:
        """Get authentication token from user."""
        print_header("Step 1: Authentication")

        if token_arg:
            self.token = token_arg
            print_info("Using token from command line argument")
        else:
            print_info("Please authenticate via the web interface:")
            print_info(f"1. Open: {FRONTEND_URL}")
            print_info("2. Sign in with koch.chris@gmail.com")
            print_info("3. Open browser DevTools (F12)")
            print_info("4. Go to Console tab")
            print_info("5. Run: localStorage.getItem('access_token')")
            print_info("6. Copy the token (without quotes)")
            print()

            self.token = input("Enter access token: ").strip()

        if not self.token:
            print_error("No token provided")
            return False

        # Verify token works
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{API_BASE_URL}/auth/me", headers=headers)

        if response.status_code == 200:
            user_data = response.json()
            print_success(f"Authenticated as: {user_data['email']}")
            return True
        else:
            print_error(f"Authentication failed: {response.status_code}")
            return False

    def check_oauth_status(self) -> bool:
        """Check OAuth connection status."""
        print_header("Step 2: Verify OAuth Connections")
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{API_BASE_URL}/oauth/status", headers=headers)

        if response.status_code != 200:
            print_error(f"Failed to check OAuth status: {response.status_code}")
            return False

        data = response.json()

        print_info(f"Source connected: {data['source_connected']}")
        if data['source_connected']:
            print_info(f"  Email: {data.get('source_email', 'N/A')}")

        print_info(f"Destination connected: {data['destination_connected']}")
        if data['destination_connected']:
            print_info(f"  Email: {data.get('destination_email', 'N/A')}")

        if not (data['source_connected'] and data['destination_connected']):
            print_error("Both source and destination accounts must be connected")
            print_info("Please connect accounts via the web interface")
            return False

        print_success("OAuth connections verified")
        return True

    def find_calendars(self) -> bool:
        """Find test-4 and test-5 calendars."""
        print_header("Step 3: Find Calendars")
        headers = {"Authorization": f"Bearer {self.token}"}

        # Get source calendars
        response = requests.get(f"{API_BASE_URL}/calendars/source/list", headers=headers)
        if response.status_code != 200:
            print_error(f"Failed to list source calendars: {response.status_code}")
            return False

        source_cals = response.json()['calendars']
        print_info(f"Found {len(source_cals)} source calendars")

        # Find test-4
        for cal in source_cals:
            if cal['summary'] == SOURCE_CALENDAR_NAME:
                self.source_calendar_id = cal['id']
                print_success(f"Found source calendar: {SOURCE_CALENDAR_NAME} ({cal['id']})")
                break

        if not self.source_calendar_id:
            print_error(f"Calendar '{SOURCE_CALENDAR_NAME}' not found in source account")
            print_info("Available calendars:")
            for cal in source_cals:
                print_info(f"  - {cal['summary']}")
            return False

        # Get destination calendars
        response = requests.get(f"{API_BASE_URL}/calendars/destination/list", headers=headers)
        if response.status_code != 200:
            print_error(f"Failed to list destination calendars: {response.status_code}")
            return False

        dest_cals = response.json()['calendars']
        print_info(f"Found {len(dest_cals)} destination calendars")

        # Find test-5
        for cal in dest_cals:
            if cal['summary'] == DEST_CALENDAR_NAME:
                self.dest_calendar_id = cal['id']
                print_success(f"Found destination calendar: {DEST_CALENDAR_NAME} ({cal['id']})")
                break

        if not self.dest_calendar_id:
            print_error(f"Calendar '{DEST_CALENDAR_NAME}' not found in destination account")
            print_info("Available calendars:")
            for cal in dest_cals:
                print_info(f"  - {cal['summary']}")
            return False

        return True

    def create_sync_config(self) -> bool:
        """Create one-way sync configuration."""
        print_header("Step 4: Create Sync Configuration")
        headers = {"Authorization": f"Bearer {self.token}"}

        payload = {
            "source_calendar_id": self.source_calendar_id,
            "dest_calendar_id": self.dest_calendar_id,
            "sync_lookahead_days": 90,
            "enable_bidirectional": False,
            "privacy_mode_enabled": False,
        }

        print_info(f"Creating sync: {SOURCE_CALENDAR_NAME} → {DEST_CALENDAR_NAME}")
        response = requests.post(f"{API_BASE_URL}/sync/config", json=payload, headers=headers)

        if response.status_code != 201:
            print_error(f"Failed to create sync config: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()
        self.sync_config_id = data['id']
        print_success(f"Sync config created: {self.sync_config_id}")
        print_info(f"Direction: {data['sync_direction']}")
        print_info(f"Active: {data['is_active']}")
        return True

    def create_test_event(self) -> bool:
        """Create test event in source calendar using Google Calendar API."""
        print_header("Step 5: Create Test Event")

        # We need to call Google Calendar API directly
        # For simplicity, instruct user to create event manually
        print_warning("Manual step required:")
        print_info(f"Please create an event in calendar '{SOURCE_CALENDAR_NAME}':")
        print_info(f"  Title: {TEST_EVENT_SUMMARY}")
        print_info(f"  Date: {TEST_DATE.strftime('%Y-%m-%d')}")
        print_info(f"  Time: {TEST_DATE.strftime('%H:%M')}")
        print()

        input("Press Enter after creating the event...")

        print_success("Event creation confirmed by user")
        return True

    def trigger_sync(self) -> Dict[str, Any]:
        """Trigger sync and return results."""
        headers = {"Authorization": f"Bearer {self.token}"}

        print_info("Triggering sync...")
        response = requests.post(
            f"{API_BASE_URL}/sync/trigger/{self.sync_config_id}",
            headers=headers
        )

        if response.status_code != 200:
            print_error(f"Failed to trigger sync: {response.status_code}")
            print_error(f"Response: {response.text}")
            return {}

        data = response.json()
        sync_log_id = data.get('sync_log_id')
        print_info(f"Sync triggered: {sync_log_id}")

        # Wait for sync to complete
        print_info("Waiting for sync to complete...")
        time.sleep(5)

        # Get sync results
        response = requests.get(
            f"{API_BASE_URL}/sync/logs/{self.sync_config_id}",
            headers=headers
        )

        if response.status_code == 200:
            logs = response.json()
            if logs:
                latest_log = logs[0]
                return latest_log

        return {}

    def test_event_creation(self) -> bool:
        """Test 1: Event creation sync."""
        print_header("Test 1: Event Creation")

        log = self.trigger_sync()

        if not log:
            print_error("Failed to get sync log")
            return False

        print_success("Sync completed!")
        print_info(f"Status: {log['status']}")
        print_info(f"Events created: {log['events_created']}")
        print_info(f"Events updated: {log['events_updated']}")
        print_info(f"Events deleted: {log['events_deleted']}")

        if log['events_created'] > 0:
            print_success(f"✓ Event successfully synced to {DEST_CALENDAR_NAME}")
            return True
        else:
            print_warning("No events were created. Event may already exist or sync window issue.")
            return False

    def test_event_rename(self) -> bool:
        """Test 2: Event rename sync."""
        print_header("Test 2: Event Rename")

        new_title = f"{TEST_EVENT_SUMMARY} [RENAMED]"
        print_warning("Manual step required:")
        print_info(f"Please rename the event in '{SOURCE_CALENDAR_NAME}':")
        print_info(f"  New title: {new_title}")
        print()

        input("Press Enter after renaming the event...")

        log = self.trigger_sync()

        if not log:
            print_error("Failed to get sync log")
            return False

        print_success("Sync completed!")
        print_info(f"Status: {log['status']}")
        print_info(f"Events updated: {log['events_updated']}")

        if log['events_updated'] > 0:
            print_success(f"✓ Event rename synced to {DEST_CALENDAR_NAME}")
            return True
        else:
            print_warning("No events were updated")
            return False

    def test_event_move(self) -> bool:
        """Test 3: Event time change sync."""
        print_header("Test 3: Event Time Change")

        new_time = TEST_DATE + timedelta(hours=2)
        print_warning("Manual step required:")
        print_info(f"Please change the event time in '{SOURCE_CALENDAR_NAME}':")
        print_info(f"  New time: {new_time.strftime('%H:%M')}")
        print()

        input("Press Enter after changing the time...")

        log = self.trigger_sync()

        if not log:
            print_error("Failed to get sync log")
            return False

        print_success("Sync completed!")
        print_info(f"Status: {log['status']}")
        print_info(f"Events updated: {log['events_updated']}")

        if log['events_updated'] > 0:
            print_success(f"✓ Event time change synced to {DEST_CALENDAR_NAME}")
            return True
        else:
            print_warning("No events were updated")
            return False

    def test_event_deletion(self) -> bool:
        """Test 4: Event deletion sync."""
        print_header("Test 4: Event Deletion")

        print_warning("Manual step required:")
        print_info(f"Please DELETE the event from '{SOURCE_CALENDAR_NAME}'")
        print()

        input("Press Enter after deleting the event...")

        log = self.trigger_sync()

        if not log:
            print_error("Failed to get sync log")
            return False

        print_success("Sync completed!")
        print_info(f"Status: {log['status']}")
        print_info(f"Events deleted: {log['events_deleted']}")

        if log['events_deleted'] > 0:
            print_success(f"✓ Event deletion synced to {DEST_CALENDAR_NAME}")
            return True
        else:
            print_warning("No events were deleted")
            return False

    def cleanup(self) -> bool:
        """Clean up: Delete sync configuration."""
        print_header("Cleanup: Delete Sync Configuration")
        headers = {"Authorization": f"Bearer {self.token}"}

        response = requests.delete(
            f"{API_BASE_URL}/sync/config/{self.sync_config_id}",
            headers=headers
        )

        if response.status_code == 204:
            print_success("Sync configuration deleted")
            return True
        else:
            print_error(f"Failed to delete sync config: {response.status_code}")
            return False

    def run(self, token_arg: Optional[str] = None):
        """Run all tests."""
        print_header("E2E Sync Test Suite")
        print_info(f"Source Calendar: {SOURCE_CALENDAR_NAME}")
        print_info(f"Destination Calendar: {DEST_CALENDAR_NAME}")
        print_info(f"Test Date: {TEST_DATE.strftime('%Y-%m-%d %H:%M')}")

        results = []

        # Setup
        if not self.get_auth_token(token_arg):
            return

        if not self.check_oauth_status():
            return

        if not self.find_calendars():
            return

        if not self.create_sync_config():
            return

        if not self.create_test_event():
            return

        # Run tests
        results.append(("Event Creation", self.test_event_creation()))
        results.append(("Event Rename", self.test_event_rename()))
        results.append(("Event Time Change", self.test_event_move()))
        results.append(("Event Deletion", self.test_event_deletion()))

        # Cleanup
        self.cleanup()

        # Print summary
        print_header("Test Results Summary")

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            if result:
                print_success(f"{test_name}: PASSED")
            else:
                print_error(f"{test_name}: FAILED")

        print()
        print_info(f"Total: {passed}/{total} tests passed")

        if passed == total:
            print_success("All tests passed! ✓")
        else:
            print_warning(f"{total - passed} test(s) failed")


if __name__ == "__main__":
    token = sys.argv[1] if len(sys.argv) > 1 else None
    test = E2ESyncTest()
    test.run(token)
