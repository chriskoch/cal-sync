from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_serializer
from typing import List, Optional
from datetime import datetime
from uuid import UUID
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
    destination_color_id: Optional[str] = None

    # Bi-directional sync options
    enable_bidirectional: bool = False

    # Privacy mode settings
    privacy_mode_enabled: bool = False
    privacy_placeholder_text: str = "Personal appointment"

    # Privacy settings for reverse direction (only if enable_bidirectional=True)
    reverse_privacy_mode_enabled: Optional[bool] = None
    reverse_privacy_placeholder_text: Optional[str] = None


class SyncConfigResponse(BaseModel):
    id: UUID
    source_calendar_id: str
    dest_calendar_id: str
    is_active: bool
    sync_lookahead_days: int
    destination_color_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None

    # Bi-directional sync fields
    sync_direction: str
    paired_config_id: Optional[UUID] = None
    privacy_mode_enabled: bool
    privacy_placeholder_text: Optional[str] = None

    @field_serializer('id', 'paired_config_id')
    def serialize_uuid(self, value: Optional[UUID]) -> Optional[str]:
        return str(value) if value else None

    class Config:
        from_attributes = True


class UpdateSyncConfigRequest(BaseModel):
    """Request model for updating sync configuration settings."""
    privacy_mode_enabled: Optional[bool] = None
    privacy_placeholder_text: Optional[str] = None
    is_active: Optional[bool] = None
    destination_color_id: Optional[str] = None


class SyncTriggerResponse(BaseModel):
    message: str
    sync_log_id: str


class SyncLogResponse(BaseModel):
    id: UUID
    events_created: int
    events_updated: int
    events_deleted: int
    status: str
    error_message: Optional[str] = None
    sync_window_start: datetime
    sync_window_end: datetime
    started_at: datetime
    completed_at: Optional[datetime] = None
    sync_direction: Optional[str] = None  # Direction of this sync

    @field_serializer('id')
    def serialize_id(self, id: UUID) -> str:
        return str(id)

    class Config:
        from_attributes = True


@router.post("/config", response_model=SyncConfigResponse, status_code=status.HTTP_201_CREATED)
def create_sync_config(
    config_data: CreateSyncConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new sync configuration with optional bi-directional support."""
    if config_data.enable_bidirectional:
        # Create A→B config
        config_a_to_b = SyncConfig(
            user_id=current_user.id,
            source_calendar_id=config_data.source_calendar_id,
            dest_calendar_id=config_data.dest_calendar_id,
            sync_lookahead_days=config_data.sync_lookahead_days,
            destination_color_id=config_data.destination_color_id,
            sync_direction="bidirectional_a_to_b",
            privacy_mode_enabled=config_data.privacy_mode_enabled,
            privacy_placeholder_text=config_data.privacy_placeholder_text,
        )
        db.add(config_a_to_b)
        db.flush()  # Get ID before creating reverse

        # Create B→A config (reversed)
        config_b_to_a = SyncConfig(
            user_id=current_user.id,
            source_calendar_id=config_data.dest_calendar_id,  # Reversed
            dest_calendar_id=config_data.source_calendar_id,  # Reversed
            sync_lookahead_days=config_data.sync_lookahead_days,
            destination_color_id=config_data.destination_color_id,
            sync_direction="bidirectional_b_to_a",
            paired_config_id=config_a_to_b.id,  # Link to A→B
            privacy_mode_enabled=config_data.reverse_privacy_mode_enabled if config_data.reverse_privacy_mode_enabled is not None else config_data.privacy_mode_enabled,
            privacy_placeholder_text=config_data.reverse_privacy_placeholder_text or config_data.privacy_placeholder_text,
        )
        db.add(config_b_to_a)
        db.flush()

        # Update A→B with reverse link
        config_a_to_b.paired_config_id = config_b_to_a.id

        db.commit()
        db.refresh(config_a_to_b)
        return config_a_to_b
    else:
        # One-way config (backward compatible)
        new_config = SyncConfig(
            user_id=current_user.id,
            source_calendar_id=config_data.source_calendar_id,
            dest_calendar_id=config_data.dest_calendar_id,
            sync_lookahead_days=config_data.sync_lookahead_days,
            destination_color_id=config_data.destination_color_id,
            sync_direction="one_way",
            privacy_mode_enabled=config_data.privacy_mode_enabled,
            privacy_placeholder_text=config_data.privacy_placeholder_text,
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


@router.patch("/config/{config_id}", response_model=SyncConfigResponse)
def update_sync_config(
    config_id: str,
    update_data: UpdateSyncConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update sync configuration settings."""
    sync_config = db.query(SyncConfig).filter(
        SyncConfig.id == config_id,
        SyncConfig.user_id == current_user.id,
    ).first()

    if not sync_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sync configuration not found",
        )

    # Update fields if provided
    if update_data.privacy_mode_enabled is not None:
        sync_config.privacy_mode_enabled = update_data.privacy_mode_enabled
    if update_data.privacy_placeholder_text is not None:
        sync_config.privacy_placeholder_text = update_data.privacy_placeholder_text
    if update_data.is_active is not None:
        sync_config.is_active = update_data.is_active
    if update_data.destination_color_id is not None:
        sync_config.destination_color_id = update_data.destination_color_id

    db.commit()
    db.refresh(sync_config)
    return sync_config


