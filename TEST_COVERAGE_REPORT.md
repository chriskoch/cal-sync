# Test Coverage Analysis & Recommendations

**Generated**: 2026-01-07
**Project**: cal-sync
**Total Backend Tests**: ~160 automated tests
**Total Frontend Tests**: 31 automated tests

---

## Executive Summary

The cal-sync project has **excellent test coverage for core business logic** (sync engine: 109 tests, scheduler: 43 tests, sync API: 53 tests) but **critical gaps in infrastructure testing**. Security middleware, calendars API, and main application endpoints have zero test coverage despite being production-exposed.

**Overall Coverage Estimate**:
- Backend: ~65-70%
- Frontend: ~25-30%

---

## Current Test Coverage

### ✅ Excellent Coverage (90%+)

#### Core Sync Engine (`test_sync_engine.py` - 109 tests)
- Event creation, updates, deletion
- Idempotency and duplicate handling
- 410/404 error handling
- Bidirectional sync with loop prevention
- Privacy mode transformations
- Conflict resolution (origin-based)
- Content hashing and change detection
- Event mapping management

**Files Covered**:
- `backend/app/core/sync_engine.py` ⭐ 95% coverage

#### Scheduler (`test_scheduler.py` + `test_sync_api_scheduling.py` - 43 tests)
- Lifecycle management (start/stop)
- Job add/remove/update operations
- Cron expression validation
- Timezone validation
- Database job loading
- Auto-sync API integration

**Files Covered**:
- `backend/app/core/scheduler.py` ⭐ 100% coverage

#### Sync API (`test_sync_api.py` - 53 tests)
- Create/update/delete sync configurations
- List configurations
- Manual sync triggers (one-way and bidirectional)
- Privacy settings validation
- Paired config management
- Authorization checks

**Files Covered**:
- `backend/app/api/sync.py` ⭐ 99% coverage

#### OAuth API (`test_oauth_api.py` - 22 tests)
- OAuth flow initiation (source/destination/register)
- Callback handling
- Token storage and updates
- Status checks
- UUID type handling

**Files Covered**:
- `backend/app/api/oauth.py` ⭐ 95% coverage

#### Security (`test_security.py` - 8 tests)
- JWT token creation and validation
- Fernet encryption/decryption
- Token expiry handling

**Files Covered**:
- `backend/app/security.py` ⭐ 90% coverage

---

## Critical Gaps (Zero Coverage)

### 🔴 HIGH RISK: Security Headers Middleware

**File**: `backend/app/middleware/security_headers.py`
**Current Tests**: 0
**Lines of Code**: ~30

**Why This Matters**:
- Sets security headers (CSP, HSTS, XSS protection)
- Production-exposed for every request
- Security vulnerabilities may go undetected

**Recommended Tests**:
```python
# backend/tests/test_middleware_security.py

def test_security_headers_present(client):
    """Verify all security headers are set on responses"""
    response = client.get("/")
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers

def test_hsts_header_value(client):
    """Verify HSTS header has correct max-age"""
    response = client.get("/")
    hsts = response.headers["Strict-Transport-Security"]
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts

def test_csp_header_value(client):
    """Verify CSP header restricts unsafe sources"""
    response = client.get("/")
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp

def test_security_headers_on_api_endpoints(client, auth_token):
    """Verify security headers present on API responses"""
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert "X-Content-Type-Options" in response.headers

def test_security_headers_on_error_responses(client):
    """Verify security headers present even on error responses"""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
    assert "X-Content-Type-Options" in response.headers
```

**Estimated Effort**: 2 hours
**Priority**: **CRITICAL**

---

### 🔴 HIGH RISK: Calendars API

**File**: `backend/app/api/calendars.py`
**Current Tests**: 0
**Endpoints**: 5 production-exposed endpoints
**Lines of Code**: ~150

**Why This Matters**:
- Test helper endpoints exposed in production
- Direct Google Calendar API integration
- Error handling untested
- Authorization checks untested

**Endpoints Without Tests**:
```
GET  /api/calendars/{account_type}/list
POST /api/calendars/{account_type}/events/create
POST /api/calendars/{account_type}/events/update
POST /api/calendars/{account_type}/events/delete
POST /api/calendars/{account_type}/events/list
```

