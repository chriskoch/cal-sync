# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-01-04

### Added
- **Automatic Scheduled Syncs (Major Feature)**
  - APScheduler 3.10.4 integration with AsyncIOScheduler for FastAPI compatibility
  - Cron-based scheduling with timezone support (pytz)
  - In-memory job store with automatic database reload on startup
  - Thread pool executor for parallel job execution (max 5 concurrent syncs)
  - Per-config scheduling with auto_sync_enabled flag, cron expression, and timezone
  - FastAPI lifespan context manager for graceful scheduler startup/shutdown
  - Comprehensive validation for cron expressions (croniter) and IANA timezones (pytz)
  - Job management: automatic replacement on update, missed run coalescing, concurrent run prevention
  - Integration with existing sync infrastructure (reuses run_sync_task)
  - Error handling and logging for missing configs, inactive configs, and missing credentials

- **Database Schema Updates**
  - New `auto_sync_enabled` boolean field (default: False, indexed)
  - New `auto_sync_cron` string field for cron expressions (e.g., "0 */6 * * *")
  - New `auto_sync_timezone` string field for IANA timezone (default: "UTC")
  - Database migration: `93a33b780cdd_add_auto_sync_scheduling_fields.py`

- **API Enhancements**
  - Auto-sync fields in POST/PATCH /sync/config endpoints
  - Pydantic model_validator for cross-field validation (auto_sync_enabled requires auto_sync_cron)
  - Scheduler integration in create/update/delete config endpoints
  - Automatic job scheduling/rescheduling/removal based on config changes

- **Frontend Features**
  - Auto-sync toggle in SyncConfigForm
  - Cron expression input with examples and validation
  - Timezone selector (UTC, America/New_York, Europe/London, Asia/Tokyo, Australia/Sydney)
  - Helper link to https://crontab.cronhub.io/ for cron expression builder
  - Auto-sync status displayed on Dashboard with Schedule icon
  - Support for auto-sync in both one-way and bi-directional sync configs

- **Testing**
  - 26 new unit tests in `backend/tests/test_scheduler.py`
    - Cron validation tests (2)
    - Timezone validation tests (2)
    - Scheduler lifecycle tests (7)
    - Job management tests (6)
    - Scheduled sync job tests (5)
    - Singleton pattern tests (2)
    - Database loading tests (2)
  - 17 new integration tests in `backend/tests/test_sync_api_scheduling.py`
    - Create config with auto-sync (7 tests)
    - Update config with auto-sync (6 tests)
    - Delete config with auto-sync (2 tests)
    - Response format validation (2 tests)
  - 100% code coverage on scheduler module
  - Total: 154 passing tests (127 backend + 27 frontend), up from 128 tests

### Changed
- **Documentation**
  - Updated README.md with auto-sync scheduler feature
  - Updated CLAUDE.md with comprehensive scheduler documentation
  - Updated test counts throughout documentation (154 tests total)
  - Removed "manual execution only" limitation
  - Moved "Automatic scheduled syncs" from Future Enhancements to Completed features

- **Dependencies**
  - Added APScheduler==3.10.4
  - Added croniter==2.0.1
  - Added pytz==2024.1

### Improved
- **Architecture**
  - Stateless scheduler design with database reload on startup
  - Timezone-aware cron scheduling per sync config
  - Prevents job overlaps with max_instances=1 configuration
  - Graceful startup and shutdown integration with FastAPI
  - Minimal code duplication by reusing existing sync_engine functions

## [0.7.1] - 2026-01-04

### Added
- **Open Source Preparation**
  - MIT License with copyright
  - Comprehensive CONTRIBUTING.md with development workflow and PR process
  - CODE_OF_CONDUCT.md using Contributor Covenant v2.1
  - GitHub issue templates (bug reports, feature requests)
  - GitHub pull request template with testing checklist
  - GitHub Actions CI/CD workflows for automated testing
    - Backend tests workflow (pytest with PostgreSQL service)
    - Frontend tests workflow (Vitest, ESLint, TypeScript)
  - Security disclosure process in SECURITY.md
  - README badges for license and CI/CD status

### Changed
- **Infrastructure**
  - Removed GCP Terraform deployment files (focus on Docker-only development)
  - Updated .env.example with Docker Compose defaults
  - Removed competitors analysis file (internal documentation)
- **Documentation**
  - Enhanced README with contributing section and OSS badges
  - Updated SECURITY.md with responsible disclosure email
  - Improved .env.example with better Docker defaults

### Removed
- GCP Terraform configuration (main.tf)
- Terraform state files and .terraform directory
- competitors-features.md (internal competitive analysis)

## [0.7.0] - 2026-01-02

