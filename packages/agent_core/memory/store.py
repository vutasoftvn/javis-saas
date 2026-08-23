from __future__ import annotations

from typing import Any, Optional
from agent_core.memory.base import MemoryNotFoundError, MemoryStore
from agent_core.memory.models import MemoryItem, MemoryKind

__all__ = ["InMemoryMemoryStore", "get_memory_store"]


class InMemoryMemoryStore:
    """In-memory implementation cho MemoryStore."""

    def __init__(self) -> None:
        self._items: dict[str, MemoryItem] = {}

    async def put(self, item: MemoryItem) -> None:
        self._items[item.id] = item.model_copy(deep=True)

    async def search(
        self,
        *,
        workspace_id: str,
        agent_key: Optional[str] = None,
        kind: Optional[MemoryKind] = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        results = [
            item
            for item in self._items.values()
            if item.workspace_id == workspace_id
            and (agent_key is None or item.agent_key == agent_key)
            and (kind is None or item.kind == kind)
        ]
        results.sort(key=lambda item: item.created_at, reverse=True)
        return results[:limit]

    async def delete(self, item_id: str) -> None:
        if item_id in self._items:
            del self._items[item_id]
        else:
            raise MemoryNotFoundError(item_id)


def get_memory_store() -> MemoryStore:
    return InMemoryMemoryStore()
