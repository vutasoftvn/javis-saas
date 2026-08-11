"""mcosa v12 sprint 9 next best action engine

Revision ID: v12_008_sprint9
Revises: v12_007_sprint8
Create Date: 2026-08-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'v12_008_sprint9'
down_revision: Union[str, Sequence[str], None] = 'v12_007_sprint8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. next_action_candidates
    op.create_table(
        'next_action_candidates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=True),
        sa.Column('portfolio_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='GOVERNANCE_DECISION'),
        sa.Column('urgency_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('impact_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('effort_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('r0_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='proposed'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_next_action_candidates_portfolio_id'), 'next_action_candidates', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_next_action_candidates_project_id'), 'next_action_candidates', ['project_id'], unique=False)
    op.create_index(op.f('ix_next_action_candidates_workspace_id'), 'next_action_candidates', ['workspace_id'], unique=False)

    # 2. next_action_rankings
    op.create_table(
        'next_action_rankings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('ranking_round', sa.String(length=50), nullable=False, server_default='R0_DETERMINISTIC'),
        sa.Column('rank_position', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('composite_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['candidate_id'], ['next_action_candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_next_action_rankings_candidate_id'), 'next_action_rankings', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_next_action_rankings_workspace_id'), 'next_action_rankings', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('next_action_rankings')
    op.drop_table('next_action_candidates')
