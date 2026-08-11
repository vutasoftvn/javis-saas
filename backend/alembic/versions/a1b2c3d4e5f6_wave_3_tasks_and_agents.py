"""wave 3 tasks and agents

Revision ID: a1b2c3d4e5f6
Revises: d3f8a1c9b6e2
Create Date: 2026-08-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd3f8a1c9b6e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sort_key to tasks
    op.add_column('tasks', sa.Column('sort_key', sa.Float(), nullable=True))
    
    # Create agents table
    op.create_table('agents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'slug', name='uix_agent_workspace_slug')
    )
    op.create_index(op.f('ix_agents_workspace_id'), 'agents', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_agents_workspace_id'), table_name='agents')
    op.drop_table('agents')
    op.drop_column('tasks', 'sort_key')
