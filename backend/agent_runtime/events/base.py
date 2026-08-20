"""
COSA Agent Events & EventStore Core Contracts
Hạ tầng sự kiện Append-Only Event Sourcing (Structure.md Mục 19, 20, 21, 22, 23).
"""
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Danh mục sự kiện chuẩn hóa của COSA Agent Harness"""
    SESSION_STARTED = "session.started"
    USER_MESSAGE = "user.message"
    INTENT_DETECTED = "intent.detected"
    CONTEXT_LOADED = "context.loaded"
    SKILL_LOADED = "skill.loaded"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_STEP_COMPLETED = "workflow.step_completed"
    TOOL_REQUESTED = "tool.requested"
    TOOL_COMPLETED = "tool.completed"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_REJECTED = "approval.rejected"
    SUBAGENT_STARTED = "subagent.started"
    SUBAGENT_COMPLETED = "subagent.completed"
    ARTIFACT_CREATED = "artifact.created"
    ASSISTANT_MESSAGE = "assistant.message"
    SESSION_COMPLETED = "session.completed"
    SESSION_FAILED = "session.failed"


class AgentEvent(BaseModel):
    """Cấu trúc dữ liệu sự kiện chuẩn (Structure.md Mục 20)"""
    id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}", description="Mã sự kiện: evt_xxxxxxxxxxxx")
    session_id: str = Field(..., description="Mã phiên làm việc: ses_xxxxxxxxxxxx")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    type: EventType
    actor: Dict[str, str] = Field(..., description='{"type": "agent", "id": "marketing"} hoặc {"type": "user", "id": "founder"}')
    payload: Dict[str, Any] = Field(default_factory=dict, description="Dữ liệu chi tiết của sự kiện")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata: runtime, model, duration_ms")


class EventStoreInterface(ABC):
    """Giao diện trừu tượng cho tầng lưu trữ Append-Only Event Store (SQLite / DB)"""

    @abstractmethod
    async def append(self, event: AgentEvent) -> bool:
        """Ghi nhận sự kiện mới vào nhật ký Append-Only"""
        pass

    @abstractmethod
    async def get_events_by_session(self, session_id: str, limit: int = 1000) -> List[AgentEvent]:
        """Truy xuất toàn bộ dòng sự kiện của một phiên làm việc"""
        pass

    @abstractmethod
    async def get_events_since(self, session_id: str, since_event_id: str) -> List[AgentEvent]:
        """Truy xuất các sự kiện phát sinh sau một event_id (phục vụ Realtime Stream / Reconnect)"""
        pass
