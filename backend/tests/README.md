# Backend Test Suite

This directory contains the backend test suite for the Calendar Sync application, implemented using `pytest`.

**Status**: All tests passing (52 tests, 0 failures)

## Running Tests

### Basic Commands
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_oauth_api.py

# Run tests by marker
pytest -m unit
pytest -m integration
pytest -m oauth
```

### Parallel Execution
```bash
# Run tests in parallel (faster for large test suites)
pytest -n auto

# Run with specific number of workers
pytest -n 4
```

### Coverage
```bash
# Run with coverage report
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Test Optimizations

### 1. Database Fixtures
- **Session-scoped database**: Tables are created once per test session
- **Transaction rollback**: Each test uses a transaction that rolls back, avoiding table drops
- **Result**: ~3-5x faster test execution

### 2. Shared Fixtures
Common mock setups are available as reusable fixtures:
- `mock_oauth_flow`: Pre-configured OAuth flow mock
- `mock_oauth_credentials`: Pre-configured OAuth credentials mock
- `mock_google_calendar_api`: Pre-configured Google Calendar API mock

### 3. Test Utilities Module (`test_utils.py`)
- **`create_test_user()`**: A helper function to quickly create and persist a `User` object in the test database.
- **`create_oauth_token()`**: A helper function to create and persist an `OAuthToken` object in the test database.
- **`assert_response_success()`**: A utility for standardizing assertions for successful API responses.
- **`assert_response_error()`**: A utility for standardizing assertions for error API responses.
- **Result**: Cleaner, more readable, and more maintainable test code by abstracting common setup and assertion logic.

**Note**: This module is available for future use. Current tests use fixtures from `conftest.py` for consistency.

### 4. Parallel Test Execution Support
- The `pytest-xdist` plugin has been added to `requirements.txt`.
- **Result**: Tests can now be run in parallel across multiple CPU cores, leading to significantly faster overall test execution times on multi-core systems.
- **Usage**: `pytest -n auto` (auto-detects CPU cores) or `pytest -n 4` (specify worker count)

## Test Organization

### Markers
- `@pytest.mark.unit`: Fast unit tests (no database)
- `@pytest.mark.integration`: Integration tests (with database)
- `@pytest.mark.oauth`: OAuth-related tests
- `@pytest.mark.auth`: Authentication tests
- `@pytest.mark.sync`: Sync operation tests

### Fixture Scopes
- `session`: Created once per test session (database engine)
- `function`: Created for each test (database session, client)

## Performance Tips

1. **Use session-scoped fixtures** for expensive setup
2. **Use shared mocks** instead of creating new ones each time
3. **Run tests in parallel** when possible
4. **Mark slow tests** with `@pytest.mark.slow` to skip in quick runs
5. **Use test utilities** to reduce boilerplate

### 5. Removed Obsolete Tests
- Tests related to password hashing in `test_security.py` were removed, as password-based authentication is no longer part of the application.
- **Result**: The test suite only covers existing and relevant functionality.

### 6. Improved Pytest Configuration (`pytest.ini`)
- Added `--tb=short` to `addopts` for shorter, more focused error tracebacks, improving readability of test failures.
- Added `--maxfail=5` to stop test execution after 5 failures, saving time in CI/CD pipelines or local development when many tests are failing.
- **Result**: Enhanced developer experience with clearer feedback and more efficient test runs.

### 7. Updated OAuth Tests
- Refactored `test_oauth_api.py` to leverage the new shared mock fixtures.
- Reduced redundant mock setup code within individual tests.
- Added comprehensive tests for the Google OAuth registration flow, covering both new user creation and updating existing users' source tokens.
- Fixed fixture dependencies (removed `mocker` parameter, using `unittest.mock` directly).
- **Result**: More robust, maintainable, and consistent tests for the core authentication flow.

### 8. Fixed Sync Engine Tests
- Added `SyncConfig` creation in tests to satisfy foreign key constraints.
- All sync engine tests now properly set up required database relationships.
- **Result**: All 52 tests passing with no foreign key constraint errors.

## Example Usage

```python
def test_example(client, db, test_user, mock_oauth_flow):
    """Example test using optimized fixtures."""
    # Use shared fixtures
    with patch('app.api.oauth.create_flow', return_value=mock_oauth_flow):
        response = client.get("/oauth/start/source", headers=auth_headers)
        assert response.status_code == 200
```

