from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from agentos.memory.models import MemoryItem, MemoryKind


class MemoryNotFoundError(Exception):
    def __init__(self, item_id: str) -> None:
        super().__init__(f"Memory item not found: {item_id}")
        self.item_id = item_id


@runtime_checkable
class MemoryStore(Protocol):
    async def put(self, item: MemoryItem) -> None:
        ...

    async def search(
        self,
        *,
        workspace_id: str,
        agent_key: str | None = None,
        kind: MemoryKind | None = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        ...

    async def delete(self, item_id: str) -> None:
        ...


class InMemoryMemoryStore:
    """MVP store: process-local dict, no persistence. Useful for fast unit testing."""

    def __init__(self) -> None:
        self._items: dict[str, MemoryItem] = {}

    async def put(self, item: MemoryItem) -> None:
        self._items[item.id] = item

    async def search(
        self,
        *,
        workspace_id: str,
        agent_key: str | None = None,
        kind: MemoryKind | None = None,
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
        try:
            del self._items[item_id]
        except KeyError:
            raise MemoryNotFoundError(item_id) from None


def get_memory_store(store_type: str = "in_memory", **kwargs: Any) -> MemoryStore:
    """Factory function để cấp phát MemoryStore theo cấu hình."""
    if store_type == "pgvector":
        from agentos.memory.pgvector_store import PgVectorMemoryStore
        return PgVectorMemoryStore(**kwargs)
    return InMemoryMemoryStore()