@router.post("/trigger/{config_id}", response_model=SyncTriggerResponse)
def trigger_sync(
    config_id: str,
    trigger_both_directions: bool = False,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger a manual sync with optional bi-directional execution."""
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
    source_creds = get_credentials_from_db(current_user.id, "source", db)
    dest_creds = get_credentials_from_db(current_user.id, "destination", db)

    if not source_creds or not dest_creds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth credentials not found for source or destination account",
        )

    # Create sync log for primary direction
    sync_log = SyncLog(
        sync_config_id=sync_config.id,
        status="running",
        sync_window_start=datetime.utcnow(),
        sync_window_end=datetime.utcnow(),
        sync_direction=sync_config.sync_direction,
    )
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)

    # Run primary sync in background
    background_tasks.add_task(
        run_sync_task,
        sync_log_id=str(sync_log.id),
        sync_config_id=str(sync_config.id),
        source_creds=source_creds,
        dest_creds=dest_creds,
        source_calendar_id=sync_config.source_calendar_id,
        dest_calendar_id=sync_config.dest_calendar_id,
        lookahead_days=sync_config.sync_lookahead_days,
        destination_color_id=sync_config.destination_color_id,
        privacy_mode_enabled=sync_config.privacy_mode_enabled,
        privacy_placeholder_text=sync_config.privacy_placeholder_text,
        sync_direction=sync_config.sync_direction,
        paired_config_id=str(sync_config.paired_config_id) if sync_config.paired_config_id else None,
    )

    # If bi-directional and user wants both, trigger reverse too
    if trigger_both_directions and sync_config.paired_config_id:
        paired_config = db.query(SyncConfig).filter(
            SyncConfig.id == sync_config.paired_config_id
        ).first()

        if paired_config and paired_config.is_active:
            # Create sync log for reverse direction
            paired_sync_log = SyncLog(
                sync_config_id=paired_config.id,
                status="running",
                sync_window_start=datetime.utcnow(),
                sync_window_end=datetime.utcnow(),
                sync_direction=paired_config.sync_direction,
            )
            db.add(paired_sync_log)
            db.commit()
            db.refresh(paired_sync_log)

            # Run reverse sync (SWAP credentials for reverse direction)
            background_tasks.add_task(
                run_sync_task,
                sync_log_id=str(paired_sync_log.id),
                sync_config_id=str(paired_config.id),
                source_creds=dest_creds,  # Swapped: reverse source is from destination account
                dest_creds=source_creds,  # Swapped: reverse dest is from source account
                source_calendar_id=paired_config.source_calendar_id,
                dest_calendar_id=paired_config.dest_calendar_id,
                lookahead_days=paired_config.sync_lookahead_days,
                destination_color_id=paired_config.destination_color_id,
                privacy_mode_enabled=paired_config.privacy_mode_enabled,
                privacy_placeholder_text=paired_config.privacy_placeholder_text,
                sync_direction=paired_config.sync_direction,
                paired_config_id=str(paired_config.paired_config_id) if paired_config.paired_config_id else None,
            )

    return {
        "message": "Sync started",
        "sync_log_id": str(sync_log.id),
    }


@router.delete("/config/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sync_config(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a sync configuration."""
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

    # Delete sync logs first (foreign key constraint)
    db.query(SyncLog).filter(SyncLog.sync_config_id == config_id).delete()

    # Delete sync config
    db.delete(sync_config)
    db.commit()


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
    destination_color_id: Optional[str] = None,
    privacy_mode_enabled: bool = False,
    privacy_placeholder_text: str = "Personal appointment",
    sync_direction: str = "one_way",
    paired_config_id: Optional[str] = None,
):
    """Background task to run the sync operation with bi-directional support."""
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
            destination_color_id=destination_color_id,
            privacy_mode_enabled=privacy_mode_enabled,
            privacy_placeholder_text=privacy_placeholder_text,
            sync_direction=sync_direction,
            paired_config_id=paired_config_id,
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
