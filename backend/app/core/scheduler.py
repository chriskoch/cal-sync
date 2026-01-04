"""
APScheduler-based automatic sync scheduler.

This module provides a lightweight, in-process scheduler for automatic calendar syncing
using cron expressions. Jobs are stored in memory and reloaded from the database on startup.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from croniter import croniter
from sqlalchemy.orm import Session
from typing import Optional
import logging
import pytz
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class SyncScheduler:
    """
    Manages APScheduler for automatic calendar syncs.

    Architecture:
    - AsyncIOScheduler for FastAPI compatibility
    - In-memory job store (stateless, reloads from DB on startup)
    - Thread pool executor for parallel job execution
    - Job ID pattern: f"sync_{config_id}"
    """

    def __init__(self):
        """Initialize scheduler (not started)."""
        self.scheduler = None
        self._running = False

    def start(self):
        """Start scheduler with configuration."""
        # Configure APScheduler
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=5)  # Max 5 concurrent syncs
        }
        job_defaults = {
            'coalesce': True,  # Combine missed runs into one
            'max_instances': 1,  # Prevent concurrent runs of same job
            'misfire_grace_time': 300  # 5 minute grace period for misfired jobs
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.UTC  # Internal timezone (jobs can have their own)
        )

        self.scheduler.start()
        self._running = True
        logger.info("APScheduler started successfully")

    def shutdown(self, wait: bool = True):
        """Gracefully shutdown scheduler."""
        if self.scheduler and self._running:
            self.scheduler.shutdown(wait=wait)
            self._running = False
            logger.info("APScheduler shutdown complete")

    def add_job(self, config_id: str, user_id: str, cron_expr: str, timezone_str: str):
        """
        Add/update scheduled job for sync config.

        Args:
            config_id: UUID of sync config
            user_id: UUID of user (for credential lookup)
            cron_expr: Cron expression (e.g., "0 */6 * * *")
            timezone_str: IANA timezone (e.g., "America/New_York")
        """
        if not self.scheduler or not self._running:
            logger.warning("Scheduler not running, cannot add job")
            return

        job_id = f"sync_{config_id}"

        # Parse timezone
        try:
            tz = pytz.timezone(timezone_str)
        except pytz.UnknownTimeZoneError:
            logger.error(f"Invalid timezone: {timezone_str}, using UTC")
            tz = pytz.UTC

        # Create cron trigger
        trigger = CronTrigger.from_crontab(cron_expr, timezone=tz)

        # Replace existing job or add new
        self.scheduler.add_job(
            func=scheduled_sync_job,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            args=[config_id, user_id],
            name=f"Sync {config_id}"
        )

        logger.info(f"Scheduled job {job_id} with cron '{cron_expr}' in {timezone_str}")

    def remove_job(self, config_id: str):
        """Remove scheduled job for sync config."""
        if not self.scheduler or not self._running:
            return

        job_id = f"sync_{config_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed scheduled job {job_id}")
        except Exception as e:
            logger.debug(f"Job {job_id} not found (may not exist): {e}")

    def load_all_jobs_from_db(self, db: Session):
        """
        Load all active auto-sync configs from database and schedule them.
        Called on application startup.
        """
        from app.models.sync_config import SyncConfig

        # Query all configs with auto-sync enabled
        configs = db.query(SyncConfig).filter(
            SyncConfig.is_active == True,
            SyncConfig.auto_sync_enabled == True,
            SyncConfig.auto_sync_cron.isnot(None)
        ).all()

        logger.info(f"Loading {len(configs)} auto-sync jobs from database")

        for config in configs:
            try:
                self.add_job(
                    config_id=str(config.id),
                    user_id=str(config.user_id),
                    cron_expr=config.auto_sync_cron,
                    timezone_str=config.auto_sync_timezone
                )
            except Exception as e:
                logger.error(f"Failed to schedule job for config {config.id}: {e}")

        logger.info(f"Successfully loaded {len(self.scheduler.get_jobs())} scheduled jobs")


# Global scheduler instance
_scheduler_instance: Optional[SyncScheduler] = None


def get_scheduler() -> SyncScheduler:
    """Get global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SyncScheduler()
    return _scheduler_instance


def scheduled_sync_job(config_id: str, user_id: str):
    """
    Job function executed by APScheduler.
    Wraps run_sync_task with database session management.

    Args:
        config_id: UUID string of sync config
        user_id: UUID string of user
    """
    from app.database import SessionLocal
    from app.models.sync_config import SyncConfig
    from app.models.sync_log import SyncLog
    from app.api.oauth import get_credentials_from_db
    from app.api.sync import run_sync_task

    logger.info(f"Starting scheduled sync for config {config_id}")

    db = SessionLocal()
    try:
        # Fetch sync config
        sync_config = db.query(SyncConfig).filter(
            SyncConfig.id == config_id,
            SyncConfig.is_active == True
        ).first()

        if not sync_config:
            logger.warning(f"Sync config {config_id} not found or inactive, skipping")
            return

        # Get OAuth credentials (user_id must be UUID object, not string)
        user_uuid = uuid.UUID(user_id)
        source_creds = get_credentials_from_db(user_uuid, "source", db)
        dest_creds = get_credentials_from_db(user_uuid, "destination", db)

        if not source_creds or not dest_creds:
            logger.error(f"OAuth credentials not found for user {user_id}")
            # Create failed sync log
            failed_log = SyncLog(
                sync_config_id=sync_config.id,
                status="failed",
                error_message="OAuth credentials not found",
                sync_window_start=datetime.utcnow(),
                sync_window_end=datetime.utcnow(),
                sync_direction=sync_config.sync_direction,
                completed_at=datetime.utcnow()
            )
            db.add(failed_log)
            db.commit()
            return

        # Create sync log
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

        # Execute sync (reuse existing function)
        run_sync_task(
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

        logger.info(f"Completed scheduled sync for config {config_id}")

    except Exception as e:
        logger.error(f"Scheduled sync failed for config {config_id}: {e}")
        # run_sync_task already handles error logging to sync_log
    finally:
        db.close()


def validate_cron_expression(cron_expr: str) -> bool:
    """
    Validate cron expression using croniter.

    Returns:
        True if valid, False otherwise
    """
    try:
        croniter(cron_expr)
        return True
    except (ValueError, KeyError):
        return False


def validate_timezone(timezone_str: str) -> bool:
    """
    Validate IANA timezone string.

    Returns:
        True if valid, False otherwise
    """
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.UnknownTimeZoneError:
        return False
