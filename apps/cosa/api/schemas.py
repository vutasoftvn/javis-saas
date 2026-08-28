from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

__all__ = [
    "ApprovalDecisionRequest",
    "ApprovalDecisionResponse",
    "AuthorizeConnectorRequest",
    "CancelRunResponse",
    "CompleteKnowledgeUploadResponse",
    "ConversationCreate",
    "ConversationListResponse",
    "ConversationResponse",
    "ConversationUpdate",
    "CreateKnowledgeUploadRequest",
    "CreateScheduleRequest",
    "EventEnvelopeDTO",
    "GrantConnectorRequest",
    "InstallConnectorRequest",
    "KnowledgeUploadResponse",
    "MessageAttachmentCreate",
    "MessageAttachmentResponse",
    "MessageCreate",
    "MessageResponse",
    "ReviewKnowledgeIngestionRequest",
    "ReviewKnowledgeIngestionResponse",
    "RevokeGrantRequest",
    "RunResponse",
    "RunSummaryResponse",
    "ScheduleListResponse",
    "ScheduleResponse",
    "SessionStatus",
    "SessionTimelineResponse",
    "SessionViewResponse",
    "WorkspaceArtifactResponse",
]


class ConversationCreate(BaseModel):
    title: str | None = "New Conversation"
    active_agent_profile: str | None = None
    agent_profile_id: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    active_agent_profile: str | None = None
    agent_profile_id: str | None = None
    archived: bool | None = None


class MessageAttachmentCreate(BaseModel):
    file_name: str
    media_type: str
    object_ref: str
    size: int = 0
    checksum: str | None = None


class MessageAttachmentResponse(BaseModel):
    id: str
    message_id: str
    object_ref: str
    media_type: str
    file_name: str
    size: int
    checksum: str | None = None
    knowledge_ingest_status: str = "COMPLETED"


class MessageCreate(BaseModel):
    content: str
    role: str = "user"
    parent_message_id: str | None = None
    attachments: list[MessageAttachmentCreate] | None = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    run_id: str | None = None
    parent_message_id: str | None = None
    status: str = "completed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    attachments: list[MessageAttachmentResponse] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    id: str
    workspace_id: str
    created_by_principal: str
    title: str
    active_agent_profile: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    archived_at: datetime | None = None
    messages: list[MessageResponse] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int


class RunResponse(BaseModel):
    run_id: str
    conversation_id: str
    status: str
    message_id: str | None = None


class CancelRunResponse(BaseModel):
    run_id: str
    status: str = "CANCELLED"


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    reason: str | None = None


class ApprovalDecisionResponse(BaseModel):
    approval_id: str
    run_id: str | None = None
    status: str
    reviewer: str
    reason: str | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EventEnvelopeDTO(BaseModel):
    run_id: str
    conversation_id: str | None = None
    sequence: int
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


SessionStatus = Literal["idle", "running", "waiting_approval", "completed", "failed"]


class RunSummaryResponse(BaseModel):
    run_id: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None


class WorkspaceArtifactResponse(BaseModel):
    artifact_id: str
    workspace_id: str
    conversation_id: str
    run_id: str | None = None
    source_message_id: str | None = None
    artifact_kind: str
    display_name: str
    media_type: str
    object_ref: str
    checksum: str | None = None
    size_bytes: int = 0
    status: str = "available"
    input_artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    archived_at: datetime | None = None


class SessionTimelineResponse(BaseModel):
    events: list[EventEnvelopeDTO] = Field(default_factory=list)
    total: int = 0


class SessionViewResponse(BaseModel):
    id: str  # exact ConversationRecord.conversation_id
    workspace_id: str
    title: str
    agent_profile: str | None = None
    status: SessionStatus
    latest_run: RunSummaryResponse | None = None
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
    expires_at: datetime | None = None


class RevokeGrantRequest(BaseModel):
    conversation_id: str
    grant_id: str


# Schedules (Task 4)
class CreateScheduleRequest(BaseModel):
    schedule_kind: Literal["one_time", "daily", "weekdays"]
    timezone: str = "Asia/Ho_Chi_Minh"
    run_at: datetime | None = None
    hour: int | None = None
    minute: int | None = None
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
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    created_at: datetime


class ScheduleListResponse(BaseModel):
    items: list[ScheduleResponse] = Field(default_factory=list)
    total: int = 0


# Knowledge Ingestion (Task 2)
class CreateKnowledgeUploadRequest(BaseModel):
    """Request to initiate a knowledge document upload.

    Fields:
    - `file_name`: client-supplied original filename (informational).
    - `declared_media_type`: client's MIME type claim (validated server-side at finalize).
    - `idempotency_key`: ensures idempotent creation.
    """

    file_name: str
    declared_media_type: str
    idempotency_key: str


class KnowledgeUploadResponse(BaseModel):
    """Response to CreateKnowledgeUploadRequest or GET status.

    Contains:
    - `ingestion_id`: reference to DocumentIngestionRecord in control plane.
    - `state`: current state (UPLOADING, QUARANTINED, QUEUED, etc.).
    - `signed_upload_url`: presigned URL for PUT (only in initial ticket response).
    - `expires_at`: UTC deadline for ticket (only in initial response).

    NOTE: `object_key` and `original_object_key` are never returned to client.
    """

    ingestion_id: str
    state: str
    file_name: str
    declared_media_type: str
    detected_media_type: str | None = None
    size_bytes: int | None = None
    signed_upload_url: str | None = None
    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CompleteKnowledgeUploadResponse(BaseModel):
    """Response to complete-upload request.

    Indicates:
    - `ingestion_id`: reference to DocumentIngestionRecord.
    - `state`: updated state after completion (QUARANTINED → QUEUED).
    - `detected_media_type`: server-sniffed MIME type.
    - `size_bytes`: actual byte count validated.
    - `source_sha256`: SHA-256 computed server-side.

    NOTE: `object_key` is never returned.
    """

    ingestion_id: str
    state: str
    detected_media_type: str
    size_bytes: int
    source_sha256: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReviewKnowledgeIngestionRequest(BaseModel):
    """Request to review a REVIEW_PENDING knowledge ingestion candidate.

    Fields:
    - `decision`: "publish_reference" (publish candidate as-is) or "reject" (discard candidate).
    - `reason`: Human-readable explanation for the decision (audit trail).

    NOTE: "publish_reference" only publishes the candidate source — it does NOT
    create a KnowledgeSnapshot or enable retrieval. That's a separate flow.
    """

    decision: Literal["publish_reference", "reject"]
    reason: str


class ReviewKnowledgeIngestionResponse(BaseModel):
    """Response to review request.

    Safe DTO that only contains status info — never Markdown, object metadata, or manifest.

    Fields:
    - `ingestion_id`: reference to DocumentIngestionRecord.
    - `state`: updated state after review (PUBLISHED or REJECTED).
    - `decision`: echoed decision ("publish_reference" or "reject").
    - `updated_at`: when the review was recorded.

    NOTE: No extraction manifest, no Markdown content, no object_key.
    """

    ingestion_id: str
    state: str
    decision: Literal["publish_reference", "reject"]
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
