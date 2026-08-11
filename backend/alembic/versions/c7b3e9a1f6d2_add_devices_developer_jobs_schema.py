"""add devices developer jobs schema

Revision ID: c7b3e9a1f6d2
Revises: f4a8c1d9e3b7
Create Date: 2026-08-11 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7b3e9a1f6d2'
down_revision: Union[str, Sequence[str], None] = 'f4a8c1d9e3b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('devices',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('workspace_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('platform', sa.String(length=50), nullable=False),
    sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('allowed_projects', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('trust_level', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('last_seen', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_devices_workspace_id'), 'devices', ['workspace_id'], unique=False)

    op.create_table('device_credentials',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('is_revoked', sa.Boolean(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_device_credentials_device_id'), 'device_credentials', ['device_id'], unique=False)
    op.create_index(op.f('ix_device_credentials_token_hash'), 'device_credentials', ['token_hash'], unique=True)

    op.create_table('developer_jobs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('workspace_id', sa.Uuid(), nullable=False),
    sa.Column('outcome_id', sa.Uuid(), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('required_capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('assigned_device_id', sa.Uuid(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('worktree_path', sa.String(length=500), nullable=True),
    sa.Column('diff_summary', sa.Text(), nullable=True),
    sa.Column('test_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['assigned_device_id'], ['devices.id'], ),
    sa.ForeignKeyConstraint(['outcome_id'], ['outcomes.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_developer_jobs_workspace_id'), 'developer_jobs', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_developer_jobs_outcome_id'), 'developer_jobs', ['outcome_id'], unique=False)
    op.create_index(op.f('ix_developer_jobs_assigned_device_id'), 'developer_jobs', ['assigned_device_id'], unique=False)

    op.create_table('job_leases',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('job_id', sa.Uuid(), nullable=False),
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('worker_id', sa.String(length=100), nullable=False),
    sa.Column('lease_until', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.ForeignKeyConstraint(['job_id'], ['developer_jobs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_leases_job_id'), 'job_leases', ['job_id'], unique=False)
    op.create_index(op.f('ix_job_leases_device_id'), 'job_leases', ['device_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_job_leases_device_id'), table_name='job_leases')
    op.drop_index(op.f('ix_job_leases_job_id'), table_name='job_leases')
    op.drop_table('job_leases')

    op.drop_index(op.f('ix_developer_jobs_assigned_device_id'), table_name='developer_jobs')
    op.drop_index(op.f('ix_developer_jobs_outcome_id'), table_name='developer_jobs')
    op.drop_index(op.f('ix_developer_jobs_workspace_id'), table_name='developer_jobs')
    op.drop_table('developer_jobs')

    op.drop_index(op.f('ix_device_credentials_token_hash'), table_name='device_credentials')
    op.drop_index(op.f('ix_device_credentials_device_id'), table_name='device_credentials')
    op.drop_table('device_credentials')

    op.drop_index(op.f('ix_devices_workspace_id'), table_name='devices')
    op.drop_table('devices')
