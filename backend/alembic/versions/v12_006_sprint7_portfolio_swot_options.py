"""mcosa v12 sprint 7 portfolio swot options synergies dependencies

Revision ID: v12_006_sprint7
Revises: v12_005_sprint6
Create Date: 2026-08-11 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'v12_006_sprint7'
down_revision: Union[str, Sequence[str], None] = 'v12_005_sprint6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. portfolio_synergies
    op.create_table(
        'portfolio_synergies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('portfolio_id', sa.UUID(), nullable=False),
        sa.Column('source_project_id', sa.UUID(), nullable=False),
        sa.Column('target_project_id', sa.UUID(), nullable=False),
        sa.Column('synergy_type', sa.String(length=50), nullable=False, server_default='SHARED_CAPABILITY'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('estimated_value', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='identified'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolio_synergies_portfolio_id'), 'portfolio_synergies', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_portfolio_synergies_source_project_id'), 'portfolio_synergies', ['source_project_id'], unique=False)
    op.create_index(op.f('ix_portfolio_synergies_target_project_id'), 'portfolio_synergies', ['target_project_id'], unique=False)
    op.create_index(op.f('ix_portfolio_synergies_workspace_id'), 'portfolio_synergies', ['workspace_id'], unique=False)

    # 2. portfolio_dependencies
    op.create_table(
        'portfolio_dependencies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('portfolio_id', sa.UUID(), nullable=False),
        sa.Column('predecessor_project_id', sa.UUID(), nullable=False),
        sa.Column('successor_project_id', sa.UUID(), nullable=False),
        sa.Column('dependency_type', sa.String(length=50), nullable=False, server_default='BLOCKS'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['predecessor_project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['successor_project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolio_dependencies_portfolio_id'), 'portfolio_dependencies', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_portfolio_dependencies_predecessor_project_id'), 'portfolio_dependencies', ['predecessor_project_id'], unique=False)
    op.create_index(op.f('ix_portfolio_dependencies_successor_project_id'), 'portfolio_dependencies', ['successor_project_id'], unique=False)
    op.create_index(op.f('ix_portfolio_dependencies_workspace_id'), 'portfolio_dependencies', ['workspace_id'], unique=False)

    # 3. portfolio_options
    op.create_table(
        'portfolio_options',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('portfolio_id', sa.UUID(), nullable=False),
        sa.Column('tows_option_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strategic_fit_score', sa.Float(), nullable=False, server_default='0.8'),
        sa.Column('feasibility_score', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('risk_level', sa.String(length=50), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tows_option_id'], ['tows_options.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolio_options_portfolio_id'), 'portfolio_options', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_portfolio_options_workspace_id'), 'portfolio_options', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('portfolio_options')
    op.drop_table('portfolio_dependencies')
    op.drop_table('portfolio_synergies')
