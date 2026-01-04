"""
Unit tests for the scheduler module.

Tests the APScheduler integration, job management, and validation functions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import uuid

from app.core.scheduler import (
    SyncScheduler,
    get_scheduler,
    validate_cron_expression,
    validate_timezone,
    scheduled_sync_job,
)


class TestCronValidation:
    """Test cron expression validation."""

    def test_valid_cron_expressions(self):
        """Valid cron expressions should return True."""
        assert validate_cron_expression("0 */6 * * *") is True  # Every 6 hours
        assert validate_cron_expression("0 0 * * *") is True    # Daily at midnight
        assert validate_cron_expression("*/15 * * * *") is True # Every 15 minutes
        assert validate_cron_expression("0 9 * * 1-5") is True  # Weekdays at 9am
        assert validate_cron_expression("30 2 1 * *") is True   # Monthly at 2:30am

    def test_invalid_cron_expressions(self):
        """Invalid cron expressions should return False."""
        assert validate_cron_expression("invalid") is False
        assert validate_cron_expression("") is False
        assert validate_cron_expression("0 0 0 0 0") is False  # Invalid day/month
        assert validate_cron_expression("60 * * * *") is False  # Invalid minute
        assert validate_cron_expression("a b c d e") is False  # Non-numeric


class TestTimezoneValidation:
    """Test timezone validation."""

    def test_valid_timezones(self):
        """Valid IANA timezones should return True."""
        assert validate_timezone("UTC") is True
        assert validate_timezone("America/New_York") is True
        assert validate_timezone("Europe/London") is True
        assert validate_timezone("Asia/Tokyo") is True
        assert validate_timezone("Australia/Sydney") is True

    def test_invalid_timezones(self):
        """Invalid timezone strings should return False."""
        assert validate_timezone("Invalid/Zone") is False
        assert validate_timezone("") is False
        assert validate_timezone("America/Invalid") is False
        assert validate_timezone("Not/A/Timezone") is False


class TestSyncScheduler:
    """Test scheduler lifecycle and job management."""

    def test_scheduler_initialization(self):
        """Scheduler should initialize without starting."""
        scheduler = SyncScheduler()
        assert scheduler.scheduler is None
        assert scheduler._running is False

    def test_scheduler_start(self):
        """Starting scheduler should configure and start APScheduler."""
        scheduler = SyncScheduler()
        scheduler.start()

        assert scheduler.scheduler is not None
        assert scheduler._running is True
        assert scheduler.scheduler.running is True

        # Cleanup
        scheduler.shutdown(wait=False)

    def test_scheduler_shutdown(self):
        """Shutting down scheduler should stop APScheduler."""
        scheduler = SyncScheduler()
        scheduler.start()
        scheduler.shutdown(wait=False)

        assert scheduler._running is False
        # Don't check scheduler.running as it's async and may not be False immediately

    def test_scheduler_shutdown_without_start(self):
        """Shutting down non-started scheduler should not raise error."""
        scheduler = SyncScheduler()
        scheduler.shutdown(wait=False)  # Should not raise

    @patch('app.core.scheduler.scheduled_sync_job')
    def test_add_job(self, mock_job_func):
        """Adding a job should create scheduler job with correct parameters."""
        scheduler = SyncScheduler()
        scheduler.start()

        config_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        cron_expr = "0 */6 * * *"
        timezone_str = "America/New_York"

        scheduler.add_job(config_id, user_id, cron_expr, timezone_str)

        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == f"sync_{config_id}"
        assert jobs[0].name == f"Sync {config_id}"

        # Cleanup
        scheduler.shutdown(wait=False)

    @patch('app.core.scheduler.scheduled_sync_job')
    def test_add_job_replaces_existing(self, mock_job_func):
        """Adding a job with same ID should replace existing job."""
        scheduler = SyncScheduler()
        scheduler.start()

        config_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Add job with first cron
        scheduler.add_job(config_id, user_id, "0 */6 * * *", "UTC")
        assert len(scheduler.scheduler.get_jobs()) == 1

        # Add job with same ID but different cron
        scheduler.add_job(config_id, user_id, "0 0 * * *", "UTC")
        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1  # Still only 1 job

        # Cleanup
        scheduler.shutdown(wait=False)

    def test_add_job_with_invalid_timezone_uses_utc(self):
        """Adding job with invalid timezone should fall back to UTC."""
        scheduler = SyncScheduler()
        scheduler.start()

        config_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Should not raise error, should use UTC as fallback
        scheduler.add_job(config_id, user_id, "0 */6 * * *", "Invalid/Timezone")

        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1

        # Cleanup
        scheduler.shutdown(wait=False)

    def test_add_job_when_not_running(self):
        """Adding job when scheduler not running should log warning and do nothing."""
        scheduler = SyncScheduler()
        # Don't start scheduler

        config_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        scheduler.add_job(config_id, user_id, "0 */6 * * *", "UTC")
        # Should not raise error, just log warning

    @patch('app.core.scheduler.scheduled_sync_job')
    def test_remove_job(self, mock_job_func):
        """Removing a job should delete it from scheduler."""
        scheduler = SyncScheduler()
        scheduler.start()

        config_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Add job
        scheduler.add_job(config_id, user_id, "0 */6 * * *", "UTC")
        assert len(scheduler.scheduler.get_jobs()) == 1

        # Remove job
        scheduler.remove_job(config_id)
        assert len(scheduler.scheduler.get_jobs()) == 0

        # Cleanup
        scheduler.shutdown(wait=False)

    def test_remove_nonexistent_job(self):
        """Removing non-existent job should not raise error."""
        scheduler = SyncScheduler()
        scheduler.start()

        # Should not raise error
        scheduler.remove_job(str(uuid.uuid4()))

        # Cleanup
        scheduler.shutdown(wait=False)

    def test_remove_job_when_not_running(self):
        """Removing job when scheduler not running should do nothing."""
        scheduler = SyncScheduler()
        # Don't start scheduler

        scheduler.remove_job(str(uuid.uuid4()))
        # Should not raise error

    @patch('app.core.scheduler.scheduled_sync_job')
    def test_load_jobs_from_database(self, mock_job_func, db, test_user):
        """Loading jobs from database should schedule all active auto-sync configs."""
        from app.models.sync_config import SyncConfig

        # Create configs with auto-sync enabled
        config1 = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            is_active=True,
            auto_sync_enabled=True,
            auto_sync_cron="0 */6 * * *",
            auto_sync_timezone="UTC"
        )
        config2 = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal3",
            dest_calendar_id="cal4",
            is_active=True,
            auto_sync_enabled=True,
            auto_sync_cron="0 0 * * *",
            auto_sync_timezone="America/New_York"
        )
        db.add_all([config1, config2])
        db.commit()

        scheduler = SyncScheduler()
        scheduler.start()
        scheduler.load_all_jobs_from_db(db)

        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 2

        job_ids = {job.id for job in jobs}
        assert f"sync_{config1.id}" in job_ids
        assert f"sync_{config2.id}" in job_ids

        # Cleanup
        scheduler.shutdown(wait=False)

    @patch('app.core.scheduler.scheduled_sync_job')
    def test_load_jobs_skips_inactive_configs(self, mock_job_func, db, test_user):
        """Loading jobs should skip inactive configs."""
        from app.models.sync_config import SyncConfig

        # Create inactive config
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            is_active=False,  # Inactive
            auto_sync_enabled=True,
            auto_sync_cron="0 */6 * * *",
            auto_sync_timezone="UTC"
        )
        db.add(config)
        db.commit()

        scheduler = SyncScheduler()
        scheduler.start()
        scheduler.load_all_jobs_from_db(db)

        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 0  # Should not schedule inactive config

        # Cleanup
        scheduler.shutdown(wait=False)

    @patch('app.core.scheduler.scheduled_sync_job')
    def test_load_jobs_skips_disabled_auto_sync(self, mock_job_func, db, test_user):
        """Loading jobs should skip configs with auto_sync_enabled=False."""
        from app.models.sync_config import SyncConfig

        # Create config with auto-sync disabled
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            is_active=True,
            auto_sync_enabled=False,  # Disabled
            auto_sync_cron="0 */6 * * *",
            auto_sync_timezone="UTC"
        )
        db.add(config)
        db.commit()

        scheduler = SyncScheduler()
        scheduler.start()
        scheduler.load_all_jobs_from_db(db)

        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 0  # Should not schedule disabled config

        # Cleanup
        scheduler.shutdown(wait=False)

    @patch('app.core.scheduler.scheduled_sync_job')
    def test_load_jobs_skips_configs_without_cron(self, mock_job_func, db, test_user):
        """Loading jobs should skip configs without cron expression."""
        from app.models.sync_config import SyncConfig

        # Create config without cron
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="cal1",
            dest_calendar_id="cal2",
            is_active=True,
            auto_sync_enabled=True,
            auto_sync_cron=None,  # No cron
            auto_sync_timezone="UTC"
        )
        db.add(config)
        db.commit()

        scheduler = SyncScheduler()
        scheduler.start()
        scheduler.load_all_jobs_from_db(db)

        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 0  # Should not schedule config without cron

        # Cleanup
        scheduler.shutdown(wait=False)


class TestGetScheduler:
    """Test global scheduler instance singleton."""

    def test_get_scheduler_returns_singleton(self):
        """get_scheduler should return same instance."""
        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()

        assert scheduler1 is scheduler2

    def test_get_scheduler_creates_instance_on_first_call(self):
        """get_scheduler should create instance on first call."""
        # Clear singleton
        import app.core.scheduler
        app.core.scheduler._scheduler_instance = None

        scheduler = get_scheduler()
        assert scheduler is not None
        assert isinstance(scheduler, SyncScheduler)


class TestScheduledSyncJob:
    """Test the scheduled sync job function."""

    @patch('app.api.sync.run_sync_task')
    @patch('app.api.oauth.get_credentials_from_db')
    @patch('app.database.SessionLocal')
    def test_scheduled_job_success(self, mock_session_local, mock_get_creds, mock_run_sync, db, test_user):
        """Test successful scheduled sync execution."""
        from app.models.sync_config import SyncConfig

        # Mock SessionLocal to return test db session
        mock_session_local.return_value = db

        # Create test config
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source_cal",
            dest_calendar_id="dest_cal",
            is_active=True,
            auto_sync_enabled=True,
            auto_sync_cron="0 */6 * * *"
        )
        db.add(config)
        db.commit()

        # Mock credentials
        mock_creds = Mock()
        mock_get_creds.return_value = mock_creds

        # Execute job
        scheduled_sync_job(str(config.id), str(test_user.id))

        # Verify run_sync_task was called
        assert mock_run_sync.called
        assert mock_get_creds.call_count == 2  # Called for source and dest

    @patch('app.api.oauth.get_credentials_from_db')
    def test_scheduled_job_with_missing_config(self, mock_get_creds, db):
        """Test scheduled job with non-existent config."""
        # Should not raise exception
        scheduled_sync_job(str(uuid.uuid4()), str(uuid.uuid4()))

        # Should not call get_credentials
        assert not mock_get_creds.called

    @patch('app.api.oauth.get_credentials_from_db')
    def test_scheduled_job_with_inactive_config(self, mock_get_creds, db, test_user):
        """Test scheduled job with inactive config."""
        from app.models.sync_config import SyncConfig

        # Create inactive config
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source_cal",
            dest_calendar_id="dest_cal",
            is_active=False,  # Inactive
            auto_sync_enabled=True,
            auto_sync_cron="0 */6 * * *"
        )
        db.add(config)
        db.commit()

        # Execute job
        scheduled_sync_job(str(config.id), str(test_user.id))

        # Should not call get_credentials for inactive config
        assert not mock_get_creds.called

    @patch('app.api.sync.run_sync_task')
    @patch('app.api.oauth.get_credentials_from_db')
    @patch('app.database.SessionLocal')
    def test_scheduled_job_with_missing_credentials(self, mock_session_local, mock_get_creds, mock_run_sync, db, test_user):
        """Test scheduled job when OAuth credentials are missing."""
        from app.models.sync_config import SyncConfig
        from app.models.sync_log import SyncLog

        # Mock SessionLocal to return test db session
        mock_session_local.return_value = db

        # Create test config
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source_cal",
            dest_calendar_id="dest_cal",
            is_active=True,
            auto_sync_enabled=True,
            auto_sync_cron="0 */6 * * *"
        )
        db.add(config)
        db.commit()

        # Mock missing credentials
        mock_get_creds.return_value = None

        # Capture config ID before job execution (to avoid DetachedInstanceError)
        config_id = config.id

        # Execute job
        scheduled_sync_job(str(config_id), str(test_user.id))

        # Should not call run_sync_task
        assert not mock_run_sync.called

        # Should create failed sync log
        failed_log = db.query(SyncLog).filter(
            SyncLog.sync_config_id == config_id
        ).first()
        assert failed_log is not None
        assert failed_log.status == "failed"
        assert "OAuth credentials not found" in failed_log.error_message

    @patch('app.api.sync.run_sync_task')
    @patch('app.api.oauth.get_credentials_from_db')
    @patch('app.database.SessionLocal')
    def test_scheduled_job_creates_sync_log(self, mock_session_local, mock_get_creds, mock_run_sync, db, test_user):
        """Test that scheduled job creates sync log."""
        from app.models.sync_config import SyncConfig
        from app.models.sync_log import SyncLog

        # Mock SessionLocal to return test db session
        mock_session_local.return_value = db

        # Create test config
        config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source_cal",
            dest_calendar_id="dest_cal",
            is_active=True,
            auto_sync_enabled=True,
            auto_sync_cron="0 */6 * * *"
        )
        db.add(config)
        db.commit()

        # Mock credentials
        mock_creds = Mock()
        mock_get_creds.return_value = mock_creds

        # Execute job
        scheduled_sync_job(str(config.id), str(test_user.id))

        # Verify sync log was created
        sync_log = db.query(SyncLog).filter(
            SyncLog.sync_config_id == config.id
        ).first()
        assert sync_log is not None
        assert sync_log.status == "running"
