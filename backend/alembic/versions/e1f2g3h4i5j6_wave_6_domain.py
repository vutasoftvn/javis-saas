"""wave 6 domain

Revision ID: e1f2g3h4i5j6
Revises: d1e2f3g4h5i6
Create Date: 2026-08-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e1f2g3h4i5j6'
down_revision = 'd1e2f3g4h5i6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('workspace_domains',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('domain', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspace_domains_domain'), 'workspace_domains', ['domain'], unique=True)
    op.create_index(op.f('ix_workspace_domains_workspace_id'), 'workspace_domains', ['workspace_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_workspace_domains_workspace_id'), table_name='workspace_domains')
    op.drop_index(op.f('ix_workspace_domains_domain'), table_name='workspace_domains')
    op.drop_table('workspace_domains')
