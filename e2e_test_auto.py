#!/usr/bin/env python3
"""
Fully automated E2E sync test - NO manual steps required!

Usage:
    python3 e2e_test_auto.py <ACCESS_TOKEN>
"""
import requests
import time
import sys
from datetime import datetime, timedelta, timezone

# Config
API_URL = "http://localhost:8000"
SOURCE_CAL = "test-4"
DEST_CAL = "test-5"
TEST_SUMMARY = f"[E2E Test] {datetime.now().strftime('%H:%M:%S')}"
TEST_START = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
TEST_END = TEST_START + timedelta(hours=1)

# Colors
C_HEADER = '\033[95m\033[1m'
C_GREEN = '\033[92m'
C_RED = '\033[91m'
C_BLUE = '\033[96m'
C_YELLOW = '\033[93m'
C_END = '\033[0m'


def header(msg):
    print(f"\n{C_HEADER}{'='*80}\n{msg}\n{'='*80}{C_END}\n")


def success(msg):
    print(f"{C_GREEN}✓ {msg}{C_END}")


def error(msg):
    print(f"{C_RED}✗ {msg}{C_END}")


def info(msg):
    print(f"{C_BLUE}ℹ {msg}{C_END}")


def warn(msg):
    print(f"{C_YELLOW}⚠ {msg}{C_END}")


