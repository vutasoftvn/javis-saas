"""Stub implementation of ConversationHistoryPort for Phase 8 composition."""

from __future__ import annotations

from typing import Any, Optional
from apps.cosa.conversations.ports import ConversationHistoryPort

__all__ = ["StubConversationHistoryPort"]


class StubConversationHistoryPort:
    """Stub implementation trả về dữ liệu rỗng an toàn cho Phase 8 composition."""

    def __init__(self, in_memory_store: Optional[dict[str, list[dict[str, Any]]]] = None) -> None:
        self._store = in_memory_store or {}

    async def recent_messages(
        self, conversation_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        return self._store.get(conversation_id, [])[:limit]

    async def search_messages(
        self, conversation_id: str, query: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        msgs = self._store.get(conversation_id, [])
        return [m for m in msgs if query.lower() in str(m.get("content", "")).lower()][:limit]

    async def get_thread_context(
        self, run_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        return []
