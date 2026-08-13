"""Báo cáo CHỈ ĐỌC: một workspace thực sự đang cấp cho AI những tool nào.

Sinh ra để trả lời câu hỏi "vì sao AI trả lời chung chung": tool bị feature flag lọc bỏ
không để lại lỗi nào, nó chỉ đơn giản là không có mặt trong request gửi model. Script này
in ra đúng danh sách model nhận được, kèm lý do cho từng tool vắng mặt.

    cd backend && python -m scripts.ai_tools_report <workspace_id>

Không ghi gì vào DB. Cần biến môi trường DATABASE_URL như brain-api.
"""

import sys

from app.core.feature_flags import TOOL_FLAG_DEFAULTS, is_enabled
from app.core.tool_bootstrap import load_all_tools
from app.core.tool_registry import get_registered_tools
from app.db.session import SessionLocal
from app.modules.chat.company_tools import tool_specs
from app.modules.chat.model_registry import DEFAULT_MODEL, DEFAULT_PROVIDER, get_model


def _print_flags(db, workspace_id: int) -> set[str]:
    print("\n=== FEATURE FLAG KHOÁ TOOL ===")
    enabled = set()
    for key in sorted(TOOL_FLAG_DEFAULTS):
        on = is_enabled(db, key, workspace_id)
        if on:
            enabled.add(key)
        expected = TOOL_FLAG_DEFAULTS[key]
        note = "" if on == expected else f"   <-- lệch mặc định ({expected})"
        print(f"  [{'x' if on else ' '}] {key}{note}")
    return enabled


def _print_tools(db, workspace_id: int, enabled_flags: set[str]) -> None:
    specs = get_registered_tools()

    print(f"\n=== TOOL REGISTRY ({len(specs)} tool) ===")
    voice_on, chat_on, blocked = [], [], []
    for name in sorted(specs):
        spec = specs[name]
        if spec.flag_key and spec.flag_key not in enabled_flags:
            blocked.append((name, spec.flag_key))
            continue
        voice_on.append(name)
        if spec.chat_schema:
            chat_on.append(spec.flat_name)

    print(f"\n-- Voice nhận được ({len(voice_on)}):")
    for name in voice_on:
        print(f"   {name}")

    print(f"\n-- Chat text nhận được ({len(chat_on)}):")
    for name in chat_on:
        print(f"   {name}")

    print(f"\n-- BỊ LỌC BỎ ({len(blocked)}):")
    for name, flag in blocked:
        print(f"   {name}   <- flag '{flag}' đang tắt")
    if not blocked:
        print("   (không có)")

    voice_only = sorted(
        specs[n].qualified_name for n in voice_on if not specs[n].chat_schema
    )
    print(f"\n-- Chỉ voice, cố tình không cho chat ({len(voice_only)}):")
    for name in voice_only:
        print(f"   {name}")


def _print_chat_payload(db, workspace_id: int) -> None:
    """Danh sách THẬT sẽ đi kèm request chat, gồm cả bước lọc theo model."""
    print("\n=== BỘ TOOL THẬT GỬI CHO MODEL CHAT ===")
    entry = get_model(DEFAULT_PROVIDER, DEFAULT_MODEL)
    print(f"  Model mặc định: {DEFAULT_PROVIDER}/{DEFAULT_MODEL}")
    if entry is None:
        print("  !! Không có trong model registry - mọi lượt chat sẽ lỗi cấu hình.")
        return
    if not entry.supports_tools:
        print(
            "  !! Model này KHÔNG gọi được tool, nên chat sẽ chạy hoàn toàn không có tool\n"
            "     và chỉ trả lời bằng kiến thức chung. Đổi CHAT_DEFAULT_PROVIDER/MODEL sang\n"
            "     một model có supports_tools=True."
        )
        return

    with_user = tool_specs(db, workspace_id, user_id=1)
    without_user = tool_specs(db, workspace_id, user_id=None)
    print(f"  Session có user_id : {len(with_user)} tool")
    print(f"  Session cũ (không user_id): {len(without_user)} tool")
    dropped = {s["function"]["name"] for s in with_user} - {
        s["function"]["name"] for s in without_user
    }
    if dropped:
        print(f"  Mất khi thiếu user_id: {sorted(dropped)}")


def _print_data_sanity(db, workspace_id: int) -> None:
    """Có tool mà workspace rỗng thì AI vẫn không nói được gì cụ thể - tách bạch hai
    nguyên nhân đó ra ngay tại đây."""
    from app.db.models import OkrObjective, Project
    from app.modules.tasks.models import Task

    print("\n=== DỮ LIỆU THẬT TRONG WORKSPACE ===")
    for label, model in (("Project", Project), ("OKR objective", OkrObjective), ("Task", Task)):
        count = db.query(model).filter(model.workspace_id == workspace_id).count()
        flag = "" if count else "   <-- rỗng: AI sẽ trả lời 'chưa có dữ liệu', đúng như thiết kế"
        print(f"  {label:16} {count}{flag}")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    try:
        workspace_id = int(sys.argv[1])
    except ValueError:
        print(f"workspace_id phải là số, nhận được {sys.argv[1]!r}")
        return 2

    load_all_tools()
    db = SessionLocal()
    try:
        print(f"Workspace: {workspace_id}")
        enabled_flags = _print_flags(db, workspace_id)
        _print_tools(db, workspace_id, enabled_flags)
        _print_chat_payload(db, workspace_id)
        _print_data_sanity(db, workspace_id)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