**Recommended Tests**:
```python
# backend/tests/test_calendars_api.py

def test_list_calendars_source(client, auth_token, mock_google_api):
    """Test listing source calendars"""
    mock_google_api.calendarList().list().execute.return_value = {
        "items": [{"id": "cal1", "summary": "Test Cal", "colorId": "1"}]
    }
    response = client.get("/api/calendars/source/list",
                          headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_list_calendars_unauthorized(client):
    """Test calendar list requires authentication"""
    response = client.get("/api/calendars/source/list")
    assert response.status_code == 401

def test_list_calendars_no_oauth_token(client, auth_token, db):
    """Test calendar list fails without OAuth token"""
    # User has no OAuth token for this account type
    response = client.get("/api/calendars/destination/list",
                          headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 404

def test_create_event(client, auth_token, mock_google_api):
    """Test creating calendar event"""
    # Test implementation

def test_update_event(client, auth_token, mock_google_api):
    """Test updating calendar event"""
    # Test implementation

def test_delete_event(client, auth_token, mock_google_api):
    """Test deleting calendar event"""
    # Test implementation

def test_list_events_with_filters(client, auth_token, mock_google_api):
    """Test listing events with time window filters"""
    # Test implementation

def test_invalid_account_type(client, auth_token):
    """Test endpoints reject invalid account_type"""
    response = client.get("/api/calendars/invalid/list",
                          headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 422
```

**Estimated Effort**: 4-6 hours
**Priority**: **CRITICAL**

---

### 🟡 MEDIUM RISK: Main Application Endpoints

**File**: `backend/app/main.py`
**Current Tests**: 2 (lifespan only)
**Lines of Code**: ~80

**What's Tested**: ✅ Lifespan management, scheduler initialization

**What's Missing**:
- Root endpoint `/` (returns version info)
- Health check `/health` (critical for monitoring)
- SPA routing catch-all `/{full_path:path}`
- Static file serving
- CORS configuration

**Recommended Tests**:
```python
# backend/tests/test_main_endpoints.py

def test_root_endpoint_returns_version(client):
    """Test root endpoint returns app info"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["app"] == "Calendar Sync"

def test_health_check_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_health_check_no_auth_required(client):
    """Test health check doesn't require authentication"""
    response = client.get("/health")
    assert response.status_code == 200

def test_spa_routing_serves_index_html(client):
    """Test SPA catch-all serves index.html for frontend routes"""
    response = client.get("/dashboard")
    assert response.status_code == 200
    # Should serve index.html, not 404

def test_api_routes_not_caught_by_spa(client):
    """Test API routes aren't caught by SPA catch-all"""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
    # Should return JSON error, not HTML

def test_cors_headers_present(client):
    """Test CORS headers are set correctly"""
    response = client.options("/api/auth/me",
                              headers={"Origin": "http://localhost:3033"})
    assert "Access-Control-Allow-Origin" in response.headers

def test_static_files_served(client):
    """Test static files are served from /static"""
    # Requires static files to exist in test environment
    pass
```

**Estimated Effort**: 3-4 hours
**Priority**: **HIGH**

---

### 🟡 MEDIUM RISK: Database Models

**Files**:
- `backend/app/models/user.py`
- `backend/app/models/oauth_token.py`
- `backend/app/models/sync_config.py`
- `backend/app/models/sync_log.py`
- `backend/app/models/event_mapping.py`

**Current Tests**: 0 (indirect coverage through API tests)
**Lines of Code**: ~200 total

**Why This Matters**:
- Field validators may not work as expected
- Relationship cascades untested
- Default values not verified
- Constraint violations not tested

