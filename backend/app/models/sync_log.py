from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_config_id = Column(UUID(as_uuid=True), ForeignKey("sync_configs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Sync statistics
    events_created = Column(Integer, default=0, nullable=False)
    events_updated = Column(Integer, default=0, nullable=False)
    events_deleted = Column(Integer, default=0, nullable=False)

    # Status (success, failed, partial)
    status = Column(String(20), nullable=False)

    # Sync direction (for bi-directional sync tracking)
    sync_direction = Column(String(20), nullable=True)  # 'one_way', 'bidirectional_a_to_b', 'bidirectional_b_to_a'

    # Error message if failed
    error_message = Column(Text)

    # Sync window
    sync_window_start = Column(DateTime(timezone=True), nullable=False)
    sync_window_end = Column(DateTime(timezone=True), nullable=False)

    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    sync_config = relationship("SyncConfig", back_populates="sync_logs")
