from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from agent_core.ids import uuid7  # LeafId UUIDv7 cho conversation_id (M2 §3)

__all__ = ["ConversationRecord", "MessageAttachmentRecord", "MessageRecord"]


class ConversationRecord(BaseModel):
    """Bản ghi hội thoại trong agent_conversation.conversations.

    workspace_id là khóa tenant duy nhất sau Task 7 (2026-08-27).
    """

    conversation_id: str = Field(default_factory=lambda: f"conv_{uuid7().hex}")
    workspace_id: str | None = None
    created_by_principal: str
    title: str = "New Conversation"
    active_agent_profile: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    archived_at: datetime | None = None


class MessageAttachmentRecord(BaseModel):
    """Bản ghi file đính kèm trong agent_conversation.message_attachments."""

    attachment_id: str = Field(default_factory=lambda: f"att_{uuid.uuid4().hex[:12]}")
    message_id: str
    object_ref: str
    media_type: str
    file_name: str
    size: int = 0
    checksum: str | None = None
    knowledge_ingest_status: str = "COMPLETED"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessageRecord(BaseModel):
    """Bản ghi tin nhắn trong agent_conversation.messages.

    `sequence_no` do DB tự sinh (BIGSERIAL) khi insert qua PostgresConversationRepository —
    giá trị trên record trước khi ghi chỉ là placeholder, không dùng để order.
    """

    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    conversation_id: str
    sequence_no: int | None = None
    role: str = "user"
    content: str
    run_id: str | None = None
    parent_message_id: str | None = None
    status: str = "completed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    attachments: list[MessageAttachmentRecord] = Field(default_factory=list)