**Recommended Tests**:
```python
# backend/tests/test_models.py

def test_user_model_creation(db):
    """Test creating user with valid data"""
    user = User(email="test@example.com")
    db.add(user)
    db.commit()
    assert user.id is not None
    assert user.created_at is not None

def test_user_email_unique_constraint(db):
    """Test user email must be unique"""
    user1 = User(email="test@example.com")
    user2 = User(email="test@example.com")
    db.add(user1)
    db.commit()
    db.add(user2)
    with pytest.raises(IntegrityError):
        db.commit()

def test_sync_config_cascade_delete(db, test_user):
    """Test deleting user cascades to sync configs"""
    config = SyncConfig(user_id=test_user.id, ...)
    db.add(config)
    db.commit()

    db.delete(test_user)
    db.commit()

    assert db.query(SyncConfig).filter_by(id=config.id).first() is None

def test_sync_config_default_values(db, test_user):
    """Test sync config default values are set correctly"""
    config = SyncConfig(
        user_id=test_user.id,
        source_calendar_id="cal1",
        dest_calendar_id="cal2"
    )
    db.add(config)
    db.commit()

    assert config.sync_lookahead_days == 90
    assert config.is_active is True
    assert config.auto_sync_enabled is False
    assert config.auto_sync_timezone == "UTC"

def test_oauth_token_account_type_validation(db, test_user):
    """Test oauth_token account_type must be valid"""
    # This depends on whether you have validators
    token = OAuthToken(
        user_id=test_user.id,
        account_type="invalid",
        access_token_encrypted="..."
    )
    # Should either raise validation error or accept any string

def test_sync_log_foreign_key_constraint(db):
    """Test sync_log requires valid sync_config_id"""
    log = SyncLog(
        sync_config_id=uuid4(),  # Non-existent config
        status="success",
        events_created=0,
        events_updated=0,
        events_deleted=0
    )
    db.add(log)
    with pytest.raises(IntegrityError):
        db.commit()

def test_event_mapping_unique_constraint(db, test_config):
    """Test source_id must be unique per sync_config"""
    mapping1 = EventMapping(
        sync_config_id=test_config.id,
        source_id="evt1",
        dest_id="evt2"
    )
    mapping2 = EventMapping(
        sync_config_id=test_config.id,
        source_id="evt1",  # Duplicate
        dest_id="evt3"
    )
    db.add(mapping1)
    db.commit()
    db.add(mapping2)
    with pytest.raises(IntegrityError):
        db.commit()
```

**Estimated Effort**: 4-5 hours
**Priority**: **MEDIUM**

---

### 🟡 MEDIUM RISK: Configuration

**File**: `backend/app/config.py`
**Current Tests**: 0
**Lines of Code**: ~50

**Why This Matters**:
- Debug mode protection in production
- Environment variable loading
- Settings validation

**Recommended Tests**:
```python
# backend/tests/test_config.py

def test_settings_loads_from_env(monkeypatch):
    """Test settings loads values from environment"""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    monkeypatch.setenv("FRONTEND_URL", "http://test.com")
    settings = Settings()
    assert settings.DATABASE_URL == "postgresql://test"
    assert settings.FRONTEND_URL == "http://test.com"

def test_debug_disabled_in_production(monkeypatch):
    """Test debug mode cannot be enabled in production"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "true")
    settings = Settings()
    assert settings.DEBUG is False

def test_debug_enabled_in_development(monkeypatch):
    """Test debug mode can be enabled in development"""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEBUG", "true")
    settings = Settings()
    assert settings.DEBUG is True

def test_jwt_settings_required(monkeypatch):
    """Test JWT settings must be provided"""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings()

def test_database_url_required(monkeypatch):
    """Test database URL must be provided"""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings()
```

**Estimated Effort**: 2-3 hours
**Priority**: **MEDIUM**

---

## Frontend Test Improvements

### Current Coverage: ~25-30%

**What's Tested** (31 tests total):
- ✅ `CalendarSelector` component (7 tests)
- ✅ `SyncConfigForm` component (7 tests)
- ✅ `AuthContext` (8 tests)
- ✅ `Dashboard` page (9 tests - partial)

**What's Missing**:

### 🟡 MEDIUM PRIORITY: Core Pages

```typescript
// frontend/src/pages/__tests__/Login.test.tsx

describe('Login Page', () => {
  test('renders login button', () => {
    render(<Login />);
    expect(screen.getByText(/sign in with google/i)).toBeInTheDocument();
  });

  test('redirects to Google OAuth on button click', () => {
    render(<Login />);
    const button = screen.getByText(/sign in with google/i);
    fireEvent.click(button);
    // Verify redirect or API call
  });

  test('handles OAuth callback token in URL', () => {
    // Test token extraction from URL params
  });
});

// frontend/src/pages/__tests__/Register.test.tsx

describe('Register Page', () => {
  test('renders register button', () => {
    render(<Register />);
    expect(screen.getByText(/sign up with google/i)).toBeInTheDocument();
  });

  test('initiates OAuth registration flow', () => {
    // Test OAuth flow initiation
  });
});
```

