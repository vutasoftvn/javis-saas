from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from agent_core.runs.models import RunEventRecord

__all__ = ["AGUIEvent", "map_run_event_to_ag_ui"]

# Best-effort mapping sang vocabulary AG-UI (Blueprint V2 §10.3) — chưa đối
# chiếu certification chính thức với AG-UI spec (không có kết nối tới tài liệu
# spec gốc trong môi trường phát triển này). Sự kiện COSA nào không có tương
# đương rõ ràng trong AG-UI (approval.required/resolved — AG-UI không có khái
# niệm approval sẵn) map về "CUSTOM", giữ nguyên `cosa_event_type` trong data
# để client Flutter/Web vẫn phân biệt được nếu cần xử lý riêng.
_EVENT_TYPE_MAP: dict[str, str] = {
    "run.started": "RUN_STARTED",
    "run.resumed": "RUN_STARTED",
    "run.completed": "RUN_FINISHED",
    "run.failed": "RUN_ERROR",
    "run.waiting": "CUSTOM",
    "message.delta": "TEXT_MESSAGE_CONTENT",
    "reasoning.status": "CUSTOM",
    "tool.requested": "TOOL_CALL_START",
    "tool.started": "TOOL_CALL_START",
    "tool.completed": "TOOL_CALL_END",
    "tool.failed": "TOOL_CALL_END",
    "policy.evaluated": "CUSTOM",
    "checkpoint.created": "STATE_SNAPSHOT",
    "approval.required": "CUSTOM",
    "approval.resolved": "CUSTOM",
    "approval.decided": "CUSTOM",
}


class AGUIEvent(BaseModel):
    """Sự kiện đã normalize sang vocabulary AG-UI. Flutter/Web/Desktop tiêu
    thụ CÙNG 1 mapping này (Blueprint V2 §10.3) — không nhận raw event nội bộ
    của từng runtime (LangChain/ADK/OpenAI Agents SDK khác nhau)."""

    type: str
    run_id: str
    cosa_event_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    sequence_no: int | None = None


def map_run_event_to_ag_ui(event: RunEventRecord) -> AGUIEvent:
    ag_ui_type = _EVENT_TYPE_MAP.get(event.event_type, "CUSTOM")
    return AGUIEvent(
        type=ag_ui_type,
        run_id=event.run_id,
        cosa_event_type=event.event_type,
        data=event.payload,
        sequence_no=event.sequence_no,
    )
