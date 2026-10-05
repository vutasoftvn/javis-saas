"""Render ngữ cảnh công việc (goal ancestry, done criteria) thành dòng prompt an toàn.

Dữ liệu goal/objective do người dùng viết nên chỉ là NGỮ CẢNH, không phải chỉ thị: mọi giá trị
được nội suy đều gộp khoảng trắng (chống chèn dòng mới/tiêu đề section giả), cắt độ dài, chịu
được sai kiểu, và giới hạn số dòng.
"""

from __future__ import annotations

from agent.contracts.done_criteria import DoneCriteriaError, parse_done_criteria

__all__ = ["done_criteria_lines", "goal_context_lines"]

_MAX_LINE = 300
_MAX_LINES = 12


def _clean(value: object) -> str:
    return " ".join(str(value).split())[:_MAX_LINE]


def _num(value: object) -> str:
    return "?" if value is None else _clean(value)


def _titled(value: object) -> str | None:
    """Tiêu đề đã làm sạch của một dict {"title": ...}; None nếu không dùng được."""
    if isinstance(value, dict) and value.get("title"):
        title = _clean(value["title"])
        return title or None
    return None


def goal_context_lines(ancestry: object) -> list[str]:
    if not isinstance(ancestry, dict):
        return []
    lines: list[str] = []
    raw_chain = ancestry.get("goalChain")
    chain: list[str] = []
    for g in raw_chain if isinstance(raw_chain, list) else []:
        title = _titled(g)
        if title is None:
            continue
        goal_type = _clean(g.get("goalType") or "")
        chain.append(f"{title} ({goal_type})" if goal_type else title)
    if chain:
        lines.append("Goal chain (nearest first): " + " < ".join(chain))
    if (company := _titled(ancestry.get("companyObjective"))) is not None:
        lines.append(f"Company objective: {company}")
    if (objective := _titled(ancestry.get("objective"))) is not None:
        lines.append(f"Objective: {objective}")
    kr = ancestry.get("keyResult")
    if (kr_title := _titled(kr)) is not None and isinstance(kr, dict):
        unit = _clean(kr.get("unit") or "")
        lines.append(
            f"Key result: {kr_title} "
            f"(baseline {_num(kr.get('baselineValue'))}, current {_num(kr.get('currentValue'))}, "
            f"target {_num(kr.get('targetValue'))}{' ' + unit if unit else ''})"
        )
    if (project := _titled(ancestry.get("project"))) is not None:
        lines.append(f"Project: {project}")
    reason = ancestry.get("unlinkedReason")
    if reason:
        lines.append(f"Goal link incomplete: {_clean(reason)}")
    return lines[:_MAX_LINES]


def done_criteria_lines(criteria: object) -> list[str]:
    try:
        parsed = parse_done_criteria(criteria)
    except DoneCriteriaError:
        return []
    lines: list[str] = []
    for c in parsed["criteria"]:
        tag = "required" if c["required"] else "optional"
        if c["check"] == "deterministic":
            detail = f"check: {_clean(c['predicate']['kind'])}"
        else:
            detail = f"rubric: {_clean(c['rubric'])}"
        lines.append(f"- [{tag}] {_clean(c['description'])} ({detail})")
    return lines[:_MAX_LINES]
