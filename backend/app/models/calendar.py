from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Calendar(Base):
    __tablename__ = "calendars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oauth_token_id = Column(UUID(as_uuid=True), ForeignKey("oauth_tokens.id", ondelete="CASCADE"), nullable=False, index=True)

    # Calendar ID from Google
    google_calendar_id = Column(String(255), nullable=False, index=True)

    # Calendar metadata from Google
    summary = Column(String(255))  # Calendar name
    description = Column(Text)
    time_zone = Column(String(100))
    is_primary = Column(Boolean, default=False)

    # Access role (owner, writer, reader)
    access_role = Column(String(50))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
