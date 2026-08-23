from __future__ import annotations

from agentos.memory.base import MemoryNotFoundError, MemoryStore
from agentos.memory.models import MemoryItem, MemoryKind


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
