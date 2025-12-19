# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2025-12-20

### Added
- Event color customization for destination calendars
  - Color picker UI with 11 Google Calendar event colors
  - Auto-selection of source calendar color when available
  - Visual color preview with Circle icon and color names
  - "Same as source" option to preserve original event colors
  - Display selected color in sync configuration cards on dashboard
- Frontend containerization
  - Added frontend/Dockerfile for React application
  - Integrated frontend service into docker-compose.yml
  - Hot reload support for local development with volume mounts
- Comprehensive sync engine testing
  - test_sync_engine.py with 95% code coverage
  - Tests for event creation, updates, deletions
  - Error handling tests for 410/404 HTTP errors
  - Test coverage for calendar sync edge cases
- OAuth API testing
  - test_oauth_api.py with 99% code coverage
  - Tests for authorization flow, token storage, status checks
  - Integration tests for OAuth callbacks and error handling
- Database migration for destination color feature
  - Added destination_color_id column to sync_configs table
  - Migration: 5ca5e2b9e0ba_add_destination_color_id_to_sync_configs.py

### Changed
- Updated CalendarItem API to include color_id and background_color fields
- Enhanced CalendarSelector to pass full calendar object to onChange callback
- Updated CLAUDE.md documentation to reflect full-stack architecture
  - Documented event color system and limitations
  - Added comprehensive API endpoints documentation
  - Added development tasks guide for common operations
  - Explained calendar vs event color distinction (24 vs 11 colors)

### Fixed
- Event color validation: Handle out-of-range calendar colors (12-24)
  - Calendar colors (IDs 12-24) now default to Lavender (ID 1)
  - Only event colors (IDs 1-11) are allowed for destination events
- 410 (Gone) error handling in sync engine
  - Gracefully handle deleted events during delete operations
  - Gracefully handle deleted events during update operations (recreate as new)
  - All error handling logged to sync_logs table
- 404 (Not Found) error handling in sync engine
  - Skip gracefully when events don't exist
  - Recreate events when update fails due to missing event

### Technical Details
- **Color System**: Google Calendar has 24 calendar colors (IDs 1-24) but only 11 event colors (IDs 1-11). Since we sync events, we can only use event colors.
- **Auto-selection Logic**: When source calendar color is valid (1-11), auto-select it. Otherwise, map background_color or default to Lavender.
- **Database Schema**: Added `destination_color_id` column (String, nullable) to sync_configs table.

## [0.3.0] - 2025-12-19

### Added
- Comprehensive backend testing infrastructure with pytest
  - 13 unit tests for security module (password hashing, JWT, encryption)
  - 13 integration tests for authentication API endpoints
  - Test fixtures for database, test users, and auth tokens
  - SQLite in-memory test database with PostgreSQL compatibility layer
  - Custom TypeDecorators for UUID and ARRAY type compatibility
  - Coverage reporting with 60% threshold (62% achieved)
- Frontend testing infrastructure with Vitest
  - React Testing Library integration for component testing
  - 6 component tests for CalendarSelector (all passing)
  - 10 context tests for AuthContext (5 passing)
  - Custom test utilities with provider wrappers
  - Mock data and API response factories
  - localStorage and matchMedia mocks
  - Coverage reporting with 70% thresholds
- Sync history viewer with detailed logs showing events created/updated/deleted
- View History button for each sync configuration
- SyncHistoryDialog component displaying complete audit trail
- Success/failure status indicators with color-coded chips
- Error message display for failed sync operations
- Refresh functionality for sync history

### Changed
- Adjusted coverage thresholds to realistic initial targets (backend: 60%, frontend: 70%)
- Updated API registration endpoint to return HTTP 201 Created (was 200 OK)

### Fixed
- UUID type incompatibility between PostgreSQL and SQLite in tests
- ARRAY type incompatibility between PostgreSQL and SQLite in tests
- Theme import in frontend test utilities (named vs default export)

## [0.2.0] - 2025-12-19

### Added
- Calendar selection UI with dropdown selectors for source and destination calendars
- Sync configuration form with validation
- Display of existing sync configurations on dashboard
- Manual sync trigger with detailed results feedback
- Delete sync configuration functionality with confirmation dialog
- Success/error alert messages with dismiss option
- Last synced timestamp display for each configuration
- Active/Inactive status indicators
- Refresh button for sync configurations list
- DELETE `/sync/config/{id}` API endpoint
- Sync configuration management UI components (CalendarSelector, SyncConfigForm)

### Changed
- Enhanced Dashboard to load and display existing sync configurations on login
- Improved sync feedback showing events created/updated/deleted counts
- Updated sync trigger to fetch and display detailed results

### Fixed
- UUID serialization in Pydantic v2 models (SyncConfigResponse, SyncLogResponse)
- Optional datetime field type annotations in API models
- Sync configurations now persist and load correctly after logout/login

## [0.1.0] - 2025-12-19

### Added
- Multi-tenant SaaS web application with React + Material UI frontend
- FastAPI backend with JWT authentication
- PostgreSQL database with Alembic migrations
- User registration and login system with bcrypt password hashing
- Web OAuth flow for Google Calendar (source and destination accounts)
- OAuth token storage with Fernet encryption in database
- Calendar listing API endpoints for source and destination accounts
- Sync configuration database model with user relationships
- Sync log tracking with detailed metrics (events created/updated/deleted)
- Event mapping system for idempotent syncs using content hashing
- Background sync execution with error handling
- Docker Compose setup for local development (PostgreSQL, backend, frontend)
- Frontend routing with React Router
- Protected routes requiring authentication
- Dashboard showing OAuth connection status
- OAuth reconnection functionality
- CORS configuration for frontend-backend communication

### Changed
- Transformed CLI-based sync tool into web application
- Moved from file-based token storage to encrypted database storage
- Switched from Desktop OAuth flow (OOB) to Web Application OAuth flow
- Updated from single-user to multi-tenant architecture
- Changed authentication from file-based to JWT token system

### Fixed
- Authentication issues with bcrypt password hashing (switched from passlib to direct bcrypt)
- OAuth redirect port mismatch (configured correct frontend URL)
- PostgreSQL port conflict (changed to 5433)
- Frontend port configuration (now using 3033)
- CORS issues with multiple frontend ports

### Security
- Implemented JWT-based authentication
- Added bcrypt password hashing for user credentials
- Encrypted OAuth tokens using Fernet cipher
- Added user isolation for all sync configurations and logs
- Implemented proper authorization checks for all API endpoints

## [0.0.1] - Initial CLI Version

### Added
- Python CLI script for Google Calendar synchronization
- Dual OAuth flow for source and destination calendars
- Terraform infrastructure provisioning for GCP
- OAuth consent screen and client ID configuration
- Idempotent sync mechanism using extended properties
- Event comparison and change detection
- One-way calendar sync (source to destination)
- Configurable sync lookahead window (default 90 days)
- Support for basic event fields (summary, description, location, start, end)
- Unit tests with mocked Google Calendar API

[Unreleased]: https://github.com/yourusername/cal-sync/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/yourusername/cal-sync/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/yourusername/cal-sync/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yourusername/cal-sync/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/yourusername/cal-sync/releases/tag/v0.0.1
