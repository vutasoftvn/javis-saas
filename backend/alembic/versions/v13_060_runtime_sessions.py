"""runtime sessions

Revision ID: v13_060_runtime_sessions
Revises: c8e01c5a0008
Create Date: 2026-08-21 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'v13_060_runtime_sessions'
down_revision = 'c8e01c5a0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'runtime_sessions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('mission_run_id', sa.BigInteger(), nullable=False),
        sa.Column('agent_run_id', sa.BigInteger(), nullable=True),
        sa.Column('runtime_type', sa.String(length=30), nullable=False),
        sa.Column('external_session_id', sa.String(length=255), nullable=True),
        sa.Column('parent_session_id', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='active'),
        sa.Column('checkpoint_ref', sa.String(length=255), nullable=True),
        sa.Column('metadata_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['mission_run_id'], ['agent_runs.id']),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id']),
        sa.ForeignKeyConstraint(['parent_session_id'], ['runtime_sessions.id'], use_alter=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_runtime_sessions_workspace_id', 'runtime_sessions', ['workspace_id'])
    op.create_index('ix_runtime_sessions_mission_run_id', 'runtime_sessions', ['mission_run_id'])
    op.create_index('ix_runtime_sessions_agent_run_id', 'runtime_sessions', ['agent_run_id'])
    op.create_index('ix_runtime_sessions_external_session_id', 'runtime_sessions', ['external_session_id'])
    op.create_index('ix_runtime_sessions_parent_session_id', 'runtime_sessions', ['parent_session_id'])
    op.create_index('ix_runtime_sessions_mission_status', 'runtime_sessions', ['mission_run_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_runtime_sessions_mission_status', table_name='runtime_sessions')
    op.drop_index('ix_runtime_sessions_parent_session_id', table_name='runtime_sessions')
    op.drop_index('ix_runtime_sessions_external_session_id', table_name='runtime_sessions')
    op.drop_index('ix_runtime_sessions_agent_run_id', table_name='runtime_sessions')
    op.drop_index('ix_runtime_sessions_mission_run_id', table_name='runtime_sessions')
    op.drop_index('ix_runtime_sessions_workspace_id', table_name='runtime_sessions')
    op.drop_table('runtime_sessions')
