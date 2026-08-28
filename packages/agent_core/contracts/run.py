from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from agent_core.contracts.wait import WaitDescriptor
from agent_core.governance.contracts import ExecutionMode, PinnedSpecIdentity

__all__ = ["RunRequest", "RunResult", "RunStatus"]


class RunStatus(enum.StrEnum):
    """Trạng thái vòng đời của một Run theo Master Guide §11.2."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunRequest(BaseModel):
    """Hợp đồng khởi chạy Run theo Master Guide §6.5.

    Định nghĩa tường minh ngữ cảnh, quyền hạn và root executable mà không
    dùng untyped dictionary làm bus điều khiển chính.

    workspace_id là khóa tenant duy nhất sau Task 7 (2026-08-27).
    """

    run_id: str | None = None
    principal: str
    workspace_id: str | None = None
    conversation_id: str | None = None
    session_ref: str | None = None
    root_executable_ref: PinnedSpecIdentity | str
    input: dict[str, Any] = Field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS
    model_policy: dict[str, Any] = Field(default_factory=dict)
    locale: str = "vi-VN"
    correlation_id: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    """Kết quả hoàn thành hoặc tạm dừng của Run theo Master Guide §6.6.

    Không đưa private chain-of-thought vào result schema công khai.
    """

    run_id: str
    status: RunStatus
    final_output: Any = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    events_cursor_ref: str | None = None
    interruptions_waits: list[WaitDescriptor] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
