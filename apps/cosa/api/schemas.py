from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

__all__ = [
    "ApprovalDecisionRequest",
    "ApprovalDecisionResponse",
    "CancelRunResponse",
    "ConversationCreate",
    "ConversationListResponse",
    "ConversationResponse",
    "ConversationUpdate",
    "EventEnvelopeDTO",
    "MessageAttachmentCreate",
    "MessageAttachmentResponse",
    "MessageCreate",
    "MessageResponse",
    "RunResponse",
    "RunSummaryResponse",
    "SessionStatus",
    "SessionTimelineResponse",
    "SessionViewResponse",
    "WorkspaceArtifactResponse",
    "InstallConnectorRequest",
    "AuthorizeConnectorRequest",
    "GrantConnectorRequest",
    "RevokeGrantRequest",
    "CreateScheduleRequest",
    "ScheduleResponse",
    "ScheduleListResponse",
]


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    active_agent_profile: Optional[str] = None
    agent_profile_id: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    active_agent_profile: Optional[str] = None
    agent_profile_id: Optional[str] = None
    archived: Optional[bool] = None


class MessageAttachmentCreate(BaseModel):
    file_name: str
    media_type: str
    object_ref: str
    size: int = 0
    checksum: Optional[str] = None


class MessageAttachmentResponse(BaseModel):
    id: str
    message_id: str
    object_ref: str
    media_type: str
    file_name: str
    size: int
    checksum: Optional[str] = None
    knowledge_ingest_status: str = "COMPLETED"


class MessageCreate(BaseModel):
    content: str
    role: str = "user"
    parent_message_id: Optional[str] = None
    attachments: Optional[list[MessageAttachmentCreate]] = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    run_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    status: str = "completed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attachments: list[MessageAttachmentResponse] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    id: str
    workspace_id: str
    created_by_principal: str
    title: str
    active_agent_profile: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    archived_at: Optional[datetime] = None
    messages: list[MessageResponse] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int


class RunResponse(BaseModel):
    run_id: str
    conversation_id: str
    status: str
    message_id: Optional[str] = None


class CancelRunResponse(BaseModel):
    run_id: str
    status: str = "CANCELLED"


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    reason: Optional[str] = None


class ApprovalDecisionResponse(BaseModel):
    approval_id: str
    run_id: Optional[str] = None
    status: str
    reviewer: str
    reason: Optional[str] = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventEnvelopeDTO(BaseModel):
    run_id: str
    conversation_id: Optional[str] = None
    sequence: int
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None


SessionStatus = Literal["idle", "running", "waiting_approval", "completed", "failed"]


class RunSummaryResponse(BaseModel):
    run_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class WorkspaceArtifactResponse(BaseModel):
    artifact_id: str
    workspace_id: str
    conversation_id: str
    run_id: Optional[str] = None
    source_message_id: Optional[str] = None
    artifact_kind: str
    display_name: str
    media_type: str
    object_ref: str
    checksum: Optional[str] = None
    size_bytes: int = 0
    status: str = "available"
    input_artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    archived_at: Optional[datetime] = None


class SessionTimelineResponse(BaseModel):
    events: list[EventEnvelopeDTO] = Field(default_factory=list)
    total: int = 0


class SessionViewResponse(BaseModel):
    id: str  # exact ConversationRecord.conversation_id
    workspace_id: str
    title: str
    agent_profile: Optional[str] = None
    status: SessionStatus
    latest_run: Optional[RunSummaryResponse] = None
    messages: list[MessageResponse] = Field(default_factory=list)
    timeline: list[EventEnvelopeDTO] = Field(default_factory=list)
    artifacts: list[WorkspaceArtifactResponse] = Field(default_factory=list)
    enabled_connector_keys: list[str] = Field(default_factory=list)


# Connectors (Task 3)
class InstallConnectorRequest(BaseModel):
    connector_key: str


class AuthorizeConnectorRequest(BaseModel):
    installation_id: str
    secret_ref: str
    granted_scopes: list[str] = Field(default_factory=list)
    expires_at: datetime


class GrantConnectorRequest(BaseModel):
    conversation_id: str
    authorization_id: str
    allowed_actions: list[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


class RevokeGrantRequest(BaseModel):
    conversation_id: str
    grant_id: str


# Schedules (Task 4)
class CreateScheduleRequest(BaseModel):
    schedule_kind: Literal["one_time", "daily", "weekdays"]
    timezone: str = "Asia/Ho_Chi_Minh"
    run_at: Optional[datetime] = None
    hour: Optional[int] = None
    minute: Optional[int] = None
    weekdays: list[int] = Field(default_factory=list)
    prompt_template: str
    agent_profile: str = "operations"
    connector_grant_ids: list[str] = Field(default_factory=list)


class ScheduleResponse(BaseModel):
    id: str
    workspace_id: str
    created_by: str
    schedule_kind: str
    timezone: str
    prompt_template: str
    agent_profile: str
    state: str
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    created_at: datetime


class ScheduleListResponse(BaseModel):
    items: list[ScheduleResponse] = Field(default_factory=list)
    total: int = 0
