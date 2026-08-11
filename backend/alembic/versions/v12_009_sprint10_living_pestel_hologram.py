"""mcosa v12 sprint 10 living pestel & model audit

Revision ID: v12_009_sprint10
Revises: v12_008_sprint9
Create Date: 2026-08-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'v12_009_sprint10'
down_revision: Union[str, Sequence[str], None] = 'v12_008_sprint9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. pestel_signals
    op.create_table(
        'pestel_signals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('signal_title', sa.String(length=255), nullable=False),
        sa.Column('signal_summary', sa.Text(), nullable=True),
        sa.Column('pestel_category', sa.String(length=50), nullable=False, server_default='ECONOMIC'),
        sa.Column('magnitude', sa.String(length=50), nullable=False, server_default='MEDIUM'),
        sa.Column('is_material_change', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pestel_signals_workspace_id'), 'pestel_signals', ['workspace_id'], unique=False)

    # 2. model_runs_audit
    op.create_table(
        'model_runs_audit',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('model_profile', sa.String(length=100), nullable=False, server_default='TERRA_V12'),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='success'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_runs_audit_workspace_id'), 'model_runs_audit', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('model_runs_audit')
    op.drop_table('pestel_signals')
