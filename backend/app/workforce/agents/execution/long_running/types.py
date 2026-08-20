from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkContext(BaseModel):
    workspace_id: int
    outcome_run_id: int
    run_step_id: int
    root_agent_run_id: int
    parent_agent_run_id: int
    profile_id: str


class WorkRequest(BaseModel):
    task: str
    permission_profile: str
    timeout_seconds: int = 600
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkHandle(BaseModel):
    provider_name: str
    external_id: str
    native_job_id: str | None = None
    safe_metadata: dict[str, Any] = Field(default_factory=dict)


class WorkStatus(BaseModel):
    state: WorkState
    progress: float | None = Field(default=None, ge=0, le=1)
    structured_result: dict[str, Any] | None = None
    output_text: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False
    error_code: str | None = None
    error_message: str | None = None
    next_poll_after_seconds: float | None = Field(default=None, ge=0)


class CancelResult(BaseModel):
    accepted: bool
    state: WorkState
    message: str | None = None


class WorkProviderHealth(BaseModel):
    provider_name: str
    available: bool
    details: dict[str, Any] = Field(default_factory=dict)


class WorkProviderCapabilities(BaseModel):
    cancel_supported: bool = True
    idempotent_start: bool = True
    asynchronous: bool = True
