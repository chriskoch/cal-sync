"""add_destination_color_id_to_sync_configs

Revision ID: 5ca5e2b9e0ba
Revises: 002_event_mappings
Create Date: 2025-12-19 22:35:29.953878

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5ca5e2b9e0ba'
down_revision = '002_event_mappings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add destination_color_id column to sync_configs table
    op.add_column('sync_configs', sa.Column('destination_color_id', sa.String(length=50), nullable=True))


def downgrade() -> None:
    # Remove destination_color_id column from sync_configs table
    op.drop_column('sync_configs', 'destination_color_id')
