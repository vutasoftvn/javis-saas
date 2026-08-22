"""workflow scope snapshots

Revision ID: v13_059
Revises: v13_058
Create Date: 2026-08-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'v13_059_workflow_scope_snapshots'
down_revision = 'v13_058_company_portfolio_scope'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('workflow_definitions', sa.Column('scope_binding_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('workflow_versions', sa.Column('scope_requirements_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('workflow_runs', sa.Column('scope_snapshot_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('workflow_approvals', sa.Column('scope_snapshot_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('artifacts', sa.Column('scope_snapshot_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

def downgrade() -> None:
    op.drop_column('artifacts', 'scope_snapshot_jsonb')
    op.drop_column('workflow_approvals', 'scope_snapshot_jsonb')
    op.drop_column('workflow_runs', 'scope_snapshot_jsonb')
    op.drop_column('workflow_versions', 'scope_requirements_jsonb')
    op.drop_column('workflow_definitions', 'scope_binding_jsonb')
