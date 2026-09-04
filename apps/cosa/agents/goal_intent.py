"""Phát hiện phát biểu "mục tiêu tuần" trong tin nhắn chat của founder (WGA).

2 tầng:
1. `looks_like_weekly_goal` — pre-filter đa tín hiệu, RẺ (không gọi LLM). Chỉ khi
   qua tầng này mới tốn 1 lượt classify LLM.
2. `classify_weekly_goal_llm` — 1 lượt LLM structured trả
   `{is_weekly_goal_statement, normalized_goal, confidence}`. Lỗi/không có model
   -> caller fallback về heuristic (`detect_weekly_goal_suggestion`).

Quyết định thật vẫn thuộc founder — agent chỉ chèn 1 structured `goal_confirm`
message; founder bấm nút mới ghi goal + chạy phân rã.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

__all__ = [
    "GoalIntentResult",
    "GoalIntentSuggestion",
    "classify_weekly_goal_llm",
    "detect_weekly_goal_suggestion",
    "looks_like_weekly_goal",
]

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
    """Heuristic-only — nếu `should_suggest`, caller chèn 1 `goal_confirm` message
    với `normalized_goal` (founder xác nhận / sửa trước khi lưu)."""
    if not looks_like_weekly_goal(user_message):
        return GoalIntentSuggestion(should_suggest=False, normalized_goal="")
    normalized = " ".join(user_message.strip().split())
    return GoalIntentSuggestion(should_suggest=True, normalized_goal=normalized)


@dataclass
class GoalIntentResult:
    is_weekly_goal_statement: bool
    normalized_goal: str
    confidence: float


_CLASSIFY_INSTRUCTIONS = (
    "You classify whether a founder's chat message STATES a weekly goal / weekly "
    "focus for their company (something they want to achieve or commit to this "
    "week or next week). A question, small talk, a status request, or a vague "
    "wish is NOT a weekly goal statement.\n\n"
    "Return ONLY a JSON object, no prose, no markdown fences:\n"
    '{"is_weekly_goal_statement": <bool>, "normalized_goal": "<one concise '
    'imperative sentence, empty string if not a goal>", "confidence": <0.0-1.0>}'
)


async def classify_weekly_goal_llm(model: object, user_message: str) -> GoalIntentResult:
    """1 lượt LLM structured. Raise nếu model không dùng được / output sai —
    caller bắt và fallback heuristic."""
    from agents import Agent, Runner

    agent = Agent(
        name="wga_goal_intent",
        instructions=_CLASSIFY_INSTRUCTIONS,
        tools=[],
        model=model,  # type: ignore[arg-type]
    )
    result = await Runner.run(agent, user_message.strip())
    raw = str(getattr(result, "final_output", "") or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        if raw.rstrip().endswith("```"):
            raw = raw.rstrip()[:-3]
    data = json.loads(raw.strip())
    is_goal = bool(data["is_weekly_goal_statement"])
    normalized = str(data.get("normalized_goal") or "").strip()
    confidence = float(data.get("confidence") or 0.0)
    if is_goal and not normalized:
        normalized = " ".join(user_message.strip().split())
    return GoalIntentResult(
        is_weekly_goal_statement=is_goal,
        normalized_goal=normalized,
        confidence=max(0.0, min(1.0, confidence)),
    )
