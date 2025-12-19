"""
Pytest configuration and fixtures for backend tests.
"""
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, String, TypeDecorator, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY as PG_ARRAY
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
import json

# Monkey-patch UUID and ARRAY to work with SQLite BEFORE importing models
class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type when available, falls back to String(36) for SQLite.
    Stores as stringified hex values.
    """
    impl = String(36)
    cache_ok = True

    def __init__(self, as_uuid=True):
        self.as_uuid = as_uuid
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=self.as_uuid))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if isinstance(value, uuid.UUID):
                return value
            else:
                return uuid.UUID(value) if self.as_uuid else value


class JSONEncodedArray(TypeDecorator):
    """Platform-independent ARRAY type.

    Uses PostgreSQL's ARRAY type when available, falls back to JSON-encoded Text for SQLite.
    """
    impl = Text
    cache_ok = True

    def __init__(self, item_type=None):
        self.item_type = item_type
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_ARRAY(self.item_type if self.item_type else String))
        else:
            return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            # For SQLite, store as JSON
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            # For SQLite, load from JSON
            return json.loads(value) if value else []


# Replace UUID and ARRAY in postgresql module with our compatible types
from sqlalchemy.dialects import postgresql
postgresql.UUID = GUID
postgresql.ARRAY = JSONEncodedArray

# Now import models after patching
from app.main import app
from app.database import Base, get_db
from app.config import settings
from app.models.user import User
from app.core.security import get_password_hash

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator:
    """
    Create a fresh database for each test function.
    """
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db) -> Generator:
    """
    Create a test client with the test database.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db) -> User:
    """
    Create a test user in the database.
    Password: TestPassword123!
    """
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("TestPassword123!"),
        full_name="Test User",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_token(client, test_user) -> str:
    """
    Get an authentication token for the test user.
    """
    response = client.post(
        "/auth/token",
        data={"username": test_user.email, "password": "testpassword123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(test_user_token) -> dict:
    """
    Get authorization headers for authenticated requests.
    """
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def mock_google_calendar_service(mocker):
    """
    Mock Google Calendar API service.
    """
    mock_service = mocker.Mock()
    mock_service.events().list().execute.return_value = {
        "items": [],
        "nextPageToken": None
    }
    mock_service.events().insert().execute.return_value = {
        "id": "test_event_id",
        "summary": "Test Event"
    }
    mock_service.events().update().execute.return_value = {
        "id": "test_event_id",
        "summary": "Updated Event"
    }
    mock_service.events().delete().execute.return_value = {}

    return mock_service
