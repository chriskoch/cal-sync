"""remove_password_auth

Revision ID: 003_remove_password_auth
Revises: 5ca5e2b9e0ba
Create Date: 2025-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_remove_password_auth'
down_revision = '5ca5e2b9e0ba'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove hashed_password column from users table
    op.drop_column('users', 'hashed_password')


def downgrade() -> None:
    # Add hashed_password column back (nullable for backward compatibility)
    op.add_column('users', sa.Column('hashed_password', sa.String(length=255), nullable=True))

