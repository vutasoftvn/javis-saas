"""mcosa v12 sprint 5 weekly reviews and week 13 celebration

Revision ID: v12_004_sprint5
Revises: v12_003_sprint3
Create Date: 2026-08-11 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'v12_004_sprint5'
down_revision: Union[str, Sequence[str], None] = 'v12_003_sprint3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. weekly_reviews
    op.create_table(
        'weekly_reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('cycle_id', sa.UUID(), nullable=False),
        sa.Column('weekly_plan_id', sa.UUID(), nullable=False),
        sa.Column('week_no', sa.Integer(), nullable=False),
        sa.Column('execution_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('outcome_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('evidence_learned', sa.Text(), nullable=True),
        sa.Column('assumptions_confirmed', JSONB(), nullable=True),
        sa.Column('assumptions_invalidated', JSONB(), nullable=True),
        sa.Column('recommendation', sa.String(length=50), nullable=False, server_default='CONTINUE'),
        sa.Column('narrative_summary', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.UUID(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['cycle_id'], ['twelve_week_cycles.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['weekly_plan_id'], ['weekly_plans.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('weekly_plan_id', name='uix_weekly_review_plan')
    )
    op.create_index(op.f('ix_weekly_reviews_cycle_id'), 'weekly_reviews', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_weekly_reviews_reviewed_by'), 'weekly_reviews', ['reviewed_by'], unique=False)
    op.create_index(op.f('ix_weekly_reviews_weekly_plan_id'), 'weekly_reviews', ['weekly_plan_id'], unique=False)
    op.create_index(op.f('ix_weekly_reviews_workspace_id'), 'weekly_reviews', ['workspace_id'], unique=False)

    # 2. cycle_reviews
    op.create_table(
        'cycle_reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('cycle_id', sa.UUID(), nullable=False),
        sa.Column('overall_execution_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('overall_outcome_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('okr_achievement_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('strategic_learnings', sa.Text(), nullable=True),
        sa.Column('systemic_blockers', sa.Text(), nullable=True),
        sa.Column('portfolio_adjustments', JSONB(), nullable=True),
        sa.Column('next_cycle_recommendations', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='finalized'),
        sa.Column('reviewed_by', sa.UUID(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['cycle_id'], ['twelve_week_cycles.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cycle_id', name='uix_cycle_review_cycle')
    )
    op.create_index(op.f('ix_cycle_reviews_cycle_id'), 'cycle_reviews', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_cycle_reviews_reviewed_by'), 'cycle_reviews', ['reviewed_by'], unique=False)
    op.create_index(op.f('ix_cycle_reviews_workspace_id'), 'cycle_reviews', ['workspace_id'], unique=False)

    # 3. celebration_records
    op.create_table(
        'celebration_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('cycle_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('milestones_achieved', JSONB(), nullable=True),
        sa.Column('top_performers_recognized', JSONB(), nullable=True),
        sa.Column('rewards_or_rituals', sa.Text(), nullable=True),
        sa.Column('reflection_notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('celebrated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['cycle_id'], ['twelve_week_cycles.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_celebration_records_created_by'), 'celebration_records', ['created_by'], unique=False)
    op.create_index(op.f('ix_celebration_records_cycle_id'), 'celebration_records', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_celebration_records_workspace_id'), 'celebration_records', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('celebration_records')
    op.drop_table('cycle_reviews')
    op.drop_table('weekly_reviews')
