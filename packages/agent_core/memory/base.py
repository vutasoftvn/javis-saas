from __future__ import annotations

from typing import Any, Optional, Protocol
from agent_core.memory.models import MemoryItem, MemoryKind

__all__ = ["MemoryError", "MemoryNotFoundError", "MemoryStore"]


class MemoryError(Exception):
    """Lỗi nền tảng của hệ thống Memory."""


class MemoryNotFoundError(MemoryError):
    def __init__(self, memory_id: str) -> None:
        super().__init__(f"MemoryItem '{memory_id}' not found")
        self.memory_id = memory_id


class MemoryStore(Protocol):
    """Giao thức lưu trữ và tìm kiếm MemoryItem theo phạm vi Workspace/Agent."""

    async def put(self, item: MemoryItem) -> None: ...

    async def search(
        self,
        *,
        workspace_id: str,
        agent_key: Optional[str] = None,
        kind: Optional[MemoryKind] = None,
        limit: int = 20,
    ) -> list[MemoryItem]: ...

    async def delete(self, item_id: str) -> None: ...
