"""Add direct workspace and chat metadata to AI runs.

Revision ID: c4a1b9e8d2f0
Revises: 14001d654660
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4a1b9e8d2f0"
down_revision: Union[str, Sequence[str], None] = "14001d654660"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_runs", sa.Column("workspace_id", sa.Uuid(), nullable=True))
    op.add_column("ai_runs", sa.Column("chat_session_id", sa.Uuid(), nullable=True))
    op.add_column("ai_runs", sa.Column("chat_message_id", sa.Uuid(), nullable=True))
    op.add_column("ai_runs", sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"))
    op.add_column("ai_runs", sa.Column("input_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_runs", sa.Column("output_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_runs", sa.Column("error_code", sa.String(length=100), nullable=True))
    op.add_column("ai_runs", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("ai_runs", sa.Column("finished_at", sa.DateTime(), nullable=True))
    op.create_foreign_key("fk_ai_runs_workspace_id", "ai_runs", "workspaces", ["workspace_id"], ["id"])
    op.create_foreign_key("fk_ai_runs_chat_session_id", "ai_runs", "chat_sessions", ["chat_session_id"], ["id"])
    op.create_foreign_key("fk_ai_runs_chat_message_id", "ai_runs", "chat_messages", ["chat_message_id"], ["id"])
    op.create_index("ix_ai_runs_workspace_id", "ai_runs", ["workspace_id"])
    op.create_index("ix_ai_runs_chat_session_id", "ai_runs", ["chat_session_id"])
    op.create_index("ix_ai_runs_chat_message_id", "ai_runs", ["chat_message_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_runs_chat_message_id", table_name="ai_runs")
    op.drop_index("ix_ai_runs_chat_session_id", table_name="ai_runs")
    op.drop_index("ix_ai_runs_workspace_id", table_name="ai_runs")
    op.drop_constraint("fk_ai_runs_chat_message_id", "ai_runs", type_="foreignkey")
    op.drop_constraint("fk_ai_runs_chat_session_id", "ai_runs", type_="foreignkey")
    op.drop_constraint("fk_ai_runs_workspace_id", "ai_runs", type_="foreignkey")
    op.drop_column("ai_runs", "finished_at")
    op.drop_column("ai_runs", "started_at")
    op.drop_column("ai_runs", "error_code")
    op.drop_column("ai_runs", "output_tokens")
    op.drop_column("ai_runs", "input_tokens")
    op.drop_column("ai_runs", "status")
    op.drop_column("ai_runs", "chat_message_id")
    op.drop_column("ai_runs", "chat_session_id")
    op.drop_column("ai_runs", "workspace_id")
