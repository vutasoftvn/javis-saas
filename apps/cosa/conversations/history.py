"""Lịch sử hội thoại đưa vào prompt (thay ADR-CONV-001 single-turn — xem
ADR-CONV-002).

Thuần, không I/O: nhận danh sách `MessageRecord` đã lưu, trả các lượt gần nhất
dạng `{"role", "content"}` trong ngân sách số lượt + ký tự. Lượt cũ vượt ngân
sách bị bỏ (theo thứ tự thời gian, giữ mới nhất). Message có cấu trúc do agent
chèn (`{"kind": ...}` — goal_confirm, plan_progress) được rút gọn thành 1 dòng
mô tả để model biết chuyện đã xảy ra mà không nhận JSON UI thô.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

__all__ = ["build_history", "history_limits"]

_ROLES = {"user": "user", "assistant": "assistant", "cosa": "assistant"}
_DEFAULT_TURNS = 12
_DEFAULT_CHARS = 12_000
_MAX_MESSAGE_CHARS = 2_000


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(int(raw), 0)
    except ValueError:
        return default


def history_limits() -> tuple[int, int]:
    """(số message tối đa, tổng ký tự tối đa); 0 = tắt lịch sử."""
    return (
        _int_env("COSA_CHAT_HISTORY_MESSAGES", _DEFAULT_TURNS),
        _int_env("COSA_CHAT_HISTORY_MAX_CHARS", _DEFAULT_CHARS),
    )


def _describe_structured(data: dict[str, Any]) -> str:
    kind = str(data.get("kind"))
    if kind == "goal_confirm":
        return f"[Đã đề xuất đặt mục tiêu tuần: {data.get('normalized_goal', '')}]"
    if kind == "plan_progress":
        parts = [
            f"{label}: {', '.join(map(str, data.get(key) or []))}"
            for key, label in (
                ("done", "xong"),
                ("pending_review", "chờ xác nhận"),
                ("waiting_approval", "chờ duyệt"),
                ("blocked", "bị chặn"),
            )
            if data.get(key)
        ]
        return "[Cập nhật tiến độ kế hoạch — " + "; ".join(parts) + "]"
    if kind == "memory_confirm":
        return f"[Đã đề xuất lưu vào trí nhớ dự án: {data.get('fact', '')}]"
    return f"[{kind}]"


def _content_for_model(content: str) -> str:
    text = (content or "").strip()
    if text.startswith("{") and '"kind"' in text:
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if isinstance(data, dict) and data.get("kind"):
            return _describe_structured(data)
    if len(text) > _MAX_MESSAGE_CHARS:
        return text[:_MAX_MESSAGE_CHARS] + " …(đã rút gọn)"
    return text


def build_history(
    messages: Sequence[Any],
    *,
    exclude_run_id: str | None,
    max_messages: int,
    max_chars: int,
) -> list[dict[str, str]]:
    if max_messages <= 0 or max_chars <= 0:
        return []
    picked: list[dict[str, str]] = []
    used = 0
    for m in reversed(list(messages)):
        role = _ROLES.get(str(getattr(m, "role", "")))
        if role is None or getattr(m, "status", "completed") != "completed":
            continue
        if exclude_run_id and getattr(m, "run_id", None) == exclude_run_id and role == "user":
            continue  # lượt hiện tại đi riêng làm input chính
        content = _content_for_model(str(getattr(m, "content", "")))
        if not content:
            continue
        if used + len(content) > max_chars:
            break
        picked.append({"role": role, "content": content})
        used += len(content)
        if len(picked) >= max_messages:
            break
    picked.reverse()
    return picked
