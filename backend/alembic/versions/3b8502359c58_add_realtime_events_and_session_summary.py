"""add realtime_events table and realtime_sessions.summary (mCOSA V12.1 §37/§38/§93 transcript+cost policy)

Revision ID: 3b8502359c58
Revises: b2cc9b34766c
Create Date: 2026-08-12 00:00:00.000002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3b8502359c58'
down_revision: Union[str, Sequence[str], None] = 'b2cc9b34766c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('realtime_sessions', sa.Column('summary', sa.Text(), nullable=True))

    op.create_table(
        'realtime_events',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('session_id', sa.BigInteger(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['realtime_sessions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_realtime_events_session_id'), 'realtime_events', ['session_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_realtime_events_session_id'), table_name='realtime_events')
    op.drop_table('realtime_events')
    op.drop_column('realtime_sessions', 'summary')
