from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class DelegationStatus(str, Enum):
    QUEUED = "queued"
    WAITING_APPROVAL = "waiting_approval"
    DENIED = "denied"
    CLAIMED = "claimed"
    DISPATCHING = "dispatching"
    RUNNING = "running"
    RETRY_SCHEDULED = "retry_scheduled"
    CANCEL_REQUESTED = "cancel_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DelegationRequest(BaseModel):
    workspace_id: int
    outcome_run_id: int
    run_step_id: int
    root_agent_run_id: int
    parent_agent_run_id: int
    profile_id: str
    provider_name: str
    runtime_name: Optional[str] = None
    task: str
    permission_profile: str = "read_only"
    context: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 600


class DelegationHandle(BaseModel):
    provider_name: str
    external_id: str
    native_job_id: Optional[str] = None
    safe_metadata: dict[str, Any] = Field(default_factory=dict)


class DelegationResult(BaseModel):
    status: DelegationStatus
    structured_result: Optional[dict[str, Any]] = None
    output_text: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    next_poll_at: Optional[datetime] = None


class ProviderHealth(BaseModel):
    provider_name: str
    available: bool
    details: dict[str, Any] = Field(default_factory=dict)


class ProviderCapabilities(BaseModel):
    cancel_supported: bool = True
    idempotent_start: bool = True
    asynchronous: bool = True
