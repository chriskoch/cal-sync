"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2025-12-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create oauth_tokens table
    op.create_table('oauth_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_type', sa.String(length=20), nullable=False),
        sa.Column('google_email', sa.String(length=255), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scopes', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'account_type', name='uq_user_account_type')
    )
    op.create_index(op.f('ix_oauth_tokens_user_id'), 'oauth_tokens', ['user_id'], unique=False)

    # Create calendars table
    op.create_table('calendars',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('oauth_token_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('google_calendar_id', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('time_zone', sa.String(length=100), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=True),
        sa.Column('access_role', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['oauth_token_id'], ['oauth_tokens.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calendars_oauth_token_id'), 'calendars', ['oauth_token_id'], unique=False)
    op.create_index(op.f('ix_calendars_google_calendar_id'), 'calendars', ['google_calendar_id'], unique=False)

    # Create sync_configs table
    op.create_table('sync_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_calendar_id', sa.String(length=255), nullable=False),
        sa.Column('dest_calendar_id', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('sync_lookahead_days', sa.Integer(), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sync_configs_user_id'), 'sync_configs', ['user_id'], unique=False)

    # Create sync_logs table
    op.create_table('sync_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sync_config_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('events_created', sa.Integer(), nullable=False),
        sa.Column('events_updated', sa.Integer(), nullable=False),
        sa.Column('events_deleted', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sync_window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sync_window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['sync_config_id'], ['sync_configs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sync_logs_sync_config_id'), 'sync_logs', ['sync_config_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sync_logs_sync_config_id'), table_name='sync_logs')
    op.drop_table('sync_logs')
    op.drop_index(op.f('ix_sync_configs_user_id'), table_name='sync_configs')
    op.drop_table('sync_configs')
    op.drop_index(op.f('ix_calendars_google_calendar_id'), table_name='calendars')
    op.drop_index(op.f('ix_calendars_oauth_token_id'), table_name='calendars')
    op.drop_table('calendars')
    op.drop_index(op.f('ix_oauth_tokens_user_id'), table_name='oauth_tokens')
    op.drop_table('oauth_tokens')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
