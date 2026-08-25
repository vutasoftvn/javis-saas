from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

__all__ = ["ConversationRecord", "MessageRecord", "MessageAttachmentRecord"]


class ConversationRecord(BaseModel):
    """Bản ghi hội thoại trong agent_conversation.conversations."""

    conversation_id: str = Field(default_factory=lambda: f"conv_{uuid.uuid4().hex[:12]}")
    tenant_id: Optional[str] = None
    company_id: Optional[str] = None
    workspace_id: Optional[str] = None
    created_by_principal: str
    title: str = "New Conversation"
    active_agent_profile: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    archived_at: Optional[datetime] = None


class MessageAttachmentRecord(BaseModel):
    """Bản ghi file đính kèm trong agent_conversation.message_attachments."""

    attachment_id: str = Field(default_factory=lambda: f"att_{uuid.uuid4().hex[:12]}")
    message_id: str
    object_ref: str
    media_type: str
    file_name: str
    size: int = 0
    checksum: Optional[str] = None
    knowledge_ingest_status: str = "COMPLETED"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MessageRecord(BaseModel):
    """Bản ghi tin nhắn trong agent_conversation.messages.

    `sequence_no` do DB tự sinh (BIGSERIAL) khi insert qua PostgresConversationRepository —
    giá trị trên record trước khi ghi chỉ là placeholder, không dùng để order.
    """

    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    conversation_id: str
    sequence_no: Optional[int] = None
    role: str = "user"
    content: str
    run_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    status: str = "completed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attachments: list[MessageAttachmentRecord] = Field(default_factory=list)
