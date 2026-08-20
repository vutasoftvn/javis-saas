"""
COSA Operational Trajectory Models
Định dạng nhật ký vận hành dễ hiểu cho con người (Human-readable Operational Narrative) (Structure.md Mục 24).
Tuyệt đối KHÔNG chứa private chain-of-thought (CLAUDE.md Mục 12).
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrajectoryStepType(str, Enum):
    """Phân loại hiển thị cho từng bước trên Live Trajectory Timeline"""
    REQUEST_RECEIVED = "request_received"
    INTENT_CLASSIFIED = "intent_classified"
    CONTEXT_LOADED = "context_loaded"
    SKILL_APPLIED = "skill_applied"
    TOOL_EXECUTED = "tool_executed"
    APPROVAL_PENDING = "approval_pending"
    APPROVAL_RESOLVED = "approval_resolved"
    ARTIFACT_CREATED = "artifact_created"
    ASSISTANT_RESPONSE = "assistant_response"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"


class TrajectoryStep(BaseModel):
    """Một bước trực quan trong dòng thời gian Trajectory"""
    step_id: str
    timestamp: str
    step_type: TrajectoryStepType
    title: str
    description: Optional[str] = None
    badge: Optional[str] = None           # e.g., "LOW_RISK", "HIGH_RISK", "APPROVED"
    actor_id: str = "agent"
    tool_id: Optional[str] = None
    duration_ms: Optional[int] = None
    presenter_payload: Optional[Dict[str, Any]] = None  # Dữ liệu hiển thị format sẵn cho Hologram Hub
    error: Optional[str] = None


class TrajectoryTimeline(BaseModel):
    """Toàn bộ dòng thời gian vận hành của một phiên làm việc"""
    session_id: str
    profile_id: str
    status: str
    created_at: str
    steps: List[TrajectoryStep] = Field(default_factory=list)
    summary_metrics: Dict[str, Any] = Field(default_factory=dict)  # total_tools, total_duration_ms, artifacts_count
