"""vault_documents just-in-time coaching metadata (Supplement §20)

Revision ID: v13_062_vault_document_metadata
Revises: v13_061_mission_resume_jobs
Create Date: 2026-08-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'v13_062_vault_document_metadata'
down_revision = 'v13_061_mission_resume_jobs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('vault_documents', sa.Column('stage', sa.String(length=50), nullable=True))
    op.add_column('vault_documents', sa.Column('dimension', sa.String(length=50), nullable=True))
    op.add_column(
        'vault_documents',
        sa.Column('regulatory_sensitivity', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column('vault_documents', sa.Column('source_version', sa.String(length=100), nullable=True))
    op.add_column('vault_documents', sa.Column('last_verified', sa.Date(), nullable=True))
    op.create_index(op.f('ix_vault_documents_stage'), 'vault_documents', ['stage'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_vault_documents_stage'), table_name='vault_documents')
    op.drop_column('vault_documents', 'last_verified')
    op.drop_column('vault_documents', 'source_version')
    op.drop_column('vault_documents', 'regulatory_sensitivity')
    op.drop_column('vault_documents', 'dimension')
    op.drop_column('vault_documents', 'stage')
