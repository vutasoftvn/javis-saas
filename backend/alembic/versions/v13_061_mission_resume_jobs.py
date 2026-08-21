"""mission resume jobs

Revision ID: v13_061_mission_resume_jobs
Revises: v13_060_runtime_sessions
Create Date: 2026-08-21 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'v13_061_mission_resume_jobs'
down_revision = 'v13_060_runtime_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'mission_resume_jobs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('mission_run_id', sa.BigInteger(), nullable=False),
        sa.Column('workflow_session_id', sa.String(length=255), nullable=True),
        sa.Column('checkpoint_key', sa.String(length=255), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='queued'),
        sa.Column('claimed_by', sa.String(length=100), nullable=True),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['mission_run_id'], ['agent_runs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mission_run_id', 'checkpoint_key', name='uq_mission_resume_job_mission_checkpoint'),
    )
    op.create_index('ix_mission_resume_jobs_workspace_id', 'mission_resume_jobs', ['workspace_id'])
    op.create_index('ix_mission_resume_jobs_mission_run_id', 'mission_resume_jobs', ['mission_run_id'])
    op.create_index('ix_mission_resume_jobs_status_created', 'mission_resume_jobs', ['status', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_mission_resume_jobs_status_created', table_name='mission_resume_jobs')
    op.drop_index('ix_mission_resume_jobs_mission_run_id', table_name='mission_resume_jobs')
    op.drop_index('ix_mission_resume_jobs_workspace_id', table_name='mission_resume_jobs')
    op.drop_table('mission_resume_jobs')
