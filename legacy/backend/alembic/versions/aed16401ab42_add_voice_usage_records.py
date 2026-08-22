"""add voice_usage_records (mCOSA V12.1 §46/§56/§82 realtime cost tracking)

Revision ID: aed16401ab42
Revises: 3b8502359c58
Create Date: 2026-08-12 00:00:00.000003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aed16401ab42'
down_revision: Union[str, Sequence[str], None] = '3b8502359c58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'voice_usage_records',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('session_id', sa.BigInteger(), nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('model_profile', sa.String(length=50), nullable=False),
        sa.Column('estimated_cost', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['realtime_sessions.id']),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id'),
    )
    op.create_index(op.f('ix_voice_usage_records_session_id'), 'voice_usage_records', ['session_id'], unique=True)
    op.create_index(op.f('ix_voice_usage_records_workspace_id'), 'voice_usage_records', ['workspace_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_voice_usage_records_workspace_id'), table_name='voice_usage_records')
    op.drop_index(op.f('ix_voice_usage_records_session_id'), table_name='voice_usage_records')
    op.drop_table('voice_usage_records')