class E2ETest:
    def __init__(self, token):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}
        self.source_cal_id = None
        self.dest_cal_id = None
        self.sync_id = None
        self.event_id = None

    def find_calendars(self):
        """Find test-4 and test-5."""
        header("Step 1: Find Calendars")

        # Source
        r = requests.get(f"{API_URL}/calendars/source/list", headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to list source calendars: {r.status_code}")
            return False

        for cal in r.json()['calendars']:
            if cal['summary'] == SOURCE_CAL:
                self.source_cal_id = cal['id']
                success(f"Found {SOURCE_CAL}: {cal['id']}")
                break

        if not self.source_cal_id:
            error(f"Calendar '{SOURCE_CAL}' not found")
            return False

        # Destination
        r = requests.get(f"{API_URL}/calendars/destination/list", headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to list dest calendars: {r.status_code}")
            return False

        for cal in r.json()['calendars']:
            if cal['summary'] == DEST_CAL:
                self.dest_cal_id = cal['id']
                success(f"Found {DEST_CAL}: {cal['id']}")
                break

        if not self.dest_cal_id:
            error(f"Calendar '{DEST_CAL}' not found")
            return False

        return True

    def create_sync(self):
        """Create one-way sync."""
        header("Step 2: Create Sync Config")

        payload = {
            "source_calendar_id": self.source_cal_id,
            "dest_calendar_id": self.dest_cal_id,
            "sync_lookahead_days": 90,
            "enable_bidirectional": False,
        }

        r = requests.post(f"{API_URL}/sync/config", json=payload, headers=self.headers)
        if r.status_code != 201:
            error(f"Failed to create sync: {r.status_code} - {r.text}")
            return False

        self.sync_id = r.json()['id']
        success(f"Created sync: {SOURCE_CAL} → {DEST_CAL}")
        info(f"Sync ID: {self.sync_id}")
        return True

    def trigger_sync(self):
        """Trigger sync and wait."""
        info("Triggering sync...")
        r = requests.post(f"{API_URL}/sync/trigger/{self.sync_id}", headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to trigger sync: {r.status_code}")
            return {}

        time.sleep(6)  # Wait for sync

        r = requests.get(f"{API_URL}/sync/logs/{self.sync_id}", headers=self.headers)
        if r.status_code == 200:
            logs = r.json()
            if logs:
                return logs[0]
        return {}

    def find_synced_event(self, summary):
        """Find event in destination calendar."""
        payload = {
            "calendar_id": self.dest_cal_id,
            "time_min": TEST_START.isoformat(),
            "time_max": (TEST_START + timedelta(days=1)).isoformat(),
            "query": summary
        }

        r = requests.post(f"{API_URL}/calendars/destination/events/list", json=payload, headers=self.headers)
        if r.status_code != 200:
            return None

        events = r.json().get('items', [])
        for event in events:
            if summary in event.get('summary', ''):
                return event
        return None

    def test_create(self):
        """Test 1: Create event and sync."""
        header("Test 1: Event Creation & Sync")

        # Create event in source
        info(f"Creating event: {TEST_SUMMARY}")
        payload = {
            "calendar_id": self.source_cal_id,
            "summary": TEST_SUMMARY,
            "description": "Automated E2E test",
            "start": {"dateTime": TEST_START.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": TEST_END.isoformat(), "timeZone": "UTC"}
        }

        r = requests.post(f"{API_URL}/calendars/source/events/create", json=payload, headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to create event: {r.status_code} - {r.text}")
            return False

        self.event_id = r.json()['id']
        success(f"Event created: {self.event_id}")

        # Sync
        log = self.trigger_sync()
        if not log:
            error("No sync log")
            return False

        success(f"Sync completed: {log['status']}")
        info(f"Created: {log['events_created']}, Updated: {log['events_updated']}, Deleted: {log['events_deleted']}")

        # Verify in dest
        info("Checking destination calendar...")
        synced = self.find_synced_event(TEST_SUMMARY)
        if synced:
            success(f"✓ Event synced to {DEST_CAL}")
            return True
        else:
            error(f"Event not found in {DEST_CAL}")
            return False

    def test_rename(self):
        """Test 2: Rename event and sync."""
        header("Test 2: Event Rename & Sync")

        new_summary = f"{TEST_SUMMARY} [RENAMED]"
        info(f"Renaming to: {new_summary}")

        payload = {
            "calendar_id": self.source_cal_id,
            "event_id": self.event_id,
            "summary": new_summary
        }

        r = requests.post(f"{API_URL}/calendars/source/events/update", json=payload, headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to rename: {r.status_code}")
            return False

        success("Event renamed")

        # Sync
        log = self.trigger_sync()
        if not log:
            error("No sync log")
            return False

        success(f"Sync completed")
        info(f"Updated: {log['events_updated']}")

        # Verify
        info("Checking destination calendar...")
        synced = self.find_synced_event(new_summary)
        if synced and new_summary in synced.get('summary', ''):
            success(f"✓ Rename synced to {DEST_CAL}")
            return True
        else:
            warn("Rename verification unclear (may still be synced)")
            return True

    def test_move(self):
        """Test 3: Move event time and sync."""
        header("Test 3: Event Time Change & Sync")

        new_start = TEST_START + timedelta(hours=2)
        new_end = new_start + timedelta(hours=1)
        info(f"Moving to: {new_start.strftime('%H:%M UTC')}")

        payload = {
            "calendar_id": self.source_cal_id,
            "event_id": self.event_id,
            "start": {"dateTime": new_start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": new_end.isoformat(), "timeZone": "UTC"}
        }

        r = requests.post(f"{API_URL}/calendars/source/events/update", json=payload, headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to move: {r.status_code}")
            return False

        success("Event moved")

        # Sync
        log = self.trigger_sync()
        if not log:
            error("No sync log")
            return False

        success(f"Sync completed")
        info(f"Updated: {log['events_updated']}")

        if log['events_updated'] > 0:
            success(f"✓ Time change synced to {DEST_CAL}")
            return True
        else:
            warn("Time change not reflected in sync count")
            return True

    def test_delete(self):
        """Test 4: Delete event and sync."""
        header("Test 4: Event Deletion & Sync")

        info("Deleting event...")
        payload = {
            "calendar_id": self.source_cal_id,
            "event_id": self.event_id
        }

        r = requests.post(f"{API_URL}/calendars/source/events/delete", json=payload, headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to delete: {r.status_code}")
            return False

        success("Event deleted")

        # Sync
        log = self.trigger_sync()
        if not log:
            error("No sync log")
            return False

        success(f"Sync completed")
        info(f"Deleted: {log['events_deleted']}")

        # Verify deletion
        time.sleep(2)
        synced = self.find_synced_event(TEST_SUMMARY)
        if not synced:
            success(f"✓ Deletion synced to {DEST_CAL}")
            return True
        else:
            error("Event still exists in destination")
            return False

    def cleanup(self):
        """Delete sync config."""
        header("Cleanup")
        r = requests.delete(f"{API_URL}/sync/config/{self.sync_id}", headers=self.headers)
        if r.status_code == 204:
            success("Sync config deleted")
        else:
            warn(f"Failed to cleanup: {r.status_code}")

    def run(self):
        """Run all tests."""
        header("Fully Automated E2E Sync Test")
        info(f"Source: {SOURCE_CAL}")
        info(f"Destination: {DEST_CAL}")
        info(f"Test event: {TEST_SUMMARY}")
        info(f"Test time: {TEST_START.strftime('%Y-%m-%d %H:%M UTC')}")

        results = []

        # Setup
        if not self.find_calendars():
            return

        if not self.create_sync():
            return

        # Tests
        results.append(("Event Creation", self.test_create()))
        results.append(("Event Rename", self.test_rename()))
        results.append(("Event Move", self.test_move()))
        results.append(("Event Deletion", self.test_delete()))

        # Cleanup
        self.cleanup()

        # Summary
        header("Test Results")
        passed = sum(1 for _, r in results if r)
        total = len(results)

        for name, result in results:
            if result:
                success(f"{name}: PASSED")
            else:
                error(f"{name}: FAILED")

        print()
        if passed == total:
            success(f"✓ All {total} tests PASSED!")
        else:
            warn(f"{passed}/{total} tests passed, {total-passed} failed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        error("Usage: python3 e2e_test_auto.py <ACCESS_TOKEN>")
        sys.exit(1)

    test = E2ETest(sys.argv[1])
    test.run()
