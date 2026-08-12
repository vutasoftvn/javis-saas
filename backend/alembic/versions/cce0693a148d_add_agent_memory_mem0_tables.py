"""add agent_memory MEM-0 integration-metadata tables (mCOSA V12.3 §183-184, ADR-MEM-001/002)

Revision ID: cce0693a148d
Revises: aed16401ab42
Create Date: 2026-08-12 00:00:00.000004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cce0693a148d'
down_revision: Union[str, Sequence[str], None] = 'aed16401ab42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'agent_memory_engines',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='tencentdb_agent_memory'),
        sa.Column('deployment', sa.String(length=50), nullable=False, server_default='local_sidecar'),
        sa.Column('base_url', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agent_memory_engines_workspace_id'), 'agent_memory_engines', ['workspace_id'], unique=False)

    op.create_table(
        'agent_memory_scopes',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('scope_type', sa.String(length=50), nullable=False),
        sa.Column('subject_id', sa.String(length=100), nullable=True),
        sa.Column('classification', sa.String(length=50), nullable=False, server_default='INTERNAL'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agent_memory_scopes_workspace_id'), 'agent_memory_scopes', ['workspace_id'], unique=False)

    op.create_table(
        'memory_candidates',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('project_id', sa.BigInteger(), nullable=True),
        sa.Column('source_memory_ref', sa.String(length=255), nullable=True),
        sa.Column('candidate_type', sa.String(length=50), nullable=False),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('source_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('proposed_target', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PROPOSED'),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('reviewed_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_memory_candidates_workspace_id'), 'memory_candidates', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_memory_candidates_project_id'), 'memory_candidates', ['project_id'], unique=False)

    op.create_table(
        'memory_promotions',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('candidate_id', sa.BigInteger(), nullable=False),
        sa.Column('promoted_target_type', sa.String(length=50), nullable=False),
        sa.Column('promoted_target_id', sa.String(length=100), nullable=True),
        sa.Column('promoted_by', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['candidate_id'], ['memory_candidates.id']),
        sa.ForeignKeyConstraint(['promoted_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_memory_promotions_workspace_id'), 'memory_promotions', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_memory_promotions_candidate_id'), 'memory_promotions', ['candidate_id'], unique=False)

    op.create_table(
        'memory_evaluations',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_memory_evaluations_workspace_id'), 'memory_evaluations', ['workspace_id'], unique=False)

    op.create_table(
        'memory_sync_records',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('sync_class', sa.String(length=50), nullable=False),
        sa.Column('memory_ref', sa.String(length=255), nullable=False),
        sa.Column('synced_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_memory_sync_records_workspace_id'), 'memory_sync_records', ['workspace_id'], unique=False)

    op.create_table(
        'memory_health_snapshots',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('backend', sa.String(length=50), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('memory_health_snapshots')
    op.drop_index(op.f('ix_memory_sync_records_workspace_id'), table_name='memory_sync_records')
    op.drop_table('memory_sync_records')
    op.drop_index(op.f('ix_memory_evaluations_workspace_id'), table_name='memory_evaluations')
    op.drop_table('memory_evaluations')
    op.drop_index(op.f('ix_memory_promotions_candidate_id'), table_name='memory_promotions')
    op.drop_index(op.f('ix_memory_promotions_workspace_id'), table_name='memory_promotions')
    op.drop_table('memory_promotions')
    op.drop_index(op.f('ix_memory_candidates_project_id'), table_name='memory_candidates')
    op.drop_index(op.f('ix_memory_candidates_workspace_id'), table_name='memory_candidates')
    op.drop_table('memory_candidates')
    op.drop_index(op.f('ix_agent_memory_scopes_workspace_id'), table_name='agent_memory_scopes')
    op.drop_table('agent_memory_scopes')
    op.drop_index(op.f('ix_agent_memory_engines_workspace_id'), table_name='agent_memory_engines')
    op.drop_table('agent_memory_engines')
