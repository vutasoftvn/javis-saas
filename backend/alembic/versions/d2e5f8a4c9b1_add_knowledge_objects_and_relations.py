"""add knowledge objects and relations

Revision ID: d2e5f8a4c9b1
Revises: c7b3e9a1f6d2
Create Date: 2026-08-11 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd2e5f8a4c9b1'
down_revision: Union[str, Sequence[str], None] = 'c7b3e9a1f6d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('knowledge_objects',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('workspace_id', sa.Uuid(), nullable=False),
    sa.Column('brain_id', sa.Uuid(), nullable=False),
    sa.Column('vault_document_id', sa.Uuid(), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('object_type', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('source_hash', sa.String(length=64), nullable=True),
    sa.Column('generated_by', sa.Uuid(), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['brain_id'], ['brains.id'], ),
    sa.ForeignKeyConstraint(['vault_document_id'], ['vault_documents.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_objects_workspace_id'), 'knowledge_objects', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_knowledge_objects_brain_id'), 'knowledge_objects', ['brain_id'], unique=False)
    op.create_index(op.f('ix_knowledge_objects_vault_document_id'), 'knowledge_objects', ['vault_document_id'], unique=False)

    op.create_table('knowledge_relations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('from_object_id', sa.Uuid(), nullable=False),
    sa.Column('to_object_id', sa.Uuid(), nullable=False),
    sa.Column('relation_type', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['from_object_id'], ['knowledge_objects.id'], ),
    sa.ForeignKeyConstraint(['to_object_id'], ['knowledge_objects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_relations_from_object_id'), 'knowledge_relations', ['from_object_id'], unique=False)
    op.create_index(op.f('ix_knowledge_relations_to_object_id'), 'knowledge_relations', ['to_object_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_knowledge_relations_to_object_id'), table_name='knowledge_relations')
    op.drop_index(op.f('ix_knowledge_relations_from_object_id'), table_name='knowledge_relations')
    op.drop_table('knowledge_relations')

    op.drop_index(op.f('ix_knowledge_objects_vault_document_id'), table_name='knowledge_objects')
    op.drop_index(op.f('ix_knowledge_objects_brain_id'), table_name='knowledge_objects')
    op.drop_index(op.f('ix_knowledge_objects_workspace_id'), table_name='knowledge_objects')
    op.drop_table('knowledge_objects')
