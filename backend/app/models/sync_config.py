from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class SyncConfig(Base):
    __tablename__ = "sync_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Source calendar (read from)
    source_calendar_id = Column(String(255), nullable=False)

    # Destination calendar (write to)
    dest_calendar_id = Column(String(255), nullable=False)

    # Sync settings
    is_active = Column(Boolean, default=True, nullable=False)
    sync_lookahead_days = Column(Integer, default=90, nullable=False)
    destination_color_id = Column(String(50), nullable=True)  # Google Calendar color ID for destination events

    # Bi-directional sync settings
    sync_direction = Column(String(20), default="one_way", nullable=False)  # 'one_way', 'bidirectional_a_to_b', 'bidirectional_b_to_a'
    paired_config_id = Column(UUID(as_uuid=True), ForeignKey("sync_configs.id", ondelete="SET NULL"), nullable=True)  # Links to paired config

    # Privacy mode settings
    privacy_mode_enabled = Column(Boolean, default=False, nullable=False)
    privacy_placeholder_text = Column(String(255), default="Personal appointment", nullable=True)

    # Auto-sync scheduling
    auto_sync_enabled = Column(Boolean, default=False, nullable=False)
    auto_sync_cron = Column(String(100), nullable=True)  # Cron expression (e.g., "0 */6 * * *")
    auto_sync_timezone = Column(String(50), default="UTC", nullable=False)

    # Last sync timestamp
    last_synced_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="sync_configs")
    sync_logs = relationship("SyncLog", back_populates="sync_config", cascade="all, delete-orphan")
    event_mappings = relationship("EventMapping", back_populates="sync_config", cascade="all, delete-orphan")
