"""add outcomes artifacts schema

Revision ID: f4a8c1d9e3b7
Revises: mkt002b3c4d5e
Create Date: 2026-08-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f4a8c1d9e3b7'
down_revision: Union[str, Sequence[str], None] = 'mkt002b3c4d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('outcomes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('workspace_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('desired_result', sa.Text(), nullable=False),
    sa.Column('acceptance_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('requested_by', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_outcomes_workspace_id'), 'outcomes', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_outcomes_project_id'), 'outcomes', ['project_id'], unique=False)
    op.create_index(op.f('ix_outcomes_requested_by'), 'outcomes', ['requested_by'], unique=False)

    op.create_table('outcome_runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('outcome_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['outcome_id'], ['outcomes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_outcome_runs_outcome_id'), 'outcome_runs', ['outcome_id'], unique=False)

    op.create_table('run_steps',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('run_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('inputs_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('expected_output', sa.Text(), nullable=True),
    sa.Column('risk_level', sa.String(length=20), nullable=False),
    sa.Column('depends_on_step_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['outcome_runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_run_steps_run_id'), 'run_steps', ['run_id'], unique=False)

    op.create_table('run_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('run_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sa.String(length=100), nullable=False),
    sa.Column('payload_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['outcome_runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_run_events_run_id'), 'run_events', ['run_id'], unique=False)

    op.create_table('artifacts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('run_id', sa.Uuid(), nullable=True),
    sa.Column('outcome_id', sa.Uuid(), nullable=True),
    sa.Column('workspace_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('local_uri', sa.String(length=500), nullable=True),
    sa.Column('object_storage_uri', sa.String(length=500), nullable=True),
    sa.Column('content_hash', sa.String(length=64), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['outcome_id'], ['outcomes.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['outcome_runs.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_artifacts_run_id'), 'artifacts', ['run_id'], unique=False)
    op.create_index(op.f('ix_artifacts_outcome_id'), 'artifacts', ['outcome_id'], unique=False)
    op.create_index(op.f('ix_artifacts_workspace_id'), 'artifacts', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_artifacts_created_by'), 'artifacts', ['created_by'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_artifacts_created_by'), table_name='artifacts')
    op.drop_index(op.f('ix_artifacts_workspace_id'), table_name='artifacts')
    op.drop_index(op.f('ix_artifacts_outcome_id'), table_name='artifacts')
    op.drop_index(op.f('ix_artifacts_run_id'), table_name='artifacts')
    op.drop_table('artifacts')

    op.drop_index(op.f('ix_run_events_run_id'), table_name='run_events')
    op.drop_table('run_events')

    op.drop_index(op.f('ix_run_steps_run_id'), table_name='run_steps')
    op.drop_table('run_steps')

    op.drop_index(op.f('ix_outcome_runs_outcome_id'), table_name='outcome_runs')
    op.drop_table('outcome_runs')

    op.drop_index(op.f('ix_outcomes_requested_by'), table_name='outcomes')
    op.drop_index(op.f('ix_outcomes_project_id'), table_name='outcomes')
    op.drop_index(op.f('ix_outcomes_workspace_id'), table_name='outcomes')
    op.drop_table('outcomes')
