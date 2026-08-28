"""Conversation History Ports for COSA Agent Platform.

Theo Hermes/LangGraph Integration Plan §3 (Phase 8, Phase 9 Track 9A):
Định nghĩa ConversationHistoryPort Protocol để truy xuất lịch sử hội thoại.
Bảo đảm Invariant tách biệt 3 định danh:
    conversation_id != run_id != checkpoint_ref/thread_id
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = ["ConversationHistoryPort"]


@runtime_checkable
class ConversationHistoryPort(Protocol):
    """Cổng truy xuất lịch sử hội thoại chuẩn cho các dịch vụ Agent."""

    async def recent_messages(self, conversation_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Lấy danh sách tin nhắn gần nhất theo conversation_id."""
        ...

    async def search_messages(
        self, conversation_id: str, query: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Tìm kiếm tin nhắn trong phạm vi một cuộc trò chuyện cụ thể."""
        ...

    async def get_thread_context(self, run_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Lấy ngữ cảnh tin nhắn gắn với một run_id cụ thể."""
        ...
