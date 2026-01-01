"""
End-to-end integration tests for sync functionality.

These tests verify the complete sync flow including:
- OAuth token creation and retrieval with correct UUID types
- One-way sync triggering
- Bi-directional sync triggering
- Actual credential fetching (not mocked)
"""
import pytest
from fastapi import status
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from app.models.sync_config import SyncConfig
from app.models.oauth_token import OAuthToken
from app.models.sync_log import SyncLog
from tests.test_utils import assert_response_success
from app.core.security import encrypt_token


@pytest.fixture
def source_oauth_token(db, test_user):
    """Create a source OAuth token with proper UUID type."""
    # Create encrypted tokens
    access_token_encrypted = encrypt_token("test_source_access_token")
    refresh_token_encrypted = encrypt_token("test_source_refresh_token")

    token = OAuthToken(
        user_id=test_user.id,  # This is already a UUID object from test_user fixture
        account_type="source",
        google_email="source@example.com",
        access_token_encrypted=access_token_encrypted,
        refresh_token_encrypted=refresh_token_encrypted,
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


@pytest.fixture
def dest_oauth_token(db, test_user):
    """Create a destination OAuth token with proper UUID type."""
    # Create encrypted tokens
    access_token_encrypted = encrypt_token("test_dest_access_token")
    refresh_token_encrypted = encrypt_token("test_dest_refresh_token")

    token = OAuthToken(
        user_id=test_user.id,  # This is already a UUID object from test_user fixture
        account_type="destination",
        google_email="dest@example.com",
        access_token_encrypted=access_token_encrypted,
        refresh_token_encrypted=refresh_token_encrypted,
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


@pytest.mark.integration
@pytest.mark.sync
class TestSyncIntegrationE2E:
    """End-to-end integration tests for sync functionality."""

    @patch('app.api.sync.BackgroundTasks.add_task')
    def test_trigger_one_way_sync_with_real_oauth_tokens(
        self,
        mock_add_task,
        client,
        auth_headers,
        db,
        test_user,
        source_oauth_token,
        dest_oauth_token
    ):
        """
        Test triggering one-way sync with real OAuth tokens from database.

        This test verifies that:
        1. OAuth tokens are correctly retrieved using UUID (not string)
        2. get_credentials_from_db works with proper UUID type
        3. Sync can be triggered successfully
        """
        # Create sync config
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source_cal@example.com",
            dest_calendar_id="dest_cal@example.com",
            sync_lookahead_days=90,
            sync_direction="one_way",
            is_active=True,
        )
        db.add(sync_config)
        db.commit()
        db.refresh(sync_config)

        # Trigger sync - this should retrieve credentials using UUID
        response = client.post(
            f"/sync/trigger/{sync_config.id}",
            headers=auth_headers
        )

        # Verify success
        assert_response_success(response, status.HTTP_200_OK)
        data = response.json()
        assert "sync_log_id" in data
        assert "message" in data

        # Verify sync log was created
        sync_log = db.query(SyncLog).filter(
            SyncLog.sync_config_id == sync_config.id
        ).first()
        assert sync_log is not None
        assert sync_log.status == "running"
        assert sync_log.sync_direction == "one_way"

        # Verify background task was scheduled
        assert mock_add_task.called

    @patch('app.api.sync.BackgroundTasks.add_task')
    def test_trigger_bidirectional_sync_with_real_oauth_tokens(
        self,
        mock_add_task,
        client,
        auth_headers,
        db,
        test_user,
        source_oauth_token,
        dest_oauth_token
    ):
        """
        Test triggering bi-directional sync with real OAuth tokens.

        Verifies:
        1. Both directions can retrieve credentials correctly
        2. Both sync logs are created
        3. Both background tasks are scheduled
        """
        # Create paired bi-directional configs
        config_a_to_b = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_a@example.com",
            dest_calendar_id="calendar_b@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_a_to_b",
            is_active=True,
        )
        db.add(config_a_to_b)
        db.flush()

        config_b_to_a = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="calendar_b@example.com",
            dest_calendar_id="calendar_a@example.com",
            sync_lookahead_days=90,
            sync_direction="bidirectional_b_to_a",
            paired_config_id=config_a_to_b.id,
            is_active=True,
        )
        db.add(config_b_to_a)
        db.flush()

        config_a_to_b.paired_config_id = config_b_to_a.id
        db.commit()

        # Trigger both directions
        response = client.post(
            f"/sync/trigger/{config_a_to_b.id}?trigger_both_directions=true",
            headers=auth_headers
        )

        # Verify success
        assert_response_success(response, status.HTTP_200_OK)

        # Verify sync logs were created for both directions
        logs = db.query(SyncLog).all()
        assert len(logs) == 2

        forward_log = next((log for log in logs if log.sync_config_id == config_a_to_b.id), None)
        reverse_log = next((log for log in logs if log.sync_config_id == config_b_to_a.id), None)

        assert forward_log is not None
        assert reverse_log is not None
        assert forward_log.sync_direction == "bidirectional_a_to_b"
        assert reverse_log.sync_direction == "bidirectional_b_to_a"

        # Verify both background tasks were scheduled
        assert mock_add_task.call_count == 2

    def test_trigger_sync_fails_without_oauth_tokens(
        self,
        client,
        auth_headers,
        db,
        test_user
    ):
        """
        Test that sync fails gracefully when OAuth tokens don't exist.

        This verifies the error handling when credentials cannot be found.
        """
        # Create sync config WITHOUT creating OAuth tokens
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source_cal@example.com",
            dest_calendar_id="dest_cal@example.com",
            sync_lookahead_days=90,
            sync_direction="one_way",
            is_active=True,
        )
        db.add(sync_config)
        db.commit()

        # Attempt to trigger sync - should fail due to missing credentials
        response = client.post(
            f"/sync/trigger/{sync_config.id}",
            headers=auth_headers
        )

        # Verify failure
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "OAuth credentials not found" in data["detail"]

    def test_trigger_sync_fails_with_only_source_token(
        self,
        client,
        auth_headers,
        db,
        test_user,
        source_oauth_token
    ):
        """
        Test that sync fails when only source OAuth token exists.
        """
        # Create sync config with only source token
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source_cal@example.com",
            dest_calendar_id="dest_cal@example.com",
            sync_lookahead_days=90,
            sync_direction="one_way",
            is_active=True,
        )
        db.add(sync_config)
        db.commit()

        # Attempt to trigger sync - should fail due to missing destination credentials
        response = client.post(
            f"/sync/trigger/{sync_config.id}",
            headers=auth_headers
        )

        # Verify failure
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "OAuth credentials not found" in data["detail"]

    def test_trigger_sync_fails_with_only_dest_token(
        self,
        client,
        auth_headers,
        db,
        test_user,
        dest_oauth_token
    ):
        """
        Test that sync fails when only destination OAuth token exists.
        """
        # Create sync config with only dest token
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source_cal@example.com",
            dest_calendar_id="dest_cal@example.com",
            sync_lookahead_days=90,
            sync_direction="one_way",
            is_active=True,
        )
        db.add(sync_config)
        db.commit()

        # Attempt to trigger sync - should fail due to missing source credentials
        response = client.post(
            f"/sync/trigger/{sync_config.id}",
            headers=auth_headers
        )

        # Verify failure
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "OAuth credentials not found" in data["detail"]

    @patch('app.api.sync.BackgroundTasks.add_task')
    def test_uuid_type_correctness(
        self,
        mock_add_task,
        client,
        auth_headers,
        db,
        test_user,
        source_oauth_token,
        dest_oauth_token
    ):
        """
        Regression test for UUID type mismatch bug.

        This test specifically verifies that:
        1. current_user.id is passed as UUID (not string) to get_credentials_from_db
        2. Database query correctly matches UUID column against UUID value
        3. Credentials are successfully retrieved

        Previously failed when str(current_user.id) was used.
        """
        import uuid

        # Verify test_user.id is a UUID object
        assert isinstance(test_user.id, uuid.UUID), "test_user.id should be a UUID object"

        # Verify OAuth tokens have matching user_id as UUID
        assert source_oauth_token.user_id == test_user.id
        assert dest_oauth_token.user_id == test_user.id
        assert isinstance(source_oauth_token.user_id, uuid.UUID)
        assert isinstance(dest_oauth_token.user_id, uuid.UUID)

        # Create sync config
        sync_config = SyncConfig(
            user_id=test_user.id,
            source_calendar_id="source_cal@example.com",
            dest_calendar_id="dest_cal@example.com",
            sync_lookahead_days=90,
            sync_direction="one_way",
            is_active=True,
        )
        db.add(sync_config)
        db.commit()

        # This should work because current_user.id is UUID (not string)
        response = client.post(
            f"/sync/trigger/{sync_config.id}",
            headers=auth_headers
        )

        # If UUID type was wrong, get_credentials_from_db would return None
        # and we'd get a 400 error about missing credentials
        assert_response_success(response, status.HTTP_200_OK)

        # Verify credentials were successfully retrieved by checking task was scheduled
        assert mock_add_task.called


