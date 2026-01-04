# Development Guide

This guide provides information for developers working on the Calendar Sync application.

## Quick Start

### Local Development (Hot-Reload)

**One command to start everything:**
```bash
./dev.sh
```

This launches:
- PostgreSQL (Docker container on port 5433)
- Backend dev server (port 8000) with hot-reload
- Frontend dev server (port 3033) with hot-reload
- Combined logs from both services

Press `Ctrl+C` to stop all services.

### Docker Deployment

```bash
# Build and start
docker build -t cal-sync:latest .
docker compose up -d

# Access at http://localhost:8033
```

### Testing

```bash
# Run backend tests
docker-compose exec backend pytest -v

# Run frontend tests
cd frontend && npm test -- --run

# Run linters
cd frontend && npm run lint
```

## Code Quality

### Linting

**Frontend:**
- ESLint configured with TypeScript support
- Run: `cd frontend && npm run lint`
- Configuration: `frontend/.eslintrc.cjs`
- Max warnings: 50 (configurable in `package.json`)

**Backend:**
- Python syntax checking via IDE/editor
- Type hints recommended for all functions
- Follow PEP 8 style guide

### Testing

**Backend Tests:**
- Framework: pytest
- Location: `backend/tests/`
- Run: `docker-compose exec backend pytest -v`
- Parallel: `docker-compose exec backend pytest -n auto`
- Coverage: `docker-compose exec backend pytest --cov=app --cov-report=html`

**Frontend Tests:**
- Framework: Vitest + React Testing Library
- Location: `frontend/src/**/*.test.tsx`
- Run: `cd frontend && npm test -- --run`
- Watch mode: `cd frontend && npm test`

### Test Best Practices

1. **Use shared fixtures** from `conftest.py` instead of creating new mocks
2. **Use test utilities** for common operations (when available)
3. **Mark tests appropriately** (`@pytest.mark.unit`, `@pytest.mark.integration`)
4. **Keep tests isolated** - each test should be independent
5. **Use descriptive test names** that explain what is being tested

## Authentication Flow

The application uses **Google OAuth-only authentication**:

1. User clicks "Sign in with Google" on login page
2. OAuth flow initiated with `account_type: "register"`
3. After OAuth callback:
   - New user: Creates user record (email from Google)
   - Creates source OAuth token automatically
   - Generates JWT token
   - Redirects to dashboard with JWT in URL
4. User connects destination account (separate OAuth flow)
5. User creates sync configurations

**Key Points:**
- No passwords stored or required
- Registered Google account = source account
- JWT tokens for API authentication (30 min expiry)
- OAuth tokens encrypted in database

## Database Migrations

```bash
# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Review migration file in backend/app/migrations/versions/

# Apply migration
docker-compose exec backend alembic upgrade head

# Rollback migration
docker-compose exec backend alembic downgrade -1
```

## API Development

### Adding New Endpoints

1. Create router function in appropriate file under `backend/app/api/`
2. Add Pydantic models for request/response
3. Add authentication if needed: `current_user: User = Depends(get_current_user)`
4. Add tests in `backend/tests/`
5. Update frontend API client in `frontend/src/services/api.ts`

### Error Handling

- Use FastAPI's `HTTPException` for errors
- Include descriptive error messages
- Log errors for debugging
- Return appropriate HTTP status codes

## Frontend Development

### Component Structure

- **Pages**: Full page components (`pages/`)
- **Components**: Reusable UI components (`components/`)
- **Context**: Global state management (`context/`)
- **Services**: API client and utilities (`services/`)

### State Management

- Use React Context for authentication (`AuthContext`)
- Use component state for local UI state
- Consider lifting state up for shared data

### TypeScript

- All components should be typed
- Use interfaces for props and API responses
- Avoid `any` types (use `unknown` with type guards)
- Enable strict mode in `tsconfig.json`

## Common Tasks

### Add New Syncable Event Field

1. Update `build_payload_from_source()` in `backend/app/core/sync_engine.py`
2. Add to `comparable_keys` in `events_differ()` in same file
3. Add test in `backend/tests/test_sync_engine.py`

### Debug Sync Issues

1. Check sync logs in UI (Dashboard → View History)
2. Check database: `docker-compose exec db psql -U postgres -d calsync`
3. Check backend logs: `docker-compose logs backend`
4. Verify OAuth tokens: `GET /oauth/status`
5. Check event extended properties for `source_id`

### Debugging

**Backend:**
- Logs: `docker-compose logs -f backend`
- Database: `docker-compose exec db psql -U postgres -d calsync`
- Interactive shell: `docker-compose exec backend python`

**Frontend:**
- Browser DevTools console
- React DevTools extension
- Network tab for API calls

## Git Workflow

1. Create feature branch from `main`
2. Make changes with tests
3. Run tests and linters
4. Commit with descriptive messages
5. Push and create pull request

## Port Configuration

**Docker Deployment (default - port 8033):**
- Unified frontend + backend container
- Access at: `http://localhost:8033`
- API docs at: `http://localhost:8033/docs`
- Configured in `.env`: `EXTERNAL_PORT=8033`, `API_URL=http://localhost:8033`, `FRONTEND_URL=http://localhost:8033`

**Local Development (separate ports):**
- Backend: `http://localhost:8000` (uvicorn dev server)
- Frontend: `http://localhost:3033` (Vite dev server)
- Database: `http://localhost:5433` (PostgreSQL)
- Hot-reload enabled for both backend and frontend
- Configured in `.env.local` (see `.env.example` for template)

**To change Docker port:**
1. Edit `.env` file
2. Update `EXTERNAL_PORT=8088` (or your desired port)
3. Update `API_URL=http://localhost:8088`
4. Update `FRONTEND_URL=http://localhost:8088`
5. Update Google OAuth redirect URI: `http://localhost:8088/api/oauth/callback`
6. Restart: `docker compose down && docker compose up -d`

## Environment Variables

The project uses a two-file approach:
- **`.env`** (committed) - Safe defaults for Docker deployment (port 8033)
- **`.env.local`** (git-ignored) - Your secrets and local overrides

Required variables (add to `.env.local`):
- `OAUTH_CLIENT_ID` - Google OAuth client ID
- `OAUTH_CLIENT_SECRET` - Google OAuth client secret
- `JWT_SECRET` - Secret for JWT token signing
- `ENCRYPTION_KEY` - Fernet key for OAuth token encryption

Optional overrides for local development:
- `DATABASE_URL` - PostgreSQL connection string (default: Docker container)
- `API_URL` - Backend URL (default: `http://localhost:8033` for Docker, override to `http://localhost:8000` for local dev)
- `FRONTEND_URL` - Frontend URL (default: `http://localhost:8033` for Docker, override to `http://localhost:3033` for local dev)

**Never commit `.env.local` files!** They contain your secrets.

## Performance

- Use database indexes for frequently queried columns
- Use connection pooling (configured in SQLAlchemy)
- Consider caching for calendar lists
- Optimize sync queries for large datasets

## Security

- Never commit secrets
- Use environment variables for configuration
- Encrypt sensitive data (OAuth tokens)
- Validate all user inputs
- Use HTTPS in production
- Review `SECURITY.md` for best practices

