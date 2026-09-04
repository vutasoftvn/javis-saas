"""Kickoff wizard Bước 3 — gợi ý outcome + việc tuần đầu (AI suggestion).

Pure helpers: JSON schema cố định, prompt, và strict parser. Không I/O, không
LLM call ở đây — worker (`kickoff_suggestion_run.py`) chạy kernel và feed raw
text vào `parse_suggestion_output`. Mẫu theo `goal_decomposition.py` (WGA).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

__all__ = [
    "KickoffSuggestion",
    "SuggestionSchemaError",
    "build_suggestion_prompt",
    "parse_suggestion_output",
]

_STAGE_LABEL = {
    "P0_DISCOVERY": "Khám phá (P0) — khảo sát pain point ban đầu",
    "P1_PROBLEM_VALIDATION": "Xác thực vấn đề (P1) — đòi hỏi từ 5 cuộc phỏng vấn hoặc prototype",
}

_EVIDENCE_LABEL = {
    "NONE": "Chưa nói chuyện với khách hàng",
    "ONE_TO_FOUR_INTERVIEWS": "Đã có 1-4 cuộc trao đổi",
    "FIVE_PLUS_INTERVIEWS": "Có từ 5 cuộc trao đổi",
    "PROTOTYPE_OR_REVENUE": "Đã có prototype hoặc khách trả tiền",
}


class SuggestionSchemaError(ValueError):
    """Raised khi output của agent không đúng schema bắt buộc."""


@dataclass
class KickoffSuggestion:
    outcome: str
    actions: list[str]


def build_suggestion_prompt(
    *,
    target_customer: str,
    problem_statement: str,
    evidence_level: str,
    selected_stage: str,
    stage_duration_weeks: int,
) -> str:
    stage_label = _STAGE_LABEL.get(selected_stage, selected_stage)
    evidence_label = _EVIDENCE_LABEL.get(evidence_level, evidence_level)

    return (
        "Bạn đang giúp 1 founder chốt kế hoạch TUẦN ĐẦU của vòng khởi nghiệp.\n\n"
        f"ĐỐI TƯỢNG GẶP VẤN ĐỀ: {target_customer.strip()}\n"
        f"VẤN ĐỀ GÂY ẢNH HƯỞNG: {problem_statement.strip()}\n"
        f"MỨC BẰNG CHỨNG HIỆN TẠI: {evidence_label}\n"
        f"VÒNG ĐÃ CHỌN: {stage_label}, kéo dài {stage_duration_weeks} tuần\n\n"
        "Đề xuất:\n"
        "1. outcome: 1 câu mô tả KẾT QUẢ cụ thể, đo được, founder nên đạt được "
        "sau TUẦN ĐẦU tiên của vòng này (không phải cả vòng).\n"
        "2. actions: 1 đến 3 việc CỤ THỂ founder nên làm trong tuần đầu để đạt "
        "outcome đó. Mỗi việc bắt đầu bằng động từ hành động, đủ cụ thể để làm "
        "ngay (vd 'Phỏng vấn 5 khách hàng mục tiêu về...', không nói chung "
        "chung 'Nghiên cứu thị trường').\n\n"
        "Trả về DUY NHẤT 1 JSON object dạng "
        '{"outcome": "...", "actions": ["...", "..."]}, không kèm giải thích, '
        "không dùng markdown fence."
    )


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def parse_suggestion_output(raw: str) -> KickoffSuggestion:
    """Parse + validate output. Raises SuggestionSchemaError cho mọi lỗi cấu
    trúc (không bao giờ trả kết quả nửa vời)."""
    if not raw or not raw.strip():
        raise SuggestionSchemaError("empty suggestion output")

    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as exc:
        raise SuggestionSchemaError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise SuggestionSchemaError("top-level output must be a JSON object")

    outcome = data.get("outcome")
    if not isinstance(outcome, str) or not outcome.strip():
        raise SuggestionSchemaError("'outcome' must be a non-empty string")
    outcome = outcome.strip()
    if len(outcome) > 200:
        outcome = outcome[:200].rstrip()

    actions = data.get("actions")
    if not isinstance(actions, list) or not (1 <= len(actions) <= 3):
        raise SuggestionSchemaError("'actions' must be an array of 1 to 3 items")

    cleaned_actions: list[str] = []
    for i, a in enumerate(actions):
        if not isinstance(a, str) or not a.strip():
            raise SuggestionSchemaError(f"actions[{i}] must be a non-empty string")
        cleaned_actions.append(a.strip())

    return KickoffSuggestion(outcome=outcome, actions=cleaned_actions)
