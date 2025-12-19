"""add event_mappings table for Story 3

Revision ID: 002_event_mappings
Revises: 001_initial
Create Date: 2025-12-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_event_mappings'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create event_mappings table for bidirectional sync tracking (Story 3)
    op.create_table('event_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sync_config_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_event_id', sa.String(length=255), nullable=False),
        sa.Column('dest_event_id', sa.String(length=255), nullable=False),
        sa.Column('sync_cluster_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_last_modified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dest_last_modified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sync_config_id'], ['sync_configs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sync_config_id', 'source_event_id', name='uq_config_source')
    )
    op.create_index(op.f('ix_event_mappings_sync_config_id'), 'event_mappings', ['sync_config_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_event_mappings_sync_config_id'), table_name='event_mappings')
    op.drop_table('event_mappings')
