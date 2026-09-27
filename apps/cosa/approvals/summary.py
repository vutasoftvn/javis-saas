"""Tóm tắt dễ đọc cho hành động agent đang chờ founder duyệt trong chat
(spec 2026-09-27-chat-business-actions §4.5).

Dựng từ tham số tool đã được scope; KHÔNG đưa ID (objective_id, task_id…) hay enum thô
vào văn bản — enum được dịch sang nhãn theo locale. Mọi capability T2 có mẫu riêng
(test khoá); capability lạ rơi về mẫu chung không lộ tên kỹ thuật.
"""

from __future__ import annotations

from typing import Any

__all__ = ["capability_id_for_tool", "summarize_action"]

# (title, detail) theo ngôn ngữ; {project} và các trường tham số điền qua format_map.
_TEMPLATES: dict[str, dict[str, tuple[str, str]]] = {
    "okr.key_result.create": {
        "vi": ("Tạo Key Result mới cho {project}", "{title} — mục tiêu {target_value} {unit}"),
        "en": ("Create a Key Result for {project}", "{title} — target {target_value} {unit}"),
    },
    "okr.key_result.checkin": {
        "vi": ("Ghi nhận tiến độ Key Result cho {project}", "Giá trị mới: {value}"),
        "en": ("Record Key Result progress for {project}", "New value: {value}"),
    },
    "startup_os.goal.create": {
        "vi": ("Tạo mục tiêu mới cho {project}", "{title} ({goal_type_label})"),
        "en": ("Create a new goal for {project}", "{title} ({goal_type_label})"),
    },
    "startup_os.project.triage": {
        "vi": ("Phân loại dự án {project}", "Quyết định: {action_label}"),
        "en": ("Triage project {project}", "Decision: {action_label}"),
    },
    "operations.task.advance": {
        "vi": ("Chuyển trạng thái công việc trong {project}", "Trạng thái mới: {to_status_label}"),
        "en": ("Update a task status in {project}", "New status: {to_status_label}"),
    },
    "finance.transaction.record": {
        "vi": ("Ghi một giao dịch cho {project}", "{description}: {amount} ({direction_label})"),
        "en": ("Record a transaction for {project}", "{description}: {amount} ({direction_label})"),
    },
    "venture.profile.propose_update": {
        "vi": ("Cập nhật hồ sơ khởi nghiệp của {project}", "Trường thay đổi: {fields}"),
        "en": ("Update the venture profile of {project}", "Changed fields: {fields}"),
    },
    "commercial.marketing_context.write": {
        "vi": ("Cập nhật bối cảnh marketing của {project}", "{change_reason}"),
        "en": ("Update the marketing context of {project}", "{change_reason}"),
    },
    "commercial.experiment.write": {
        "vi": ("Tạo thử nghiệm marketing cho {project}", "{hypothesis}"),
        "en": ("Create a marketing experiment for {project}", "{hypothesis}"),
    },
    "engagement.assignment.write": {
        "vi": ("Giao hội thoại khách hàng cho người phụ trách", "{reason}"),
        "en": ("Assign a customer conversation", "{reason}"),
    },
}

_ENUM_LABELS: dict[str, dict[str, dict[str, str]]] = {
    "goal_type": {
        "vi": {
            "vision": "tầm nhìn",
            "strategic": "chiến lược",
            "tactical": "chiến thuật",
            "sprint": "sprint",
        },
        "en": {
            "vision": "vision",
            "strategic": "strategic",
            "tactical": "tactical",
            "sprint": "sprint",
        },
    },
    "action": {
        "vi": {
            "link": "gắn vào mục tiêu",
            "mark_rd": "đánh dấu R&D",
            "archive": "lưu trữ",
            "roll_to_new_goal": "chuyển sang mục tiêu mới",
        },
        "en": {
            "link": "link to an objective",
            "mark_rd": "mark as R&D",
            "archive": "archive",
            "roll_to_new_goal": "roll into a new goal",
        },
    },
    "to_status": {
        "vi": {"in_progress": "đang làm", "done": "hoàn thành", "blocked": "bị chặn"},
        "en": {"in_progress": "in progress", "done": "done", "blocked": "blocked"},
    },
    "direction": {
        "vi": {"IN": "thu", "OUT": "chi", "inbound": "thu", "outbound": "chi"},
        "en": {"IN": "income", "OUT": "expense", "inbound": "income", "outbound": "expense"},
    },
}

_VENTURE_FIELD_LABELS: dict[str, dict[str, str]] = {
    "problem_statement": {"vi": "vấn đề", "en": "problem"},
    "target_customer": {"vi": "khách hàng mục tiêu", "en": "target customer"},
    "industry": {"vi": "ngành", "en": "industry"},
    "geography": {"vi": "thị trường", "en": "geography"},
    "currency": {"vi": "tiền tệ", "en": "currency"},
    "timezone": {"vi": "múi giờ", "en": "timezone"},
    "founder_goal": {"vi": "mục tiêu founder", "en": "founder goal"},
    "initial_runway_months": {"vi": "runway", "en": "runway"},
}


class _Safe(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "—"


def _lang(locale: str | None) -> str:
    return "en" if (locale or "").lower().startswith("en") else "vi"


def capability_id_for_tool(tool_name: str | None, known_ids: Any) -> str | None:
    """Tên tool của model (`okr_key_result_create`) -> capability id (`okr.key_result.create`)."""
    if not tool_name:
        return None
    for cap_id in known_ids:
        if tool_name in (cap_id, cap_id.replace(".", "_")):
            return str(cap_id)
    return None


def summarize_action(
    capability_id: str | None,
    args: dict[str, Any] | None,
    locale: str | None,
    *,
    project_name: str | None,
) -> dict[str, str]:
    lang = _lang(locale)
    args = args or {}
    templates = _TEMPLATES.get(capability_id or "")
    if templates is None:
        generic = (
            "Perform an action that needs your approval"
            if lang == "en"
            else ("Thực hiện một hành động cần bạn duyệt")
        )
        return {"title": generic, "detail": ""}
    project = project_name or ("this project" if lang == "en" else "dự án này")
    values = _Safe({k: v for k, v in args.items() if v not in (None, "")}, project=project)
    values.setdefault("unit", "")
    for field, labels in _ENUM_LABELS.items():
        if field in args:
            values[f"{field}_label"] = labels[lang].get(str(args[field]), "—")
    if capability_id == "venture.profile.propose_update":
        values["fields"] = (
            ", ".join(
                _VENTURE_FIELD_LABELS[k][lang]
                for k in _VENTURE_FIELD_LABELS
                if args.get(k) not in (None, "")
            )
            or "—"
        )
    title, detail = templates[lang]
    return {
        "title": title.format_map(values),
        "detail": " ".join(detail.format_map(values).split()),
    }
