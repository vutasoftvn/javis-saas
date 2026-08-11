"""mcosa v12 sprint 2 analysis imports

Revision ID: v12_002_sprint2
Revises: v12_001_sprint1
Create Date: 2026-08-11 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'v12_002_sprint2'
down_revision: Union[str, Sequence[str], None] = 'v12_001_sprint1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'analysis_imports',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('strategy_revision_id', sa.Uuid(), nullable=True),
        sa.Column('raw_input', sa.Text(), nullable=False),
        sa.Column('parsed_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('schema_version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('imported_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['imported_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['strategy_revision_id'], ['strategy_revisions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_imports_project_id'), 'analysis_imports', ['project_id'], unique=False)
    op.create_index(op.f('ix_analysis_imports_strategy_revision_id'), 'analysis_imports', ['strategy_revision_id'], unique=False)
    op.create_index(op.f('ix_analysis_imports_workspace_id'), 'analysis_imports', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_analysis_imports_workspace_id'), table_name='analysis_imports')
    op.drop_index(op.f('ix_analysis_imports_strategy_revision_id'), table_name='analysis_imports')
    op.drop_index(op.f('ix_analysis_imports_project_id'), table_name='analysis_imports')
    op.drop_table('analysis_imports')
