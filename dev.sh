#!/bin/bash
# Cal-Sync Local Development Launcher
# One-command setup for local development with hot-reload

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Cal-Sync Local Development Environment${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping all services...${NC}"

    # Kill backend if running
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping backend (PID: $BACKEND_PID)"
        kill $BACKEND_PID 2>/dev/null || true
    fi

    # Kill frontend if running
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping frontend (PID: $FRONTEND_PID)"
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    echo -e "${GREEN}✓ All services stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 1. Check prerequisites
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}"

# 2. Check .env.local
echo -e "${YELLOW}[2/6] Checking environment configuration...${NC}"

if [ ! -f .env.local ]; then
    echo -e "${RED}Error: .env.local not found${NC}"
    echo "Please create .env.local with your secrets:"
    echo "  cp .env.example .env.local"
    echo "  # Edit .env.local and add your OAuth credentials"
    exit 1
fi

echo -e "${GREEN}✓ Environment configured${NC}"

# 3. Start PostgreSQL
echo -e "${YELLOW}[3/6] Starting PostgreSQL...${NC}"

if docker ps | grep -q cal-sync-db; then
    echo -e "${GREEN}✓ PostgreSQL already running${NC}"
else
    docker compose up -d db
    echo "Waiting for PostgreSQL to be healthy..."
    sleep 5
    echo -e "${GREEN}✓ PostgreSQL started${NC}"
fi

# 4. Setup backend
echo -e "${YELLOW}[4/6] Setting up backend...${NC}"

cd backend

# Create venv if it doesn't exist
if [ ! -d .venv ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate venv and install dependencies
source .venv/bin/activate
if [ ! -f .venv/.deps_installed ]; then
    echo "Installing Python dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    touch .venv/.deps_installed
fi

# Run migrations
echo "Running database migrations..."
alembic upgrade head > /dev/null 2>&1 || echo -e "${YELLOW}⚠ Migrations may have issues (continuing anyway)${NC}"

echo -e "${GREEN}✓ Backend ready${NC}"

cd ..

# 5. Setup frontend
echo -e "${YELLOW}[5/6] Setting up frontend...${NC}"

cd frontend

if [ ! -d node_modules ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Create frontend .env for local dev
if [ ! -f .env ]; then
    echo "VITE_API_URL=http://localhost:8000/api" > .env
fi

echo -e "${GREEN}✓ Frontend ready${NC}"

cd ..

# 6. Start services
echo -e "${YELLOW}[6/6] Starting development servers...${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  🚀 Services starting...${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}  Backend:  ${NC}http://localhost:8000"
echo -e "${GREEN}  Frontend: ${NC}http://localhost:3033"
echo -e "${GREEN}  API Docs: ${NC}http://localhost:8000/docs"
echo -e "${GREEN}  Database: ${NC}localhost:5433"
echo ""
echo -e "${YELLOW}  Press Ctrl+C to stop all services${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Start backend in background
cd backend
source .venv/bin/activate
# Load environment from .env.local
export $(grep -v '^#' ../.env.local | xargs)
# Override for local dev
export API_URL=http://localhost:8000
export FRONTEND_URL=http://localhost:3033
export DATABASE_URL=postgresql://postgres:postgres@localhost:5433/calsync

uvicorn app.main:app --reload --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 2

# Start frontend in background
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait a bit for frontend to start
sleep 3

echo -e "${GREEN}✓ All services started!${NC}"
echo ""
echo "Logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""

# Show combined logs
tail -f backend.log frontend.log
