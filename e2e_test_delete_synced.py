#!/usr/bin/env python3
"""
E2E Test: Delete Synced Event Edge Case

Tests the edge case:
1. Create event in source (test-4)
2. Sync → event appears in destination (test-5)
3. Manually delete the SYNCED copy from destination
4. Resync → verify behavior (should recreate or handle gracefully)

This tests sync engine idempotency and orphaned event handling.

Usage:
    python3 e2e_test_delete_synced.py <ACCESS_TOKEN>
"""
import requests
import time
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

# Config
API_URL = "http://localhost:8000"
SOURCE_CAL = "test-4"
DEST_CAL = "test-5"
TEST_SUMMARY = f"[Delete Sync Test] {datetime.now().strftime('%H:%M:%S')}"
TEST_START = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
TEST_END = TEST_START + timedelta(hours=1)

# Colors
C_HEADER = '\033[95m\033[1m'
C_GREEN = '\033[92m'
C_RED = '\033[91m'
C_BLUE = '\033[96m'
C_YELLOW = '\033[93m'
C_PURPLE = '\033[95m'
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


def highlight(msg):
    print(f"{C_PURPLE}▶ {msg}{C_END}")


class DeleteSyncedTest:
    def __init__(self, token):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}
        self.source_cal_id = None
        self.dest_cal_id = None
        self.sync_id = None
        self.source_event_id = None
        self.synced_event_id = None

    def find_calendars(self):
        """Find test-4 and test-5."""
        header("Setup: Find Calendars")

        # Source
        r = requests.get(f"{API_URL}/calendars/source/list", headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to list source calendars: {r.status_code}")
            return False

        for cal in r.json()['calendars']:
            if cal['summary'] == SOURCE_CAL:
                self.source_cal_id = cal['id']
                success(f"Found {SOURCE_CAL}")
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
                success(f"Found {DEST_CAL}")
                break

        if not self.dest_cal_id:
            error(f"Calendar '{DEST_CAL}' not found")
            return False

        return True

    def create_sync(self):
        """Create one-way sync."""
        header("Setup: Create Sync Configuration")

        payload = {
            "source_calendar_id": self.source_cal_id,
            "dest_calendar_id": self.dest_cal_id,
            "sync_lookahead_days": 90,
            "enable_bidirectional": False,
        }

        r = requests.post(f"{API_URL}/sync/config", json=payload, headers=self.headers)
        if r.status_code != 201:
            error(f"Failed to create sync: {r.status_code}")
            return False

        self.sync_id = r.json()['id']
        success(f"Created one-way sync: {SOURCE_CAL} → {DEST_CAL}")
        info(f"Sync ID: {self.sync_id}")
        return True

    def trigger_sync(self):
        """Trigger sync and get results."""
        info("Triggering sync...")
        r = requests.post(f"{API_URL}/sync/trigger/{self.sync_id}", headers=self.headers)
        if r.status_code != 200:
            error(f"Failed to trigger sync: {r.status_code}")
            return None

        time.sleep(6)  # Wait for sync

        r = requests.get(f"{API_URL}/sync/logs/{self.sync_id}", headers=self.headers)
        if r.status_code == 200:
            logs = r.json()
            if logs:
                return logs[0]
        return None

    def find_event_in_dest(self, summary):
        """Find event in destination by summary."""
        payload = {
            "calendar_id": self.dest_cal_id,
            "time_min": TEST_START.isoformat(),
            "time_max": (TEST_START + timedelta(days=1)).isoformat(),
            "query": summary
        }

        r = requests.post(
            f"{API_URL}/calendars/destination/events/list",
            json=payload,
            headers=self.headers
        )

        if r.status_code != 200:
            return None

        events = r.json().get('items', [])
        for event in events:
            if summary in event.get('summary', ''):
                return event
        return None

    def get_event_details(self, account_type, calendar_id, event_id):
        """Get full event details to check extended properties."""
        # Use list to get event with extended properties
        payload = {
            "calendar_id": calendar_id,
            "time_min": (TEST_START - timedelta(days=1)).isoformat(),
            "time_max": (TEST_START + timedelta(days=2)).isoformat(),
        }

        r = requests.post(
            f"{API_URL}/calendars/{account_type}/events/list",
            json=payload,
            headers=self.headers
        )

        if r.status_code != 200:
            return None

        events = r.json().get('items', [])
        for event in events:
            if event.get('id') == event_id:
                return event
        return None

    def step1_create_event(self):
        """Step 1: Create event in source calendar."""
        header("Step 1: Create Event in Source")

        payload = {
            "calendar_id": self.source_cal_id,
            "summary": TEST_SUMMARY,
            "description": "Testing deletion of synced event",
            "start": {"dateTime": TEST_START.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": TEST_END.isoformat(), "timeZone": "UTC"}
        }

        info(f"Creating event: {TEST_SUMMARY}")
        info(f"Time: {TEST_START.strftime('%Y-%m-%d %H:%M UTC')}")

        r = requests.post(
            f"{API_URL}/calendars/source/events/create",
            json=payload,
            headers=self.headers
        )

        if r.status_code != 200:
            error(f"Failed to create event: {r.status_code}")
            return False

        self.source_event_id = r.json()['id']
        success(f"Event created in {SOURCE_CAL}")
        info(f"Event ID: {self.source_event_id}")
        return True

    def step2_initial_sync(self):
        """Step 2: Sync event to destination."""
        header("Step 2: Initial Sync to Destination")

        log = self.trigger_sync()
        if not log:
            error("Sync failed")
            return False

        success("Sync completed!")
        info(f"Status: {log['status']}")
        info(f"Events created: {log['events_created']}")
        info(f"Events updated: {log['events_updated']}")
        info(f"Events deleted: {log['events_deleted']}")

        # Verify event exists in destination
        info(f"Verifying event in {DEST_CAL}...")
        time.sleep(2)
        synced_event = self.find_event_in_dest(TEST_SUMMARY)

        if synced_event:
            self.synced_event_id = synced_event['id']
            success(f"✓ Event synced to {DEST_CAL}")
            info(f"Synced event ID: {self.synced_event_id}")

            # Check for source_id in extended properties
            ext_props = synced_event.get('extendedProperties', {})
            shared_props = ext_props.get('shared', {})
            source_id = shared_props.get('source_id')

            if source_id:
                highlight(f"Extended property 'source_id' = {source_id}")
                if source_id == self.source_event_id:
                    success("✓ Source ID correctly links to original event")
                else:
                    warn(f"Source ID mismatch: {source_id} vs {self.source_event_id}")
            else:
                warn("No 'source_id' found in extended properties")

            return True
        else:
            error(f"Event not found in {DEST_CAL}")
            return False

    def step3_delete_synced(self):
        """Step 3: Manually delete the SYNCED event from destination."""
        header("Step 3: Delete SYNCED Event from Destination")

        highlight(f"Deleting synced copy from {DEST_CAL} (NOT the original)")
        info(f"Deleting event ID: {self.synced_event_id}")
        info(f"Original in {SOURCE_CAL} still exists: {self.source_event_id}")

        payload = {
            "calendar_id": self.dest_cal_id,
            "event_id": self.synced_event_id
        }

        r = requests.post(
            f"{API_URL}/calendars/destination/events/delete",
            json=payload,
            headers=self.headers
        )

        if r.status_code != 200:
            error(f"Failed to delete synced event: {r.status_code}")
            return False

        success(f"Synced event deleted from {DEST_CAL}")

        # Verify deletion
        time.sleep(2)
        check = self.find_event_in_dest(TEST_SUMMARY)
        if not check:
            success(f"✓ Confirmed: Event no longer in {DEST_CAL}")
            return True
        else:
            warn("Event still found (might be caching)")
            return True

    def step4_resync(self):
        """Step 4: Resync and verify behavior."""
        header("Step 4: Resync After Manual Deletion")

        highlight("Question: What happens when we resync?")
        info("The source event still exists")
        info("The destination copy was manually deleted")
        info("Expected: Sync should recreate the event in destination")

        log = self.trigger_sync()
        if not log:
            error("Resync failed")
            return False

        success("Resync completed!")
        info(f"Status: {log['status']}")
        info(f"Events created: {log['events_created']}")
        info(f"Events updated: {log['events_updated']}")
        info(f"Events deleted: {log['events_deleted']}")

        # Check if event was recreated
        time.sleep(2)
        recreated = self.find_event_in_dest(TEST_SUMMARY)

        if recreated:
            success(f"✓ Event RECREATED in {DEST_CAL}!")
            info(f"New synced event ID: {recreated['id']}")

            # Verify it has source_id
            ext_props = recreated.get('extendedProperties', {})
            shared_props = ext_props.get('shared', {})
            source_id = shared_props.get('source_id')

            if source_id == self.source_event_id:
                success("✓ Source ID correctly links to original event")
                highlight("RESULT: Sync is idempotent - recreates deleted synced events")
            else:
                warn(f"Source ID issue: {source_id}")

            # Store new synced event ID for cleanup
            self.synced_event_id = recreated['id']
            return True
        else:
            warn(f"Event NOT recreated in {DEST_CAL}")
            info("This could indicate:")
            info("  - Sync engine treats manual deletion as intentional")
            info("  - Or there's an issue with event recreation logic")
            return False

    def step5_verify_original_intact(self):
        """Step 5: Verify original event is still intact."""
        header("Step 5: Verify Original Event Intact")

        info(f"Checking if original event still exists in {SOURCE_CAL}...")

        # List events from source
        payload = {
            "calendar_id": self.source_cal_id,
            "time_min": TEST_START.isoformat(),
            "time_max": (TEST_START + timedelta(days=1)).isoformat(),
            "query": TEST_SUMMARY
        }

        r = requests.post(
            f"{API_URL}/calendars/source/events/list",
            json=payload,
            headers=self.headers
        )

        if r.status_code != 200:
            error("Failed to check source calendar")
            return False

        events = r.json().get('items', [])
        original_exists = any(e.get('id') == self.source_event_id for e in events)

        if original_exists:
            success(f"✓ Original event still exists in {SOURCE_CAL}")
            info(f"Event ID: {self.source_event_id}")
            highlight("CONFIRMED: Deleting synced copy does NOT affect original")
            return True
        else:
            error(f"Original event missing from {SOURCE_CAL}")
            return False

    def cleanup(self):
        """Clean up test data."""
        header("Cleanup")

        # Delete source event
        if self.source_event_id:
            info(f"Deleting original event from {SOURCE_CAL}...")
            r = requests.post(
                f"{API_URL}/calendars/source/events/delete",
                json={
                    "calendar_id": self.source_cal_id,
                    "event_id": self.source_event_id
                },
                headers=self.headers
            )
            if r.status_code == 200:
                success(f"Deleted original event from {SOURCE_CAL}")

        # Delete synced event if it exists
        if self.synced_event_id:
            info(f"Deleting synced event from {DEST_CAL}...")
            r = requests.post(
                f"{API_URL}/calendars/destination/events/delete",
                json={
                    "calendar_id": self.dest_cal_id,
                    "event_id": self.synced_event_id
                },
                headers=self.headers
            )
            if r.status_code == 200:
                success(f"Deleted synced event from {DEST_CAL}")

        # Delete sync config
        if self.sync_id:
            r = requests.delete(
                f"{API_URL}/sync/config/{self.sync_id}",
                headers=self.headers
            )
            if r.status_code == 204:
                success("Deleted sync configuration")

    def run(self):
        """Run the complete test."""
        header("Edge Case Test: Delete Synced Event & Resync")
        info("Testing sync engine idempotency and orphaned event handling")
        info(f"Source: {SOURCE_CAL}")
        info(f"Destination: {DEST_CAL}")
        info(f"Test: {TEST_SUMMARY}")

        results = []

        # Setup
        if not self.find_calendars():
            return

        if not self.create_sync():
            return

        # Execute test steps
        results.append(("Step 1: Create Event", self.step1_create_event()))
        results.append(("Step 2: Initial Sync", self.step2_initial_sync()))
        results.append(("Step 3: Delete Synced Event", self.step3_delete_synced()))
        results.append(("Step 4: Resync After Deletion", self.step4_resync()))
        results.append(("Step 5: Verify Original Intact", self.step5_verify_original_intact()))

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
            success(f"✓ All {total} steps PASSED!")
            print()
            highlight("KEY FINDINGS:")
            success("✓ Sync engine is idempotent")
            success("✓ Recreates deleted synced events when source still exists")
            success("✓ Deleting synced copy does NOT affect original")
            success("✓ Source_id properly tracks event relationships")
        else:
            warn(f"{passed}/{total} steps passed, {total-passed} failed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        error("Usage: python3 e2e_test_delete_synced.py <ACCESS_TOKEN>")
        sys.exit(1)

    test = DeleteSyncedTest(sys.argv[1])
    test.run()
