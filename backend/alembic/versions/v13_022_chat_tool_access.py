"""cho chat truy cập dữ liệu thật: chat_sessions.user_id + seed flag tool còn thiếu

Revision ID: v13_022_chat_tool_access
Revises: v13_021_stage_orchestration

Hai thay đổi cùng phục vụ một việc: để AI trả lời bằng dữ liệu thật thay vì tự nghĩ.

1. ``chat_sessions.user_id`` - các tool tính theo người dùng (next best actions) và việc
   ghi nhận chủ của một đề xuất do chat tạo đều cần biết ai đang nói chuyện. Nullable để
   mọi session đã có từ trước vẫn chạy bình thường.

2. ``next_best_action_v12`` và ``weekly_missions_v12`` chưa từng được seed trong bất kỳ
   migration nào, mà ``is_enabled()`` trả False khi không tìm thấy row. Hệ quả:
   ``company.next_best_actions`` bị lọc khỏi bộ tool của voice agent trong im lặng, trong
   khi system prompt lại dặn model "LUÔN gọi get_next_best_actions" - bảo model gọi một
   tool nó không hề có thì nó chỉ còn cách bịa ra việc cần làm.
"""

from alembic import op
import sqlalchemy as sa

from app.core.snowflake import generate_snowflake_id


revision = "v13_022_chat_tool_access"
down_revision = "v13_021_stage_orchestration"
branch_labels = None
depends_on = None

# Bật mặc định ở mức global; override theo workspace (nếu có) không bị đụng tới.
_ENABLED_DEFAULTS = ("next_best_action_v12", "weekly_missions_v12")

_FLAG_DESCRIPTION = "mCOSA V13 tool-access default"


def _insert_absent(bind, key: str, enabled: bool) -> None:
    """Chỉ thêm khi chưa có row nào. Cùng cách làm với v13_001_flags: cấu hình là thứ
    người vận hành đã có thể đã chỉnh tay, migration không được ghi đè."""
    exists = bind.execute(
        sa.text("SELECT 1 FROM feature_flags WHERE workspace_id IS NULL AND key = :key"),
        {"key": key},
    ).first()
    if exists is None:
        bind.execute(
            sa.text(
                "INSERT INTO feature_flags "
                "(id, workspace_id, key, enabled, description, created_at, updated_at) "
                "VALUES (:id, NULL, :key, :enabled, :description, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": generate_snowflake_id(),
                "key": key,
                "enabled": enabled,
                "description": _FLAG_DESCRIPTION,
            },
        )


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("user_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_foreign_key(
        "fk_chat_sessions_user_id", "chat_sessions", "users", ["user_id"], ["id"]
    )

    bind = op.get_bind()
    for key in _ENABLED_DEFAULTS:
        _insert_absent(bind, key, True)


def downgrade() -> None:
    """Không xoá flag: cấu hình cố tình không bị huỷ ngược, giống v13_001_flags."""
    op.drop_constraint("fk_chat_sessions_user_id", "chat_sessions", type_="foreignkey")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_column("chat_sessions", "user_id")