@pytest.mark.integration
@pytest.mark.sync
class TestCredentialRetrievalWithUUID:
    """Test OAuth credential retrieval with UUID type handling."""

    def test_get_credentials_with_uuid_object(
        self,
        db,
        test_user,
        source_oauth_token
    ):
        """Test that get_credentials_from_db works with UUID object."""
        from app.api.oauth import get_credentials_from_db

        # Pass UUID object (correct)
        creds = get_credentials_from_db(test_user.id, "source", db)

        assert creds is not None
        assert creds.token == "test_source_access_token"
        assert creds.refresh_token == "test_source_refresh_token"

    def test_get_credentials_with_string_uuid_also_works(
        self,
        db,
        test_user,
        source_oauth_token
    ):
        """
        Test that get_credentials_from_db works with string UUID too.

        Note: While SQLAlchemy/PostgreSQL automatically converts string UUIDs,
        it's still better practice to pass UUID objects for:
        - Code clarity
        - Type consistency
        - Database portability
        """
        from app.api.oauth import get_credentials_from_db

        # Pass string UUID - SQLAlchemy/PostgreSQL handles conversion
        creds = get_credentials_from_db(str(test_user.id), "source", db)

        # This works because PostgreSQL can cast string to UUID automatically
        assert creds is not None
        assert creds.token == "test_source_access_token"
