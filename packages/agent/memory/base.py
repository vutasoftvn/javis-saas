from __future__ import annotations

from typing import Protocol

from agent.memory.models import MemoryItem, MemoryKind

__all__ = ["ConfigurationError", "MemoryError", "MemoryNotFoundError", "MemoryStore"]


class MemoryError(Exception):
    """Lỗi nền tảng của hệ thống Memory."""


class MemoryNotFoundError(MemoryError):
    def __init__(self, memory_id: str) -> None:
        super().__init__(f"MemoryItem '{memory_id}' not found")
        self.memory_id = memory_id


class ConfigurationError(MemoryError):
    """Lỗi cấu hình store — vd thiếu db_session_factory bắt buộc."""


class MemoryStore(Protocol):
    """Giao thức lưu trữ và tìm kiếm MemoryItem theo phạm vi Workspace/Agent."""

    async def put(self, item: MemoryItem) -> None: ...

    async def search(
        self,
        *,
        workspace_id: str,
        agent_key: str | None = None,
        kind: MemoryKind | None = None,
        limit: int = 20,
    ) -> list[MemoryItem]: ...

    async def delete(self, item_id: str, workspace_id: str) -> None: ...
