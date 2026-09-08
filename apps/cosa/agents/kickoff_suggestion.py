"""Kickoff wizard Bước 3 — gợi ý outcome + việc tuần đầu (AI suggestion).

Pure helpers: JSON schema cố định, prompt, và strict parser. Không I/O, không
LLM call ở đây — worker (`kickoff_suggestion_run.py`) chạy kernel và feed raw
text vào `parse_suggestion_output`. Mẫu theo `goal_decomposition.py` (WGA).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

__all__ = [
    "KickoffSuggestion",
    "SuggestionSchemaError",
    "build_suggestion_prompt",
    "parse_suggestion_output",
]

_STAGE_LABEL_VI = {
    "P0_DISCOVERY": "Khám phá (P0) — khảo sát pain point ban đầu",
    "P1_PROBLEM_VALIDATION": "Xác thực vấn đề (P1) — đòi hỏi từ 5 cuộc phỏng vấn hoặc prototype",
}

_STAGE_LABEL_EN = {
    "P0_DISCOVERY": "Discovery (P0) — initial pain point exploration",
    "P1_PROBLEM_VALIDATION": "Problem Validation (P1) — requires 5+ interviews or prototype",
}

_EVIDENCE_LABEL_VI = {
    "NONE": "Chưa nói chuyện với khách hàng",
    "ONE_TO_FOUR_INTERVIEWS": "Đã có 1-4 cuộc trao đổi",
    "FIVE_PLUS_INTERVIEWS": "Có từ 5 cuộc trao đổi",
    "PROTOTYPE_OR_REVENUE": "Đã có prototype hoặc khách trả tiền",
}

_EVIDENCE_LABEL_EN = {
    "NONE": "Haven't spoken with potential customers yet",
    "ONE_TO_FOUR_INTERVIEWS": "Had 1-4 conversations",
    "FIVE_PLUS_INTERVIEWS": "Had 5+ conversations",
    "PROTOTYPE_OR_REVENUE": "Have a prototype or paying customers",
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
    locale: str = "vi-VN",
) -> str:
    is_en = (locale or "").strip().lower().startswith("en")

    if is_en:
        stage_label = _STAGE_LABEL_EN.get(selected_stage, selected_stage)
        evidence_label = _EVIDENCE_LABEL_EN.get(evidence_level, evidence_level)
        return (
            "You are an AI co-founder helping a founder finalize their FIRST WEEK plan for an early-stage cycle.\n\n"
            f"TARGET CUSTOMER: {target_customer.strip()}\n"
            f"PROBLEM STATEMENT: {problem_statement.strip()}\n"
            f"CURRENT EVIDENCE LEVEL: {evidence_label}\n"
            f"SELECTED CYCLE: {stage_label}, lasting {stage_duration_weeks} weeks\n\n"
            "Recommendations needed:\n"
            "1. outcome: exactly 1 sentence describing the concrete, measurable RESULT the founder should achieve "
            "after the FIRST WEEK of this cycle (not the entire cycle).\n"
            "2. actions: 1 to 3 CONCRETE actions the founder should execute during week 1 to achieve that outcome. "
            "Each action must start with an action verb and be specific enough to execute immediately "
            "(e.g., 'Interview 5 target customers about...', not vague like 'Market research').\n\n"
            "LANGUAGE REQUIREMENT: Respond entirely in English. All text in 'outcome' and 'actions' MUST be in English.\n\n"
            "Return ONLY 1 JSON object strictly following the format "
            '{"outcome": "...", "actions": ["...", "..."]}, without explanations, '
            "without markdown fences."
        )

    stage_label = _STAGE_LABEL_VI.get(selected_stage, selected_stage)
    evidence_label = _EVIDENCE_LABEL_VI.get(evidence_level, evidence_level)

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
        "YÊU CẦU NGÔN NGỮ: Toàn bộ nội dung 'outcome' và 'actions' PHẢI viết bằng tiếng Việt.\n\n"
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

    cleaned = _strip_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                raise SuggestionSchemaError(f"invalid JSON: {exc}") from exc
        else:
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
