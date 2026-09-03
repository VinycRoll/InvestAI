"""add password_hash

Revision ID: a1b2c3d4e5f6
Revises: fe96d7ea4f1b
Create Date: 2026-08-31 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | Sequence[str] | None = 'fe96d7ea4f1b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('password_hash', sa.String(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'password_hash')
