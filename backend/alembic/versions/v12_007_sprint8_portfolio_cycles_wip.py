"""mcosa v12 sprint 8 portfolio cycles wip limit founder attention

Revision ID: v12_007_sprint8
Revises: v12_006_sprint7
Create Date: 2026-08-11 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'v12_007_sprint8'
down_revision: Union[str, Sequence[str], None] = 'v12_006_sprint7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. founder_profiles
    op.create_table(
        'founder_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('weekly_capacity_hours', sa.Float(), nullable=False, server_default='40.0'),
        sa.Column('max_active_strategic_projects', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uix_founder_profile_workspace_user')
    )
    op.create_index(op.f('ix_founder_profiles_user_id'), 'founder_profiles', ['user_id'], unique=False)
    op.create_index(op.f('ix_founder_profiles_workspace_id'), 'founder_profiles', ['workspace_id'], unique=False)

    # 2. portfolio_cycles
    op.create_table(
        'portfolio_cycles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('portfolio_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('start_date', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('end_date', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('active_project_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolio_cycles_portfolio_id'), 'portfolio_cycles', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_portfolio_cycles_workspace_id'), 'portfolio_cycles', ['workspace_id'], unique=False)

    # 3. capacity_allocations
    op.create_table(
        'capacity_allocations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('portfolio_cycle_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('allocated_percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_cycle_id'], ['portfolio_cycles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_capacity_allocations_portfolio_cycle_id'), 'capacity_allocations', ['portfolio_cycle_id'], unique=False)
    op.create_index(op.f('ix_capacity_allocations_project_id'), 'capacity_allocations', ['project_id'], unique=False)
    op.create_index(op.f('ix_capacity_allocations_workspace_id'), 'capacity_allocations', ['workspace_id'], unique=False)

    # 4. founder_attention_allocations
    op.create_table(
        'founder_attention_allocations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('portfolio_cycle_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('allocated_hours_per_week', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_cycle_id'], ['portfolio_cycles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_founder_attention_allocations_portfolio_cycle_id'), 'founder_attention_allocations', ['portfolio_cycle_id'], unique=False)
    op.create_index(op.f('ix_founder_attention_allocations_project_id'), 'founder_attention_allocations', ['project_id'], unique=False)
    op.create_index(op.f('ix_founder_attention_allocations_workspace_id'), 'founder_attention_allocations', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('founder_attention_allocations')
    op.drop_table('capacity_allocations')
    op.drop_table('portfolio_cycles')
    op.drop_table('founder_profiles')
