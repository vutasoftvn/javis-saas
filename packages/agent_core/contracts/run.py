from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Optional, Union
from pydantic import BaseModel, Field

from agent_core.governance.contracts import ExecutionMode, PinnedSpecIdentity
from agent_core.contracts.wait import WaitDescriptor

__all__ = ["RunStatus", "RunRequest", "RunResult"]


class RunStatus(str, enum.Enum):
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
    """

    run_id: Optional[str] = None
    principal: str
    tenant_id: Optional[str] = None

    company_id: Optional[str] = None
    workspace_id: Optional[str] = None
    conversation_id: Optional[str] = None
    session_ref: Optional[str] = None
    root_executable_ref: Union[PinnedSpecIdentity, str]
    input: dict[str, Any] = Field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS
    model_policy: dict[str, Any] = Field(default_factory=dict)
    locale: str = "vi-VN"
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None
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
    events_cursor_ref: Optional[str] = None
    interruptions_waits: list[WaitDescriptor] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
