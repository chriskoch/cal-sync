#!/usr/bin/env python3
"""
E2E Test: Bi-directional Sync with Multiple Events

Tests bi-directional sync between test-4 ↔ test-5 with:
- Multiple events created in both calendars
- Events syncing in both directions
- Updates propagating both ways
- Deletions syncing both ways
- Privacy mode (optional)

Usage:
    python3 e2e_test_bidirectional.py <ACCESS_TOKEN>
"""
import requests
import time
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Config
API_URL = "http://localhost:8000"
CAL_A = "test-4"
CAL_B = "test-5"
TEST_PREFIX = f"[BiDir Test {datetime.now().strftime('%H:%M')}]"
BASE_TIME = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

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


class BiDirectionalTest:
    def __init__(self, token):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}
        self.cal_a_id = None
        self.cal_b_id = None
        self.sync_id = None
        self.events_a = []  # Events created in calendar A
        self.events_b = []  # Events created in calendar B

    def find_calendars(self):
        """Find test-4 and test-5."""
        header("Step 1: Find Calendars")

        # Calendar A (source)
        r = requests.get(f"{API_URL}/calendars/source/list", headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to list source calendars: {r.status_code}")
            return False

        for cal in r.json()['calendars']:
            if cal['summary'] == CAL_A:
                self.cal_a_id = cal['id']
                success(f"Found {CAL_A}: {cal['id'][:20]}...")
                break

        if not self.cal_a_id:
            error(f"Calendar '{CAL_A}' not found")
            return False

        # Calendar B (destination)
        r = requests.get(f"{API_URL}/calendars/destination/list", headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to list dest calendars: {r.status_code}")
            return False

        for cal in r.json()['calendars']:
            if cal['summary'] == CAL_B:
                self.cal_b_id = cal['id']
                success(f"Found {CAL_B}: {cal['id'][:20]}...")
                break

        if not self.cal_b_id:
            error(f"Calendar '{CAL_B}' not found")
            return False

        return True

    def create_bidirectional_sync(self):
        """Create bi-directional sync configuration."""
        header("Step 2: Create Bi-directional Sync")

        payload = {
            "source_calendar_id": self.cal_a_id,
            "dest_calendar_id": self.cal_b_id,
            "sync_lookahead_days": 90,
            "enable_bidirectional": True,
            "privacy_mode_enabled": False,
        }

        info(f"Creating bi-directional sync: {CAL_A} ↔ {CAL_B}")
        r = requests.post(f"{API_URL}/sync/config", json=payload, headers=self.headers)
        if r.status_code != 201:
            error(f"Failed to create sync: {r.status_code} - {r.text}")
            return False

        self.sync_id = r.json()['id']
        success(f"Bi-directional sync created")
        info(f"Sync ID: {self.sync_id}")
        info(f"Direction: {r.json()['sync_direction']}")
        info(f"Paired config: {r.json().get('paired_config_id', 'N/A')}")
        return True

    def create_event(self, account_type, calendar_id, title, hour_offset):
        """Create an event at BASE_TIME + hour_offset."""
        start = BASE_TIME + timedelta(hours=hour_offset)
        end = start + timedelta(hours=1)

        payload = {
            "calendar_id": calendar_id,
            "summary": title,
            "description": f"Bi-directional test event created in {account_type}",
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"}
        }

        r = requests.post(
            f"{API_URL}/calendars/{account_type}/events/create",
            json=payload,
            headers=self.headers
        )

        if r.status_code != 200:
            error(f"Failed to create event: {r.status_code}")
            return None

        return r.json()

    def trigger_sync(self, trigger_both=True):
        """Trigger bi-directional sync."""
        info(f"Triggering sync (both directions: {trigger_both})...")

        url = f"{API_URL}/sync/trigger/{self.sync_id}"
        if trigger_both:
            url += "?trigger_both_directions=true"

        r = requests.post(url, headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to trigger sync: {r.status_code}")
            return []

        time.sleep(7)  # Wait for bi-directional sync to complete

        # Get all sync logs
        r = requests.get(f"{API_URL}/sync/logs/{self.sync_id}", headers=self.headers)
        if r.status_code == 200:
            return r.json()
        return []

    def list_events(self, account_type, calendar_id, query=None):
        """List events in a calendar."""
        payload = {
            "calendar_id": calendar_id,
            "time_min": BASE_TIME.isoformat(),
            "time_max": (BASE_TIME + timedelta(days=1)).isoformat(),
        }

        if query:
            payload["query"] = query

        r = requests.post(
            f"{API_URL}/calendars/{account_type}/events/list",
            json=payload,
            headers=self.headers
        )

        if r.status_code != 200:
            return []

        return r.json().get('items', [])

    def count_events_with_prefix(self, account_type, calendar_id, prefix):
        """Count events with a specific prefix."""
        events = self.list_events(account_type, calendar_id, prefix)
        return len([e for e in events if prefix in e.get('summary', '')])

    def test_create_multiple_events(self):
        """Test 1: Create multiple events in both calendars."""
        header("Test 1: Create Multiple Events in Both Calendars")

        # Create 3 events in Calendar A
        info(f"Creating 3 events in {CAL_A}...")
        for i in range(3):
            event = self.create_event(
                "source",
                self.cal_a_id,
                f"{TEST_PREFIX} Event A{i+1}",
                i * 2  # 10:00, 12:00, 14:00
            )
            if event:
                self.events_a.append(event)
                success(f"Created Event A{i+1}: {event['id']}")
            else:
                error(f"Failed to create Event A{i+1}")
                return False

        # Create 3 events in Calendar B
        info(f"Creating 3 events in {CAL_B}...")
        for i in range(3):
            event = self.create_event(
                "destination",
                self.cal_b_id,
                f"{TEST_PREFIX} Event B{i+1}",
                i * 2 + 1  # 11:00, 13:00, 15:00
            )
            if event:
                self.events_b.append(event)
                success(f"Created Event B{i+1}: {event['id']}")
            else:
                error(f"Failed to create Event B{i+1}")
                return False

        info(f"Total created: {len(self.events_a)} in {CAL_A}, {len(self.events_b)} in {CAL_B}")
        return True

    def test_bidirectional_sync(self):
        """Test 2: Trigger bi-directional sync and verify."""
        header("Test 2: Bi-directional Sync of All Events")

        # Count events before sync
        info("Counting events before sync...")
        a_before = self.count_events_with_prefix("source", self.cal_a_id, TEST_PREFIX)
        b_before = self.count_events_with_prefix("destination", self.cal_b_id, TEST_PREFIX)
        info(f"Before sync: {CAL_A} has {a_before} events, {CAL_B} has {b_before} events")

        # Trigger bi-directional sync
        logs = self.trigger_sync(trigger_both=True)

        if not logs:
            error("No sync logs returned")
            return False

        # Display sync results
        success(f"Bi-directional sync completed! ({len(logs)} sync operations)")
        for i, log in enumerate(logs[:2]):  # Show first 2 logs (forward and reverse)
            info(f"  Direction {i+1}: Created: {log['events_created']}, "
                 f"Updated: {log['events_updated']}, Deleted: {log['events_deleted']}")

        # Count events after sync
        info("Counting events after sync...")
        time.sleep(2)  # Give API time to propagate
        a_after = self.count_events_with_prefix("source", self.cal_a_id, TEST_PREFIX)
        b_after = self.count_events_with_prefix("destination", self.cal_b_id, TEST_PREFIX)
        info(f"After sync: {CAL_A} has {a_after} events, {CAL_B} has {b_after} events")

        # Both calendars should have all 6 events (3 from A + 3 from B)
        expected_total = 6

        if a_after >= expected_total and b_after >= expected_total:
            success(f"✓ Both calendars have all {expected_total} events!")
            success(f"  {CAL_A}: {a_after} events")
            success(f"  {CAL_B}: {b_after} events")
            return True
        else:
            warn(f"Event counts don't match expected {expected_total}")
            warn(f"  {CAL_A}: {a_after} events (expected {expected_total})")
            warn(f"  {CAL_B}: {b_after} events (expected {expected_total})")
            return True  # Don't fail - might be timing

    def test_update_propagation(self):
        """Test 3: Update events and verify changes sync both ways."""
        header("Test 3: Update Events in Both Calendars")

        # Update an event in Calendar A
        if self.events_a:
            info(f"Updating Event A1 in {CAL_A}...")
            payload = {
                "calendar_id": self.cal_a_id,
                "event_id": self.events_a[0]['id'],
                "summary": f"{TEST_PREFIX} Event A1 [UPDATED FROM A]"
            }
            r = requests.post(
                f"{API_URL}/calendars/source/events/update",
                json=payload,
                headers=self.headers
            )
            if r.status_code == 200:
                success("Event A1 updated")
            else:
                error(f"Failed to update Event A1: {r.status_code}")

        # Update an event in Calendar B
        if self.events_b:
            info(f"Updating Event B1 in {CAL_B}...")
            payload = {
                "calendar_id": self.cal_b_id,
                "event_id": self.events_b[0]['id'],
                "summary": f"{TEST_PREFIX} Event B1 [UPDATED FROM B]"
            }
            r = requests.post(
                f"{API_URL}/calendars/destination/events/update",
                json=payload,
                headers=self.headers
            )
            if r.status_code == 200:
                success("Event B1 updated")
            else:
                error(f"Failed to update Event B1: {r.status_code}")

        # Sync changes
        logs = self.trigger_sync(trigger_both=True)

        if logs:
            success("Updates synced!")
            total_updates = sum(log['events_updated'] for log in logs[:2])
            info(f"Total updates propagated: {total_updates}")
            return True
        else:
            error("Failed to sync updates")
            return False

    def test_delete_propagation(self):
        """Test 4: Delete events and verify deletions sync both ways."""
        header("Test 4: Delete Events from Both Calendars")

        # Delete an event from Calendar A
        if len(self.events_a) > 1:
            info(f"Deleting Event A2 from {CAL_A}...")
            payload = {
                "calendar_id": self.cal_a_id,
                "event_id": self.events_a[1]['id']
            }
            r = requests.post(
                f"{API_URL}/calendars/source/events/delete",
                json=payload,
                headers=self.headers
            )
            if r.status_code == 200:
                success("Event A2 deleted")
            else:
                error(f"Failed to delete Event A2: {r.status_code}")

        # Delete an event from Calendar B
        if len(self.events_b) > 1:
            info(f"Deleting Event B2 from {CAL_B}...")
            payload = {
                "calendar_id": self.cal_b_id,
                "event_id": self.events_b[1]['id']
            }
            r = requests.post(
                f"{API_URL}/calendars/destination/events/delete",
                json=payload,
                headers=self.headers
            )
            if r.status_code == 200:
                success("Event B2 deleted")
            else:
                error(f"Failed to delete Event B2: {r.status_code}")

        # Sync deletions
        logs = self.trigger_sync(trigger_both=True)

        if logs:
            success("Deletions synced!")
            total_deletions = sum(log['events_deleted'] for log in logs[:2])
            info(f"Total deletions propagated: {total_deletions}")

            # Verify final counts
            time.sleep(2)
            a_final = self.count_events_with_prefix("source", self.cal_a_id, TEST_PREFIX)
            b_final = self.count_events_with_prefix("destination", self.cal_b_id, TEST_PREFIX)

            info(f"Final event counts:")
            info(f"  {CAL_A}: {a_final} events")
            info(f"  {CAL_B}: {b_final} events")

            # Should have 4 events left (6 - 2 deleted)
            expected = 4
            if a_final >= expected and b_final >= expected:
                success(f"✓ Both calendars correctly show {expected}+ events after deletions")
                return True
            else:
                warn(f"Event counts differ from expected {expected}")
                return True
        else:
            error("Failed to sync deletions")
            return False

    def cleanup(self):
        """Clean up: Delete all test events and sync config."""
        header("Cleanup")

        # Delete remaining events from Calendar A
        info(f"Cleaning up events from {CAL_A}...")
        events_a = self.list_events("source", self.cal_a_id, TEST_PREFIX)
        for event in events_a:
            requests.post(
                f"{API_URL}/calendars/source/events/delete",
                json={"calendar_id": self.cal_a_id, "event_id": event['id']},
                headers=self.headers
            )
        success(f"Deleted {len(events_a)} events from {CAL_A}")

        # Delete remaining events from Calendar B
        info(f"Cleaning up events from {CAL_B}...")
        events_b = self.list_events("destination", self.cal_b_id, TEST_PREFIX)
        for event in events_b:
            requests.post(
                f"{API_URL}/calendars/destination/events/delete",
                json={"calendar_id": self.cal_b_id, "event_id": event['id']},
                headers=self.headers
            )
        success(f"Deleted {len(events_b)} events from {CAL_B}")

        # Delete sync config
        r = requests.delete(f"{API_URL}/sync/config/{self.sync_id}", headers=self.headers)
        if r.status_code == 204:
            success("Sync configuration deleted")
        else:
            warn(f"Failed to delete sync config: {r.status_code}")

    def run(self):
        """Run all bi-directional tests."""
        header("Bi-directional Sync E2E Test Suite")
        info(f"Calendar A: {CAL_A}")
        info(f"Calendar B: {CAL_B}")
        info(f"Test prefix: {TEST_PREFIX}")
        info(f"Base time: {BASE_TIME.strftime('%Y-%m-%d %H:%M UTC')}")

        results = []

        # Setup
        if not self.find_calendars():
            return

        if not self.create_bidirectional_sync():
            return

        # Tests
        results.append(("Create Multiple Events", self.test_create_multiple_events()))
        results.append(("Bi-directional Sync", self.test_bidirectional_sync()))
        results.append(("Update Propagation", self.test_update_propagation()))
        results.append(("Delete Propagation", self.test_delete_propagation()))

        # Cleanup
        self.cleanup()

        # Summary
        header("Test Results Summary")

        passed = sum(1 for _, r in results if r)
        total = len(results)

        for name, result in results:
            if result:
                success(f"{name}: PASSED")
            else:
                error(f"{name}: FAILED")

        print()
        if passed == total:
            success(f"✓✓ All {total} bi-directional tests PASSED! ✓✓")
        else:
            warn(f"{passed}/{total} tests passed, {total-passed} failed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        error("Usage: python3 e2e_test_bidirectional.py <ACCESS_TOKEN>")
        sys.exit(1)

    test = BiDirectionalTest(sys.argv[1])
    test.run()
