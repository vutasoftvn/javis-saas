"""add realtime_sessions (mCOSA V12.1 LiveKit voice MVP)

Revision ID: f3a9c1e7b2d4
Revises: 0cb6b8a3b033
Create Date: 2026-08-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a9c1e7b2d4'
down_revision: Union[str, Sequence[str], None] = '0cb6b8a3b033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'realtime_sessions',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('device_type', sa.String(length=20), nullable=False),
        sa.Column('transport', sa.String(length=30), nullable=False, server_default='livekit_cloud'),
        sa.Column('model_profile', sa.String(length=50), nullable=False, server_default='gemini_live'),
        sa.Column('room_name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='creating'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('room_name'),
    )
    op.create_index(op.f('ix_realtime_sessions_workspace_id'), 'realtime_sessions', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_realtime_sessions_user_id'), 'realtime_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_realtime_sessions_room_name'), 'realtime_sessions', ['room_name'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_realtime_sessions_room_name'), table_name='realtime_sessions')
    op.drop_index(op.f('ix_realtime_sessions_user_id'), table_name='realtime_sessions')
    op.drop_index(op.f('ix_realtime_sessions_workspace_id'), table_name='realtime_sessions')
    op.drop_table('realtime_sessions')
