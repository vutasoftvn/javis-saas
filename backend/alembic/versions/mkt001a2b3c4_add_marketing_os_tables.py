"""add_marketing_os_tables - Marketing Context, Objectives, Campaigns, Experiments, Skill Registry, Pending Approvals

Revision ID: mkt001a2b3c4
Revises: f2a7c1d4e8b3
Create Date: 2026-08-10 20:19:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'mkt001a2b3c4'
down_revision = 'f2a7c1d4e8b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # marketing_contexts
    op.create_table(
        'marketing_contexts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('brain_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('strategy_revision_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('icp', postgresql.JSONB(), nullable=True),
        sa.Column('personas', postgresql.JSONB(), nullable=True),
        sa.Column('jobs_to_be_done', postgresql.JSONB(), nullable=True),
        sa.Column('positioning', postgresql.JSONB(), nullable=True),
        sa.Column('value_proposition', postgresql.JSONB(), nullable=True),
        sa.Column('brand_voice', postgresql.JSONB(), nullable=True),
        sa.Column('competitors', postgresql.JSONB(), nullable=True),
        sa.Column('pricing', postgresql.JSONB(), nullable=True),
        sa.Column('constraints', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_marketing_contexts_workspace_id', 'marketing_contexts', ['workspace_id'])

    # marketing_objectives
    op.create_table(
        'marketing_objectives',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('brain_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('strategic_objective_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_metric', sa.String(100), nullable=False),
        sa.Column('target_value', sa.Float(), nullable=False, server_default='0'),
        sa.Column('current_value', sa.Float(), nullable=False, server_default='0'),
        sa.Column('unit', sa.String(50), nullable=False, server_default='count'),
        sa.Column('period_weeks', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_marketing_objectives_workspace_id', 'marketing_objectives', ['workspace_id'])

    # marketing_campaigns
    op.create_table(
        'marketing_campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('brain_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('marketing_objective_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('funnel_stage', sa.String(50), nullable=False, server_default='discover'),
        sa.Column('channels', postgresql.JSONB(), nullable=True),
        sa.Column('budget', sa.Float(), nullable=False, server_default='0'),
        sa.Column('owner', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_marketing_campaigns_workspace_id', 'marketing_campaigns', ['workspace_id'])

    # campaign_assets
    op.create_table(
        'campaign_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('marketing_campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    # marketing_metrics
    op.create_table(
        'marketing_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('brain_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False, server_default='0'),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('period', sa.String(20), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    # metric_snapshots
    op.create_table(
        'metric_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('snapshot_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    # marketing_experiments
    op.create_table(
        'marketing_experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('brain_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('hypothesis', sa.Text(), nullable=False),
        sa.Column('metric', sa.String(100), nullable=False),
        sa.Column('baseline_value', sa.Float(), nullable=False, server_default='0'),
        sa.Column('target_value', sa.Float(), nullable=False, server_default='0'),
        sa.Column('variant_a', sa.String(255), nullable=False),
        sa.Column('variant_b', sa.String(255), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('decision', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_marketing_experiments_workspace_id', 'marketing_experiments', ['workspace_id'])

    # marketing_learnings
    op.create_table(
        'marketing_learnings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('brain_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('insight', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('impact_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    # skill_registries
    op.create_table(
        'skill_registries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('capability_id', sa.String(100), nullable=False),
        sa.Column('primary_provider', postgresql.JSONB(), nullable=False),
        sa.Column('fallback_provider', postgresql.JSONB(), nullable=True),
        sa.Column('permissions', postgresql.JSONB(), nullable=True),
        sa.Column('quality_gate', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('workspace_id', 'capability_id', name='uq_skill_registry_workspace_capability'),
    )
    op.create_index('ix_skill_registries_workspace_id', 'skill_registries', ['workspace_id'])

    # pending_approvals
    op.create_table(
        'pending_approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('brain_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('requested_by_agent', sa.String(100), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_pending_approvals_workspace_id', 'pending_approvals', ['workspace_id'])
    op.create_index('ix_pending_approvals_status', 'pending_approvals', ['status'])


def downgrade() -> None:
    op.drop_table('pending_approvals')
    op.drop_table('skill_registries')
    op.drop_table('marketing_learnings')
    op.drop_table('marketing_experiments')
    op.drop_table('metric_snapshots')
    op.drop_table('marketing_metrics')
    op.drop_table('campaign_assets')
    op.drop_table('marketing_campaigns')
    op.drop_table('marketing_objectives')
    op.drop_table('marketing_contexts')
