"""mcosa v12 sprint 1 domain schema

Revision ID: v12_001_sprint1
Revises: e8f1a7c3d5b9
Create Date: 2026-08-11 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'v12_001_sprint1'
down_revision: Union[str, Sequence[str], None] = 'e8f1a7c3d5b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Feature flags table
    op.create_table(
        'feature_flags',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=True),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'key', name='uix_feature_flag_workspace_key')
    )
    op.create_index(op.f('ix_feature_flags_key'), 'feature_flags', ['key'], unique=False)
    op.create_index(op.f('ix_feature_flags_workspace_id'), 'feature_flags', ['workspace_id'], unique=False)

    # 2. Add columns to projects table
    op.add_column('projects', sa.Column('project_type', sa.String(length=50), nullable=True))
    op.add_column('projects', sa.Column('strategic_priority', sa.String(length=50), nullable=True))
    op.add_column('projects', sa.Column('founder_attention_budget', sa.Float(), nullable=True))
    op.add_column('projects', sa.Column('portfolio_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_projects_portfolio_id'), 'projects', ['portfolio_id'], unique=False)

    # 3. Project classifications table
    op.create_table(
        'project_classifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('project_type', sa.String(length=50), nullable=False),
        sa.Column('strategic_depth', sa.String(length=50), nullable=True),
        sa.Column('uncertainty_level', sa.String(length=50), nullable=True),
        sa.Column('risk_level', sa.String(length=50), nullable=True),
        sa.Column('research_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('external_evidence_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('internal_context_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('recommended_methodologies', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('human_required_areas', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('classified_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['classified_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_classifications_project_id'), 'project_classifications', ['project_id'], unique=False)
    op.create_index(op.f('ix_project_classifications_workspace_id'), 'project_classifications', ['workspace_id'], unique=False)

    # 4. Methodology plans table
    op.create_table(
        'methodology_plans',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('selected_methodologies', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('custom_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_methodology_plans_project_id'), 'methodology_plans', ['project_id'], unique=False)
    op.create_index(op.f('ix_methodology_plans_workspace_id'), 'methodology_plans', ['workspace_id'], unique=False)

    # 5. Cycle contracts table
    op.create_table(
        'cycle_contracts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('cycle_id', sa.Uuid(), nullable=False),
        sa.Column('success_definition', sa.Text(), nullable=False),
        sa.Column('goal_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('kr_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('founder_capacity_per_week', sa.Float(), nullable=True),
        sa.Column('reserved_buffer_percent', sa.Float(), nullable=True),
        sa.Column('ai_budget', sa.Float(), nullable=True),
        sa.Column('operating_budget', sa.Float(), nullable=True),
        sa.Column('risk_constraints', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('approved_by', sa.Uuid(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['cycle_id'], ['twelve_week_cycles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cycle_id', name='uix_cycle_contract_cycle_id')
    )
    op.create_index(op.f('ix_cycle_contracts_cycle_id'), 'cycle_contracts', ['cycle_id'], unique=True)
    op.create_index(op.f('ix_cycle_contracts_workspace_id'), 'cycle_contracts', ['workspace_id'], unique=False)

    # 6. Add cycle_contract_id to twelve_week_cycles
    op.add_column('twelve_week_cycles', sa.Column('cycle_contract_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_twelve_week_cycles_cycle_contract_id', 'twelve_week_cycles', 'cycle_contracts', ['cycle_contract_id'], ['id'], use_alter=True)
    op.create_index(op.f('ix_twelve_week_cycles_cycle_contract_id'), 'twelve_week_cycles', ['cycle_contract_id'], unique=False)

    # 7. Cycle stages table
    op.create_table(
        'cycle_stages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('cycle_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=True),
        sa.Column('start_week', sa.Integer(), nullable=False),
        sa.Column('end_week', sa.Integer(), nullable=False),
        sa.Column('order_no', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('expected_outcomes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['cycle_id'], ['twelve_week_cycles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cycle_id', 'order_no', name='uix_cycle_stage_cycle_order')
    )
    op.create_index(op.f('ix_cycle_stages_cycle_id'), 'cycle_stages', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_cycle_stages_workspace_id'), 'cycle_stages', ['workspace_id'], unique=False)

    # 8. Add columns to weekly_plans
    op.add_column('weekly_plans', sa.Column('stage_id', sa.Uuid(), nullable=True))
    op.add_column('weekly_plans', sa.Column('mission', sa.Text(), nullable=True))
    op.add_column('weekly_plans', sa.Column('success_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('weekly_plans', sa.Column('outcome_score', sa.Float(), nullable=True))
    op.create_foreign_key('fk_weekly_plans_stage_id', 'weekly_plans', 'cycle_stages', ['stage_id'], ['id'])
    op.create_index(op.f('ix_weekly_plans_stage_id'), 'weekly_plans', ['stage_id'], unique=False)

    # 9. Milestones table
    op.create_table(
        'milestones',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('cycle_id', sa.Uuid(), nullable=True),
        sa.Column('stage_id', sa.Uuid(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_week', sa.Integer(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('required_artifacts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('required_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('acceptance_criteria', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['cycle_id'], ['twelve_week_cycles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stage_id'], ['cycle_stages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_milestones_cycle_id'), 'milestones', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_milestones_project_id'), 'milestones', ['project_id'], unique=False)
    op.create_index(op.f('ix_milestones_stage_id'), 'milestones', ['stage_id'], unique=False)
    op.create_index(op.f('ix_milestones_workspace_id'), 'milestones', ['workspace_id'], unique=False)

    # 10. Milestone evidence join table
    op.create_table(
        'milestone_evidence',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('milestone_id', sa.Uuid(), nullable=False),
        sa.Column('evidence_id', sa.Uuid(), nullable=False),
        sa.Column('relevance_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['milestone_id'], ['milestones.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('milestone_id', 'evidence_id', name='uix_milestone_evidence_milestone_evidence')
    )
    op.create_index(op.f('ix_milestone_evidence_evidence_id'), 'milestone_evidence', ['evidence_id'], unique=False)
    op.create_index(op.f('ix_milestone_evidence_milestone_id'), 'milestone_evidence', ['milestone_id'], unique=False)
    op.create_index(op.f('ix_milestone_evidence_workspace_id'), 'milestone_evidence', ['workspace_id'], unique=False)

    # 11. Gate decisions table
    op.create_table(
        'gate_decisions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('milestone_id', sa.Uuid(), nullable=True),
        sa.Column('stage_id', sa.Uuid(), nullable=True),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('evidence_summary', sa.Text(), nullable=True),
        sa.Column('evidence_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('next_step_instructions', sa.Text(), nullable=True),
        sa.Column('decided_by', sa.Uuid(), nullable=False),
        sa.Column('decided_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['decided_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['milestone_id'], ['milestones.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stage_id'], ['cycle_stages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gate_decisions_milestone_id'), 'gate_decisions', ['milestone_id'], unique=False)
    op.create_index(op.f('ix_gate_decisions_project_id'), 'gate_decisions', ['project_id'], unique=False)
    op.create_index(op.f('ix_gate_decisions_stage_id'), 'gate_decisions', ['stage_id'], unique=False)
    op.create_index(op.f('ix_gate_decisions_workspace_id'), 'gate_decisions', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('gate_decisions')
    op.drop_table('milestone_evidence')
    op.drop_table('milestones')
    op.drop_constraint('fk_weekly_plans_stage_id', 'weekly_plans', type_='foreignkey')
    op.drop_index(op.f('ix_weekly_plans_stage_id'), table_name='weekly_plans')
    op.drop_column('weekly_plans', 'outcome_score')
    op.drop_column('weekly_plans', 'success_criteria')
    op.drop_column('weekly_plans', 'mission')
    op.drop_column('weekly_plans', 'stage_id')
    op.drop_table('cycle_stages')
    op.drop_constraint('fk_twelve_week_cycles_cycle_contract_id', 'twelve_week_cycles', type_='foreignkey')
    op.drop_index(op.f('ix_twelve_week_cycles_cycle_contract_id'), table_name='twelve_week_cycles')
    op.drop_column('twelve_week_cycles', 'cycle_contract_id')
    op.drop_table('cycle_contracts')
    op.drop_table('methodology_plans')
    op.drop_table('project_classifications')
    op.drop_index(op.f('ix_projects_portfolio_id'), table_name='projects')
    op.drop_column('projects', 'portfolio_id')
    op.drop_column('projects', 'founder_attention_budget')
    op.drop_column('projects', 'strategic_priority')
    op.drop_column('projects', 'project_type')
    op.drop_table('feature_flags')
