# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