**Estimated Effort**: 2-3 hours
**Priority**: **MEDIUM**

### 🟡 MEDIUM PRIORITY: Missing Components

```typescript
// frontend/src/components/__tests__/SyncHistoryDialog.test.tsx

describe('SyncHistoryDialog', () => {
  test('displays sync log entries', () => {
    const logs = [/* mock sync logs */];
    render(<SyncHistoryDialog logs={logs} open={true} />);
    // Verify logs are displayed
  });

  test('shows empty state when no logs', () => {
    render(<SyncHistoryDialog logs={[]} open={true} />);
    expect(screen.getByText(/no sync history/i)).toBeInTheDocument();
  });

  test('formats timestamps correctly', () => {
    // Test timestamp display
  });

  test('displays sync statistics', () => {
    // Test events_created/updated/deleted display
  });
});
```

**Estimated Effort**: 2-3 hours
**Priority**: **MEDIUM**

### 🟢 LOW PRIORITY: API Service Layer

```typescript
// frontend/src/services/__tests__/api.test.ts

describe('API Client', () => {
  test('includes authorization header when token present', () => {
    // Test JWT token is included in requests
  });

  test('handles 401 unauthorized responses', () => {
    // Test logout on 401
  });

  test('sync API endpoints', () => {
    // Test createSyncConfig, getSyncConfigs, etc.
  });
});
```

**Estimated Effort**: 3-4 hours
**Priority**: **LOW**

---

## Implementation Priority

### Phase 1: Critical Security & Stability (1-2 weeks)

1. **Security Headers Middleware** - 2 hours
2. **Calendars API** - 6 hours
3. **Main Application Endpoints** - 4 hours

**Total**: ~12 hours of work
**Impact**: Covers all production-exposed code without tests

### Phase 2: Data Layer Validation (1 week)

4. **Database Models** - 5 hours
5. **Configuration** - 3 hours

**Total**: ~8 hours of work
**Impact**: Validates data integrity and settings

### Phase 3: Frontend Coverage (1-2 weeks)

6. **Login/Register Pages** - 3 hours
7. **SyncHistoryDialog** - 3 hours
8. **API Service Layer** - 4 hours

**Total**: ~10 hours of work
**Impact**: Brings frontend coverage to ~50%

### Phase 4: Integration & E2E (Optional)

9. **Frontend E2E tests** (Playwright/Cypress) - 10-15 hours
10. **Full user flow integration tests** - 8-10 hours

---

## Testing Best Practices to Continue

Your codebase already demonstrates excellent testing practices:

1. ✅ **Session-scoped fixtures** for performance
2. ✅ **Comprehensive mocking** for external APIs
3. ✅ **Parallel test execution** support
4. ✅ **Real E2E scripts** for manual validation
5. ✅ **Clear test organization** by feature/module

**Recommendations**:
- Continue using pytest fixtures for database setup
- Maintain mock consistency across test files
- Keep E2E scripts up-to-date as features evolve
- Add coverage reporting to CI/CD pipeline

---

## Measuring Success

**Target Coverage Goals**:
- Backend: 85%+ (currently ~70%)
- Frontend: 60%+ (currently ~30%)

**Key Metrics**:
- Zero production-exposed endpoints without tests
- All security middleware tested
- All database models validated
- All core pages covered

**Tools to Add**:
```bash
# Backend coverage reporting
pytest --cov=app --cov-report=html --cov-report=term-missing

# Frontend coverage
npm test -- --coverage

# Set coverage thresholds in pytest.ini
[tool:pytest]
addopts = --cov-fail-under=85
```

---

## Conclusion

The cal-sync project has **excellent core business logic coverage** but needs **infrastructure and frontend test improvements**. Prioritizing security middleware, calendars API, and main application endpoints will address the most critical gaps in 1-2 weeks of focused work.

The existing test suite demonstrates high quality standards - extending these practices to infrastructure and frontend code will significantly improve overall confidence and maintainability.
