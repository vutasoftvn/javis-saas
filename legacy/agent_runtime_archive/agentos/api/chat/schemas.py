from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


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
    knowledge_ingest_status: str

    class Config:
        from_attributes = True


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
    status: str
    created_at: datetime
    attachments: list[MessageAttachmentResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    company_id: str
    workspace_id: str
    created_by_principal: str
    title: str
    active_agent_profile: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    messages: list[MessageResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


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
    decided_at: datetime


class EventEnvelopeDTO(BaseModel):
    run_id: str
    conversation_id: str
    sequence: int
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
