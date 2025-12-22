from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class EventMapping(Base):
    """Tracks bidirectional mapping between source and destination events (Story 3)."""
    __tablename__ = "event_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_config_id = Column(UUID(as_uuid=True), ForeignKey("sync_configs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event IDs from Google Calendar
    source_event_id = Column(String(255), nullable=False)
    dest_event_id = Column(String(255), nullable=False)

    # Bidirectional sync cluster ID (Story 3)
    sync_cluster_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)

    # Last modified timestamps from Google
    source_last_modified = Column(DateTime(timezone=True))
    dest_last_modified = Column(DateTime(timezone=True))

    # Last sync timestamp
    last_synced_at = Column(DateTime(timezone=True))

    # Content hash (SHA-256) for change detection
    content_hash = Column(String(64))

    # Bi-directional sync metadata
    origin_calendar_id = Column(String(255), nullable=True)  # Which calendar originally created the event
    is_privacy_mode = Column(Boolean, default=False, nullable=False)  # If event was synced with privacy mode

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    sync_config = relationship("SyncConfig", back_populates="event_mappings")

    __table_args__ = (
        UniqueConstraint('sync_config_id', 'source_event_id', name='uq_config_source'),
    )
