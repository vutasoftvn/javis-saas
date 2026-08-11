"""email approvals - thư AI soạn phải được người duyệt mới gửi

Revision ID: f2a7c1d4e8b3
Revises: e1f2g3h4i5j6
Create Date: 2026-08-10 13:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f2a7c1d4e8b3'
down_revision = 'e1f2g3h4i5j6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'email_approvals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('chat_session_id', sa.UUID(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('draft_id', sa.String(length=255), nullable=True),
        sa.Column('to_email', sa.String(length=500), nullable=False),
        sa.Column('subject', sa.String(length=998), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('decided_by', sa.UUID(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.ForeignKeyConstraint(['chat_session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['decided_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_email_approvals_workspace_id'), 'email_approvals', ['workspace_id'], unique=False
    )
    op.create_index(
        op.f('ix_email_approvals_chat_session_id'), 'email_approvals', ['chat_session_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_email_approvals_chat_session_id'), table_name='email_approvals')
    op.drop_index(op.f('ix_email_approvals_workspace_id'), table_name='email_approvals')
    op.drop_table('email_approvals')
