"""wave 5 chatbots

Revision ID: d1e2f3g4h5i6
Revises: c1d2e3f4g5h6
Create Date: 2026-08-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd1e2f3g4h5i6'
down_revision = 'c1d2e3f4g5h6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('chatbots',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('agent_id', sa.UUID(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('channel', sa.String(length=50), nullable=False),
    sa.Column('channel_config_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chatbots_workspace_id'), 'chatbots', ['workspace_id'], unique=False)
    
    op.create_table('chatbot_conversations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('chatbot_id', sa.UUID(), nullable=False),
    sa.Column('external_user_id', sa.String(length=255), nullable=False),
    sa.Column('context_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['chatbot_id'], ['chatbots.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chatbot_conversations_chatbot_id'), 'chatbot_conversations', ['chatbot_id'], unique=False)
    op.create_index(op.f('ix_chatbot_conversations_external_user_id'), 'chatbot_conversations', ['external_user_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_chatbot_conversations_external_user_id'), table_name='chatbot_conversations')
    op.drop_index(op.f('ix_chatbot_conversations_chatbot_id'), table_name='chatbot_conversations')
    op.drop_table('chatbot_conversations')
    op.drop_index(op.f('ix_chatbots_workspace_id'), table_name='chatbots')
    op.drop_table('chatbots')
