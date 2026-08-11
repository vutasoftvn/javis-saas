"""mcosa v12 sprint 6 portfolio intelligence detector shared pestel impact matrix

Revision ID: v12_005_sprint6
Revises: v12_004_sprint5
Create Date: 2026-08-11 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'v12_005_sprint6'
down_revision: Union[str, Sequence[str], None] = 'v12_004_sprint5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. portfolios table
    op.create_table(
        'portfolios',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('brain_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strategic_focus', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['brain_id'], ['brains.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolios_brain_id'), 'portfolios', ['brain_id'], unique=False)
    op.create_index(op.f('ix_portfolios_workspace_id'), 'portfolios', ['workspace_id'], unique=False)

    # 2. portfolio_projects table
    op.create_table(
        'portfolio_projects',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('portfolio_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('strategic_priority', sa.String(length=50), nullable=False, server_default='core'),
        sa.Column('capacity_allocation', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('founder_attention_hours', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('portfolio_id', 'project_id', name='uix_portfolio_project')
    )
    op.create_index(op.f('ix_portfolio_projects_portfolio_id'), 'portfolio_projects', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_portfolio_projects_project_id'), 'portfolio_projects', ['project_id'], unique=False)
    op.create_index(op.f('ix_portfolio_projects_workspace_id'), 'portfolio_projects', ['workspace_id'], unique=False)

    # 3. Add portfolio_id column to existing analyses
    op.add_column('strategy_analyses', sa.Column('portfolio_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_strategy_analyses_portfolio_id'), 'strategy_analyses', ['portfolio_id'], unique=False)

    op.add_column('pestel_items', sa.Column('portfolio_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_pestel_items_portfolio_id'), 'pestel_items', ['portfolio_id'], unique=False)

    op.add_column('swot_items', sa.Column('portfolio_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_swot_items_portfolio_id'), 'swot_items', ['portfolio_id'], unique=False)

    op.add_column('tows_options', sa.Column('portfolio_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_tows_options_portfolio_id'), 'tows_options', ['portfolio_id'], unique=False)

    # 4. project_pestel_impacts table
    op.create_table(
        'project_pestel_impacts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('pestel_item_id', sa.UUID(), nullable=False),
        sa.Column('impact_type', sa.String(length=50), nullable=False, server_default='POSITIVE'),
        sa.Column('impact_magnitude', sa.String(length=50), nullable=False, server_default='MEDIUM'),
        sa.Column('impact_analysis', sa.Text(), nullable=True),
        sa.Column('mitigation_or_leverage', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['pestel_item_id'], ['pestel_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'pestel_item_id', name='uix_project_pestel_impact')
    )
    op.create_index(op.f('ix_project_pestel_impacts_pestel_item_id'), 'project_pestel_impacts', ['pestel_item_id'], unique=False)
    op.create_index(op.f('ix_project_pestel_impacts_project_id'), 'project_pestel_impacts', ['project_id'], unique=False)
    op.create_index(op.f('ix_project_pestel_impacts_workspace_id'), 'project_pestel_impacts', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('project_pestel_impacts')
    op.drop_index(op.f('ix_tows_options_portfolio_id'), table_name='tows_options')
    op.drop_column('tows_options', 'portfolio_id')
    op.drop_index(op.f('ix_swot_items_portfolio_id'), table_name='swot_items')
    op.drop_column('swot_items', 'portfolio_id')
    op.drop_index(op.f('ix_pestel_items_portfolio_id'), table_name='pestel_items')
    op.drop_column('pestel_items', 'portfolio_id')
    op.drop_index(op.f('ix_strategy_analyses_portfolio_id'), table_name='strategy_analyses')
    op.drop_column('strategy_analyses', 'portfolio_id')
    op.drop_table('portfolio_projects')
    op.drop_table('portfolios')
