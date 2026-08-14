"""chat_sessions.purpose: tách lượt prompt một-lần khỏi hội thoại người dùng

Revision ID: v13_029_chat_session_purpose
Revises: v13_028_automation_catalog_seed

brain-api không giữ khoá provider (chỉ nhận cờ ``PROVIDER_CONFIGURED_*``), nên các nút
"AI đề xuất ..." của Strategy phải nhờ agent-worker gọi model hộ qua một chat session ẩn.
Session ẩn đó KHÔNG phải hội thoại: nó cần đúng một khối JSON trả về, không cần RAG,
không cần tool, không cần system prompt chống bịa - bộ prompt hội thoại dặn model "chưa
gọi tool là chưa biết gì về workspace" sẽ đẩy nó đi gọi tool thay vì trả JSON như yêu cầu.

Cột này là chỗ đánh dấu khác biệt đó. Nullable để mọi session đã có từ trước vẫn là hội
thoại bình thường.
"""

from alembic import op
import sqlalchemy as sa


revision = "v13_029_chat_session_purpose"
down_revision = "v13_028_automation_catalog_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("purpose", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "purpose")
