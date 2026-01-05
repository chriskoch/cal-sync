"""
Tests for FastAPI lifespan integration and scheduler initialization.

Tests that the scheduler properly starts and stops with the FastAPI application
lifecycle using the lifespan context manager.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


class TestLifespanIntegration:
    """Test FastAPI lifespan integration with scheduler."""

    @patch('app.main.get_scheduler')
    @patch('app.main.SessionLocal')
    def test_lifespan_starts_scheduler(self, mock_session_local, mock_get_scheduler):
        """Lifespan should start scheduler on application startup."""
        # Setup mocks
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler
        mock_db = Mock()
        mock_session_local.return_value = mock_db

        # Import app after patching to ensure mocks are used
        from app.main import app

        # Create test client (triggers lifespan)
        with TestClient(app) as client:
            # Verify scheduler was retrieved
            mock_get_scheduler.assert_called_once()

            # Verify scheduler.start() was called
            mock_scheduler.start.assert_called_once()

            # Verify jobs were loaded from database
            mock_session_local.assert_called_once()
            mock_scheduler.load_all_jobs_from_db.assert_called_once_with(mock_db)

            # Verify database session was closed
            mock_db.close.assert_called_once()

        # After context exit, verify shutdown was called
        mock_scheduler.shutdown.assert_called_once_with(wait=True)

    @patch('app.main.get_scheduler')
    @patch('app.main.SessionLocal')
    def test_lifespan_handles_database_error(self, mock_session_local, mock_get_scheduler):
        """Lifespan should close database even if job loading fails."""
        # Setup mocks
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler
        mock_db = Mock()
        mock_session_local.return_value = mock_db

        # Make load_all_jobs_from_db raise an error
        mock_scheduler.load_all_jobs_from_db.side_effect = Exception("Database error")

        from app.main import app

        # App should still start despite job loading error
        with pytest.raises(Exception, match="Database error"):
            with TestClient(app):
                pass

        # Database should still be closed even after error
        mock_db.close.assert_called_once()

    @patch('app.main.get_scheduler')
    @patch('app.main.SessionLocal')
    def test_lifespan_health_check(self, mock_session_local, mock_get_scheduler):
        """Health check should work after lifespan initialization."""
        # Setup mocks
        mock_scheduler = Mock()
        mock_get_scheduler.return_value = mock_scheduler
        mock_db = Mock()
        mock_session_local.return_value = mock_db

        from app.main import app

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}


class TestSchedulerSingleton:
    """Test scheduler singleton pattern."""

    def test_get_scheduler_returns_same_instance(self):
        """get_scheduler() should return the same instance on multiple calls."""
        from app.core.scheduler import get_scheduler, _scheduler_instance

        # Reset global instance for clean test
        import app.core.scheduler
        app.core.scheduler._scheduler_instance = None

        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()

        assert scheduler1 is scheduler2
        assert scheduler1 is not None

    def test_get_scheduler_creates_new_instance(self):
        """get_scheduler() should create instance if none exists."""
        from app.core.scheduler import get_scheduler, SyncScheduler

        # Reset global instance
        import app.core.scheduler
        app.core.scheduler._scheduler_instance = None

        scheduler = get_scheduler()

        assert isinstance(scheduler, SyncScheduler)
        assert scheduler.scheduler is None  # Not started yet
        assert scheduler._running is False


class TestSchedulerInitialization:
    """Test scheduler initialization and configuration."""

    def test_scheduler_initial_state(self):
        """New scheduler should be uninitialized and not running."""
        from app.core.scheduler import SyncScheduler

        scheduler = SyncScheduler()

        assert scheduler.scheduler is None
        assert scheduler._running is False

    def test_scheduler_start_creates_apscheduler(self):
        """Starting scheduler should create and configure APScheduler instance."""
        from app.core.scheduler import SyncScheduler

        scheduler = SyncScheduler()
        scheduler.start()

        try:
            # Verify APScheduler was created
            assert scheduler.scheduler is not None
            assert scheduler._running is True

            # Verify configuration
            assert scheduler.scheduler.running is True
            assert 'default' in scheduler.scheduler._jobstores
            assert 'default' in scheduler.scheduler._executors

        finally:
            scheduler.shutdown(wait=False)

    def test_scheduler_configuration(self):
        """Scheduler should be configured with correct settings."""
        from app.core.scheduler import SyncScheduler
        import pytz

        scheduler = SyncScheduler()
        scheduler.start()

        try:
            # Check jobstore configuration
            jobstore = scheduler.scheduler._jobstores['default']
            assert jobstore.__class__.__name__ == 'MemoryJobStore'

            # Check executor configuration
            executor = scheduler.scheduler._executors['default']
            assert executor.__class__.__name__ == 'ThreadPoolExecutor'
            # Note: ThreadPoolExecutor._max_workers is private and may vary

            # Check timezone
            assert scheduler.scheduler.timezone == pytz.UTC

        finally:
            scheduler.shutdown(wait=False)

    def test_multiple_start_calls_idempotent(self):
        """Calling start() multiple times should be safe."""
        from app.core.scheduler import SyncScheduler

        scheduler = SyncScheduler()

        scheduler.start()
        assert scheduler._running is True

        # Second start() call - should not crash
        scheduler.start()
        assert scheduler._running is True

        scheduler.shutdown(wait=False)


class TestSchedulerWithRealDB:
    """Integration tests with real database (session-scoped fixtures)."""

    def test_load_jobs_from_database(self, db):
        """Scheduler should load all active auto-sync configs from database."""
        from app.core.scheduler import SyncScheduler
        from app.models.sync_config import SyncConfig
        from app.models.user import User
        import uuid

        # Create test user
        user = User(
            id=uuid.uuid4(),
            email="scheduler_test@example.com",
        )
        db.add(user)
        db.commit()

        # Create test configs with auto-sync enabled
        configs = []
        for i in range(3):
            config = SyncConfig(
                user_id=user.id,
                source_calendar_id=f"test_cal_{i}",
                dest_calendar_id=f"dest_cal_{i}",
                is_active=True,
                auto_sync_enabled=True,
                auto_sync_cron=f"*/{(i+1)*5} * * * *",  # Every 5, 10, 15 minutes
                auto_sync_timezone="UTC",
            )
            configs.append(config)
            db.add(config)

        db.commit()

        # Test scheduler loading
        scheduler = SyncScheduler()
        scheduler.start()

        try:
            scheduler.load_all_jobs_from_db(db)

            jobs = scheduler.scheduler.get_jobs()
            assert len(jobs) == 3

            # Verify job IDs match config IDs
            config_ids = {str(c.id) for c in configs}
            job_config_ids = {job.id.replace("sync_", "") for job in jobs}
            assert job_config_ids == config_ids

        finally:
            scheduler.shutdown(wait=False)
