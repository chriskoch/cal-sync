# E2E Testing Scripts

This directory contains comprehensive end-to-end test scripts that validate calendar synchronization functionality using real Google Calendar API calls.

## Prerequisites

- User must have valid OAuth tokens for both source and destination accounts
- Calendars `test-4` (source) and `test-5` (destination) must exist in your Google accounts
- Backend server must be running at `http://localhost:8000`
- Valid access token (JWT) from the application

## Getting an Access Token

1. Log in to the application at `http://localhost:3000`
2. Open browser developer tools (F12)
3. Go to Application/Storage → Local Storage
4. Copy the JWT token value
5. Use this token as the `<ACCESS_TOKEN>` parameter

## Test Scripts

### Basic Sync Testing

#### `e2e_test_auto.py` - One-Way Sync (Full Automation)
Comprehensive test of one-way calendar synchronization with full CRUD operations.

**What it tests:**
- Creating events in source calendar
- Syncing to destination calendar
- Renaming events (sync updates)
- Moving events to different times (sync updates)
- Deleting source events (removes from destination)
- Event comparison and idempotency

**Usage:**
```bash
python3 backend/tests/e2e/e2e_test_auto.py <ACCESS_TOKEN>
```

**Duration:** ~15 seconds

---

#### `e2e_test_bidirectional.py` - Bi-Directional Sync
Validates bi-directional synchronization with conflict resolution and loop prevention.

