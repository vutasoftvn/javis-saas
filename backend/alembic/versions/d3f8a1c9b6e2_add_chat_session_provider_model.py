"""Add provider/model selection to chat sessions (Wave 1 multi-provider chat).

Revision ID: d3f8a1c9b6e2
Revises: 50a0e7e178f1
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3f8a1c9b6e2"
down_revision: Union[str, Sequence[str], None] = "50a0e7e178f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default giữ nguyên hành vi cũ (mọi session trước đây ngầm định DeepSeek) cho
    # cả session đã tồn tại lẫn insert không truyền cột này.
    op.add_column(
        "chat_sessions",
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="deepseek"),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("model", sa.String(length=100), nullable=False, server_default="deepseek-chat"),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "model")
    op.drop_column("chat_sessions", "provider")
