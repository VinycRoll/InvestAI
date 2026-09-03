"""baseline schema

Revision ID: fe96d7ea4f1b
Revises:
Create Date: 2026-08-29 18:20:27.203020

Cria o schema inicial (estado anterior à migration ``a1b2c3d4e5f6``,
que adiciona ``users.password_hash``). Inclui também ``user_categories``,
que estava ausente da autogeração original.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fe96d7ea4f1b'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('email', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
            index=True,
        ),
    )

    op.create_table(
        'files',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), index=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('parsed_data', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
            index=True,
        ),
    )

    op.create_table(
        'analyses',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), index=True),
        sa.Column(
            'file_id',
            sa.Integer(),
            sa.ForeignKey('files.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column('analysis_type', sa.String(), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
            index=True,
        ),
    )

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), index=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
            index=True,
        ),
    )

    op.create_table(
        'user_categories',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
            index=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_categories')
    op.drop_table('chat_messages')
    op.drop_table('analyses')
    op.drop_table('files')
    op.drop_table('users')