**What it tests:**
- Creating events in both calendars
- Syncing in both directions simultaneously
- Loop prevention (synced events don't re-sync)
- Paired config creation and linking
- Event updates in both directions

**Usage:**
```bash
python3 backend/tests/e2e/e2e_test_bidirectional.py <ACCESS_TOKEN>
```

**Duration:** ~20 seconds

---

### Edge Cases & Special Scenarios

#### `e2e_test_delete_synced.py` - Idempotency After Manual Deletion
Tests sync idempotency when users manually delete synced events.

**What it tests:**
- Syncing an event from A → B
- Manually deleting the synced event in B
- Re-running sync to verify event is recreated
- Validates sync engine treats cancelled events as non-existent

**Edge Case:** Ensures sync engine doesn't treat deleted destination events as "already synced"

**Usage:**
```bash
python3 backend/tests/e2e/e2e_test_delete_synced.py <ACCESS_TOKEN>
```

**Duration:** ~15 seconds

---

#### `e2e_test_recurring.py` - Recurring Events
Documents limitations and edge cases with recurring events.

**What it tests:**
- Basic recurring event syncing
- Documents 8 known edge cases with recurring events

**Known Limitations:**
- Backend test helpers cannot create events with recurrence rules
- Cannot modify single instances of recurring events
- Cannot delete single instances (requires EXDATE handling)

**Usage:**
```bash
python3 backend/tests/e2e/e2e_test_recurring.py <ACCESS_TOKEN>
```

**Note:** This test documents limitations rather than providing full coverage

---

### Privacy Mode Testing

#### `e2e_test_privacy_one_way.py` - One-Way Privacy Mode
Validates that privacy mode correctly hides event details while preserving time slots.

**What it tests:**
- Creating source event with full details (title, description, location, attendees)
- Syncing with privacy mode enabled
- Verifying destination event shows placeholder text
- Verifying all sensitive details are removed
- Verifying times/dates are preserved exactly
- Updating source event and verifying privacy maintained

**Privacy Transformations:**
- Title → Custom placeholder text
- Description → Empty
- Location → Empty
- Attendees → Removed
- Start/End times → Preserved exactly

**Usage:**
```bash
python3 backend/tests/e2e/e2e_test_privacy_one_way.py <ACCESS_TOKEN>
```

**Duration:** ~15 seconds

**Example Output:**
```
✓ Source event created with full details
✓ Privacy mode correctly hides title, description, location, attendees
✓ Time slots preserved exactly
✓ Privacy maintained after source event updates
```

---

#### `e2e_test_privacy_bidirectional.py` - Bi-Directional Privacy with Different Placeholders
Validates privacy mode with different placeholder texts for each sync direction.

**What it tests:**
- Creating work event in calendar A (test-4) with confidential details
- Creating personal event in calendar B (test-5) with private details
- Bi-directional sync with direction-specific privacy:
  - A → B: "Work Meeting" placeholder
  - B → A: "Personal Time" placeholder
- Verifying correct placeholder used in each direction
- Verifying times preserved in both directions
- Updating both events and verifying privacy maintained

**Use Case:** Separating work and personal calendars while maintaining privacy in both directions

**Usage:**
```bash
python3 backend/tests/e2e/e2e_test_privacy_bidirectional.py <ACCESS_TOKEN>
```

**Duration:** ~20 seconds

**Example Output:**
```
✓ Work event synced to personal calendar with 'Work Meeting' placeholder
✓ Personal event synced to work calendar with 'Personal Time' placeholder
✓ All confidential details hidden in both directions
✓ Time slots preserved exactly in both directions
```

---

## Test Architecture

All E2E tests follow a consistent pattern:

1. **Setup:** Create test events with specific data
2. **Configure:** Create sync configuration with desired settings
3. **Execute:** Trigger manual sync
4. **Verify:** Validate results using Google Calendar API
5. **Update:** Modify events to test update scenarios
6. **Re-verify:** Ensure updates sync correctly
7. **Cleanup:** Delete all created resources (events and configs)

## Cleanup

All tests include automatic cleanup to remove:
- Created events in both calendars
- Sync configurations
- Event mappings and sync logs (via cascade delete)

If a test is interrupted (Ctrl+C), some resources may remain. You can manually clean up via:
- Dashboard UI (delete sync configs)
- Google Calendar UI (delete test events)
- Database (clear sync_logs and event_mappings tables)

## Common Issues

### "OAuth credentials not found"
- Ensure you've connected both source and destination accounts in the web UI
- Check `/oauth/status` endpoint to verify tokens exist

### "Calendar not found: test-4 or test-5"
- Create calendars named exactly `test-4` and `test-5` in your Google accounts
- Or modify the test scripts to use your calendar names

### "Invalid token"
- Token may have expired (30 minute lifetime)
- Log out and log back in to get a fresh token

### "Sync failed with 410 error"
- This is expected behavior (event already deleted)
- The sync engine correctly handles this by skipping

## Test Coverage

| Feature | Unit Tests | Integration Tests | E2E Tests |
|---------|------------|-------------------|-----------|
| One-way sync | ✓ | ✓ | ✓ |
| Bi-directional sync | ✓ | ✓ | ✓ |
| Privacy mode | ✓ | ✓ | ✓ |
| Event CRUD | ✓ | ✓ | ✓ |
| Conflict resolution | ✓ | ✓ | ✓ |
| Loop prevention | ✓ | - | ✓ |
| Error handling | ✓ | ✓ | ✓ |
| Recurring events | ✓ | - | Partial |
| Idempotency | ✓ | - | ✓ |

## Running All E2E Tests

```bash
# Get access token first (see "Getting an Access Token" above)
export TOKEN="your-jwt-token-here"

# Run all tests
python3 backend/tests/e2e/e2e_test_auto.py $TOKEN
python3 backend/tests/e2e/e2e_test_bidirectional.py $TOKEN
python3 backend/tests/e2e/e2e_test_delete_synced.py $TOKEN
python3 backend/tests/e2e/e2e_test_privacy_one_way.py $TOKEN
python3 backend/tests/e2e/e2e_test_privacy_bidirectional.py $TOKEN
```

**Total Duration:** ~1.5 minutes for all tests

## Contributing

When adding new E2E tests:

1. Follow the existing test structure (setup → configure → execute → verify → cleanup)
2. Include automatic cleanup in a try/finally or cleanup function
3. Add clear step-by-step output with `print_step()` function
4. Document what the test validates in the docstring
5. Update this README with test description
6. Add to CLAUDE.md E2E Testing Scripts section
