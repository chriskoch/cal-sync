from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api import auth, oauth, calendars, sync
from app.middleware import SecurityHeadersMiddleware
from app.core.scheduler import get_scheduler
from contextlib import asynccontextmanager
import os
import logging

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Starts scheduler on startup, shuts down on termination.
    """
    # Startup: Initialize and start scheduler
    print("=" * 80)
    print("LIFESPAN STARTUP: Beginning scheduler initialization")
    print("=" * 80)
    logger.info("Starting application lifespan...")
    scheduler = get_scheduler()
    print(f"LIFESPAN: Got scheduler instance: {scheduler}")
    scheduler.start()
    print("LIFESPAN: Scheduler started")

    # Load all auto-sync jobs from database
    db = SessionLocal()
    try:
        print("LIFESPAN: Loading jobs from database")
        scheduler.load_all_jobs_from_db(db)
        print("LIFESPAN: Jobs loaded successfully")
    finally:
        db.close()

    logger.info("Application startup complete")
    print("=" * 80)
    print("LIFESPAN STARTUP: Complete")
    print("=" * 80)

    yield

    # Shutdown: Stop scheduler gracefully
    print("=" * 80)
    print("LIFESPAN SHUTDOWN: Beginning")
    print("=" * 80)
    logger.info("Shutting down application...")
    scheduler.shutdown(wait=True)
    logger.info("Application shutdown complete")
    print("LIFESPAN SHUTDOWN: Complete")


# Create FastAPI app
app = FastAPI(
    title="Calendar Sync API",
    description="Multi-tenant SaaS for syncing Google Calendar events",
    version="0.8.3",
    debug=settings.debug,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:3001", "http://localhost:3033"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Mount static files (frontend build) if directory exists
static_dir = os.path.join(os.path.dirname(__file__), "../static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Register API routers with /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(oauth.router, prefix="/api")
app.include_router(calendars.router, prefix="/api")
app.include_router(sync.router, prefix="/api")


@app.get("/")
async def read_root():
    """Serve frontend at root."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    # Fallback to API info if static files don't exist (development mode)
    return {"message": "Calendar Sync API", "version": "0.8.3"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve React SPA for all non-API routes."""
    # Skip API routes (shouldn't happen due to router order)
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)

    # Serve static files
    static_file = os.path.join(static_dir, full_path)
    if os.path.exists(static_file) and os.path.isfile(static_file):
        return FileResponse(static_file)

    # Fallback to index.html for client-side routing
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Application not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
