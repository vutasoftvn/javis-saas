"""Conversation Repository with Strict Tenant Isolation (Track 9A).

Theo Hermes/LangGraph Integration Plan §3 (Track 9A, HL-03):
Lưu trữ và tìm kiếm tin nhắn hội thoại, đảm bảo cách ly dữ liệu tuyệt đối giữa các tenant:
Tenant A không bao giờ tìm thấy tin nhắn của Tenant B kể cả khi nội dung query trùng khớp.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

__all__ = ["ConversationMessage", "ConversationRepository"]


class ConversationMessage(BaseModel):
    id: str
    conversation_id: str
    workspace_id: str  # sole tenant key after Task 7 migration
    sender_id: str
    role: str  # user, assistant, system
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationRepository:
    """Repository quản lý hội thoại với lọc tenant nghiêm ngặt (workspace_id only)."""

    def __init__(self) -> None:
        self._messages: dict[str, ConversationMessage] = {}

    async def add_message(self, message: ConversationMessage) -> None:
        self._messages[message.id] = message

    async def recent_messages(
        self, workspace_id: str, conversation_id: str, limit: int = 50
    ) -> list[ConversationMessage]:
        msgs = [
            m
            for m in self._messages.values()
            if m.workspace_id == workspace_id and m.conversation_id == conversation_id
        ]
        msgs.sort(key=lambda x: x.created_at)
        return msgs[-limit:]

    async def search_messages(
        self, workspace_id: str, conversation_id: str, query: str, limit: int = 20
    ) -> list[ConversationMessage]:
        """HL-03: Tìm kiếm có lọc theo workspace_id bắt buộc."""
        q = query.lower()
        matched = [
            m
            for m in self._messages.values()
            if m.workspace_id == workspace_id
            and m.conversation_id == conversation_id
            and q in m.content.lower()
        ]
        matched.sort(key=lambda x: x.created_at, reverse=True)
        return matched[:limit]
