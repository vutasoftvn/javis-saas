from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class AutomationHealth(BaseModel):
    status: str = "healthy"  # healthy, degraded, unavailable
    provider: str
    details: dict[str, Any] = Field(default_factory=dict)
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AutomationRequest(BaseModel):
    automation_key: str
    execution_id: str
    workspace_id: int
    company_id: Optional[int] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    callback_url: Optional[str] = None
    requested_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AutomationStartResult(BaseModel):
    execution_id: str
    provider_execution_id: str
    status: str = "running"  # running, completed, queued, failed
    error: Optional[str] = None


class AutomationRunStatus(BaseModel):
    status: str = "running"  # running, succeeded, failed, cancelled
    progress: Optional[float] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class AutomationCallbackPayload(BaseModel):
    execution_id: str
    provider_execution_id: str
    status: str  # succeeded, failed, cancelled
    result: dict[str, Any] = Field(default_factory=dict)
    finished_at: str
    signature: str
    timestamp: str
