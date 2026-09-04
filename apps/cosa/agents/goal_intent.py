"""Phát hiện phát biểu "mục tiêu tuần" trong tin nhắn chat của founder (WGA).

v1: pre-filter đa tín hiệu (KHÔNG phải 1 keyword) quyết định CÓ gợi ý hay không.
Quyết định thật vẫn thuộc founder — agent chỉ chèn 1 structured `goal_confirm`
message; founder bấm nút mới ghi goal + chạy phân rã. Không parse text để suy
trạng thái ứng dụng.

Follow-up: thay `looks_like_weekly_goal` bằng 1 lượt classify LLM trả
`{is_weekly_goal_statement, normalized_goal, confidence}` (spec §7.2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["GoalIntentSuggestion", "detect_weekly_goal_suggestion", "looks_like_weekly_goal"]

# Cụm chỉ ý định đặt mục tiêu / kết quả mong muốn cho một khoảng thời gian.
_GOAL_CUES = (
    r"tuần này",
    r"tuần tới",
    r"tuần sau",
    r"mục tiêu",
    r"trọng tâm",
    r"ưu tiên",
    r"kết quả mong muốn",
    r"cần đạt",
    r"muốn đạt",
    r"đặt mục tiêu",
    r"this week",
    r"next week",
    r"weekly goal",
    r"our goal",
    r"focus for",
)
# Động từ hành động / cam kết -> tăng độ chắc đây là một tuyên bố mục tiêu.
_COMMIT_CUES = (
    r"muốn",
    r"cần",
    r"hãy",
    r"sẽ",
    r"quyết tâm",
    r"chốt",
    r"hoàn thành",
    r"triển khai",
    r"launch",
    r"ship",
    r"finish",
    r"close",
    r"want to",
    r"need to",
    r"aim to",
)
# Câu hỏi / xã giao -> KHÔNG phải tuyên bố mục tiêu.
_NEGATIVE_CUES = (
    r"^\s*(ai|bạn|cái gì|tại sao|làm sao|như thế nào|khi nào|ở đâu)\b",
    r"\?\s*$",
    r"cảm ơn",
    r"^\s*(hi|hello|chào|xin chào)\b",
)

_MIN_WORDS = 4
_MAX_CHARS = 400


@dataclass
class GoalIntentSuggestion:
    should_suggest: bool
    normalized_goal: str


def _score(text: str) -> int:
    low = text.lower()
    score = 0
    if any(re.search(p, low) for p in _GOAL_CUES):
        score += 2
    if any(re.search(p, low) for p in _COMMIT_CUES):
        score += 1
    return score


def looks_like_weekly_goal(user_message: str) -> bool:
    if not user_message:
        return False
    text = user_message.strip()
    if len(text) > _MAX_CHARS or len(text.split()) < _MIN_WORDS:
        return False
    low = text.lower()
    if any(re.search(p, low) for p in _NEGATIVE_CUES):
        return False
    return _score(text) >= 3


def detect_weekly_goal_suggestion(user_message: str) -> GoalIntentSuggestion:
    """Trả về gợi ý — nếu `should_suggest`, caller chèn 1 `goal_confirm` message
    với `normalized_goal` (founder xác nhận / sửa trước khi lưu)."""
    if not looks_like_weekly_goal(user_message):
        return GoalIntentSuggestion(should_suggest=False, normalized_goal="")
    normalized = " ".join(user_message.strip().split())
    return GoalIntentSuggestion(should_suggest=True, normalized_goal=normalized)
