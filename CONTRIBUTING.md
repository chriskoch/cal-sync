# Contributing to Cal-Sync

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites
- Docker Desktop installed
- Git installed
- Basic knowledge of Python (FastAPI) and TypeScript (React)

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/chriskoch/cal-sync.git
   cd cal-sync
   ```

2. Copy environment template:
   ```bash
   cp .env.example .env
   ```

3. Set up Google OAuth credentials:
   - Visit [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create OAuth 2.0 Client ID
   - Add to `.env` file

4. Start all services:
   ```bash
   docker compose up
   ```

5. Access the application:
   - Frontend: http://localhost:3033
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs

## Development Workflow

### Branch Naming
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation updates

### Commit Messages
We use conventional commits:
- `feat: add new feature`
- `fix: resolve bug`
- `docs: update documentation`
- `test: add tests`
- `refactor: code refactoring`

### Code Style
- **Backend (Python)**: Follow PEP 8, use Black formatter
- **Frontend (TypeScript)**: Follow ESLint rules in project

## Testing Requirements

All pull requests must pass tests:

### Backend Tests
```bash
docker compose exec backend pytest -v
```

Expected: 101+ tests passing with >90% coverage

### Frontend Tests
```bash
cd frontend
npm test -- --run
```

Expected: All tests passing

### Linting
```bash
cd frontend
npm run lint
```

Expected: No errors

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch from `dev`
3. **Make** your changes with tests
4. **Run** all tests locally
5. **Commit** with conventional commit messages
6. **Push** to your fork
7. **Submit** pull request to `dev` branch

### PR Description Template
- What does this PR do?
- Why is this change needed?
- How was it tested?
- Any breaking changes?

## Code Review

- PRs are reviewed by maintainers
- Please respond to feedback within 1 week
- Approval from at least 1 maintainer required
- All tests must pass before merge

## Questions?

- Open a [GitHub Discussion](https://github.com/chriskoch/cal-sync/discussions)
- Or file an [issue](https://github.com/chriskoch/cal-sync/issues)

Thank you for contributing!
