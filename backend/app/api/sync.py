from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

from app.database import get_db
from app.models.user import User
from app.models.sync_config import SyncConfig
from app.models.sync_log import SyncLog
from app.api.auth import get_current_user
from app.api.oauth import get_credentials_from_db
from app.core.sync_engine import SyncEngine
from app.config import settings

router = APIRouter(prefix="/sync", tags=["sync"])


class CreateSyncConfigRequest(BaseModel):
    source_calendar_id: str
    dest_calendar_id: str
    sync_lookahead_days: int = 90


class SyncConfigResponse(BaseModel):
    id: str
    source_calendar_id: str
    dest_calendar_id: str
    is_active: bool
    sync_lookahead_days: int
    last_synced_at: datetime = None

    class Config:
        from_attributes = True


class SyncTriggerResponse(BaseModel):
    message: str
    sync_log_id: str


class SyncLogResponse(BaseModel):
    id: str
    events_created: int
    events_updated: int
    events_deleted: int
    status: str
    error_message: str = None
    sync_window_start: datetime
    sync_window_end: datetime
    started_at: datetime
    completed_at: datetime = None

    class Config:
        from_attributes = True


@router.post("/config", response_model=SyncConfigResponse, status_code=status.HTTP_201_CREATED)
def create_sync_config(
    config_data: CreateSyncConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new sync configuration."""
    new_config = SyncConfig(
        user_id=current_user.id,
        source_calendar_id=config_data.source_calendar_id,
        dest_calendar_id=config_data.dest_calendar_id,
        sync_lookahead_days=config_data.sync_lookahead_days,
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)

    return new_config


@router.get("/config", response_model=List[SyncConfigResponse])
def list_sync_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all sync configurations for the current user."""
    configs = db.query(SyncConfig).filter(SyncConfig.user_id == current_user.id).all()
    return configs


@router.post("/trigger/{config_id}", response_model=SyncTriggerResponse)
def trigger_sync(
    config_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger a manual sync for the specified configuration."""
    # Get sync config
    sync_config = db.query(SyncConfig).filter(
        SyncConfig.id == config_id,
        SyncConfig.user_id == current_user.id,
    ).first()

    if not sync_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sync configuration not found",
        )

    if not sync_config.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sync configuration is inactive",
        )

    # Get credentials
    source_creds = get_credentials_from_db(str(current_user.id), "source", db)
    dest_creds = get_credentials_from_db(str(current_user.id), "destination", db)

    if not source_creds or not dest_creds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth credentials not found for source or destination account",
        )

    # Create sync log
    sync_log = SyncLog(
        sync_config_id=sync_config.id,
        status="running",
        sync_window_start=datetime.utcnow(),
        sync_window_end=datetime.utcnow(),
    )
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)

    # Run sync in background
    background_tasks.add_task(
        run_sync_task,
        sync_log_id=str(sync_log.id),
        sync_config_id=str(sync_config.id),
        source_creds=source_creds,
        dest_creds=dest_creds,
        source_calendar_id=sync_config.source_calendar_id,
        dest_calendar_id=sync_config.dest_calendar_id,
        lookahead_days=sync_config.sync_lookahead_days,
    )

    return {
        "message": "Sync started",
        "sync_log_id": str(sync_log.id),
    }


@router.get("/logs/{config_id}", response_model=List[SyncLogResponse])
def get_sync_logs(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get sync history for the specified configuration."""
    # Verify ownership
    sync_config = db.query(SyncConfig).filter(
        SyncConfig.id == config_id,
        SyncConfig.user_id == current_user.id,
    ).first()

    if not sync_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sync configuration not found",
        )

    # Get logs
    logs = db.query(SyncLog).filter(
        SyncLog.sync_config_id == config_id
    ).order_by(SyncLog.started_at.desc()).limit(50).all()

    return logs


def run_sync_task(
    sync_log_id: str,
    sync_config_id: str,
    source_creds,
    dest_creds,
    source_calendar_id: str,
    dest_calendar_id: str,
    lookahead_days: int,
):
    """Background task to run the sync operation."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        sync_engine = SyncEngine(db)

        # Run sync
        result = sync_engine.sync_calendars(
            sync_config_id=sync_config_id,
            source_creds=source_creds,
            dest_creds=dest_creds,
            source_calendar_id=source_calendar_id,
            dest_calendar_id=dest_calendar_id,
            lookahead_days=lookahead_days,
        )

        # Update sync log
        sync_log = db.query(SyncLog).filter(SyncLog.id == sync_log_id).first()
        if sync_log:
            sync_log.events_created = result["created"]
            sync_log.events_updated = result["updated"]
            sync_log.events_deleted = result["deleted"]
            sync_log.status = "success"
            sync_log.completed_at = datetime.utcnow()

        # Update sync config last_synced_at
        sync_config = db.query(SyncConfig).filter(SyncConfig.id == sync_config_id).first()
        if sync_config:
            sync_config.last_synced_at = datetime.utcnow()

        db.commit()

    except Exception as e:
        # Update sync log with error
        sync_log = db.query(SyncLog).filter(SyncLog.id == sync_log_id).first()
        if sync_log:
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.utcnow()
            db.commit()

    finally:
        db.close()