### Added
- **Privacy Mode E2E Testing**
  - New E2E test script: `e2e_test_privacy_one_way.py` - Validates one-way privacy mode (8 steps)
  - New E2E test script: `e2e_test_privacy_bidirectional.py` - Validates bi-directional privacy with different placeholders (10 steps)
  - Comprehensive validation of privacy placeholder text, sensitive data removal, and time preservation
  - Tests privacy maintenance after event updates
  - Direction-specific privacy settings testing for bi-directional sync
- **Documentation**
  - Created `backend/tests/e2e/README.md` with comprehensive E2E test documentation
  - Updated all .md files with privacy test information and code quality improvements

### Changed
- **Code Quality Improvements**
  - Fixed version number consistency (0.7.0 across all endpoints)
  - Replaced `print()` with proper logging in `backend/app/config.py` for production monitoring
  - Extracted duplicated color palette to shared constants file (`frontend/src/constants/colors.ts`)
  - Improved code maintainability by eliminating duplicate color definitions
- **Project Structure**
  - Added `frontend/src/constants/` directory for shared constants
  - Better organization of frontend code

### Improved
- **Test Coverage**
  - Total: 128 passing tests (101 backend + 27 frontend)
  - E2E: 5 comprehensive test scripts with 100% pass rate
  - All tests verified in Docker environment
  - Complete privacy mode validation coverage

## [0.6.2] - 2025-12-20

### Fixed
- **CRITICAL**: Fixed OAuth registration flow redirect issue
  - ProtectedRoute now preserves query parameters when redirecting to login
  - Token extraction from URL now happens before authentication check in AuthContext
  - Prevents token loss during OAuth callback redirect, allowing users to complete registration
  - Removed duplicate token extraction logic and consolidated into single useEffect

## [0.6.1] - 2025-12-20

### Security
- **CRITICAL**: Fixed security vulnerability in OAuth registration flow
  - Registration now rejects attempts for existing users
  - Prevents attackers from overwriting OAuth tokens by gaining access to a victim's Google account
  - Existing users must use the login flow instead of registration

### Fixed
- OAuth registration flow no longer allows updating source tokens for existing users
- Added explicit check to reject registration attempts for emails that already have associated user accounts

## [0.6.0] - 2025-12-20

### Changed
- **BREAKING**: Removed password-based authentication. Now Google OAuth-only.
- Registration and login unified into single Google OAuth flow
- Registered Google account automatically becomes source account
- Removed `/auth/register` and `/auth/token` endpoints
- Removed password hashing (bcrypt) from dependencies
- Updated frontend to use single "Sign in with Google" button
- Removed Register page and Change Password functionality

### Added
- OAuth registration flow (`/oauth/start/register`) - no authentication required
- Automatic source account connection during registration
- JWT token generation after successful OAuth registration
- Test suite optimizations:
  - Session-scoped database fixtures (3-5x faster)
  - Shared mock fixtures for OAuth and Google Calendar API
  - Test utilities module (`test_utils.py`)
  - Parallel test execution support (`pytest-xdist`)
- ESLint configuration for frontend
- Code cleanup and refactoring:
  - Extracted duplicate OAuth token upsert logic
  - Improved error handling
  - Removed unused dependencies

### Fixed
- Foreign key constraint issues in sync engine tests
- Frontend test failures after authentication changes
- TypeScript type errors in test files
- ESLint warnings (replaced `any` types with proper error handling)

### Security
- Removed password storage (no passwords in database)
- OAuth tokens encrypted with Fernet before storage
- Updated security documentation for OAuth-only flow

### Documentation
- Updated README.md for OAuth-only authentication
- Updated CLAUDE.md with new authentication flow
- Updated SECURITY.md to remove password-related sections
- Added backend/tests/README.md with test optimization guide
- Added DEVELOPMENT.md with comprehensive development guide

## [0.5.0] - 2025-12-20

### Removed
- Google reCAPTCHA v3 Enterprise integration
- Password-based authentication endpoints (migrated to OAuth-only in v0.6.0)

### Changed
- Authentication endpoints simplified without reCAPTCHA verification

## [0.4.0] - 2024-12-19

### Added
- Web application with React + Material UI frontend
- FastAPI backend with PostgreSQL database
- Google OAuth Web Application flow
- Calendar selection UI
- Sync configuration management
- Manual sync triggers with detailed results
- Sync history viewer
- Docker Compose for local development

### Changed
- Migrated from CLI to web application
- OAuth flow changed from Desktop OOB to Web Application

## [0.3.0] - 2024-01-15

### Added
- Event mappings table for bidirectional sync tracking
- Content hashing for change detection
- Sync cluster IDs for event relationships

## [0.2.0] - 2024-01-10

### Added
- Idempotent sync mechanism
- Extended properties for event tracking
- Error handling for 410/404 errors

## [0.1.0] - 2024-01-01

### Added
- Initial CLI version
- Basic calendar sync functionality
- Desktop OAuth flow
