from __future__ import annotations

import os
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


def get_memory_store(database_url: Optional[str] = None) -> MemoryStore:
    """Production mặc định dùng PostgresMemoryStore — KHÔNG âm thầm rơi về
    in-memory (DB_FINAL_CUTOVER.md §9.1). Muốn in-memory cho test/dev, gọi
    InMemoryMemoryStore() trực tiếp thay vì qua hàm này."""
    resolved_url = database_url or os.environ.get("AGENT_CORE_DATABASE_URL")
    if not resolved_url:
        raise RuntimeError(
            "get_memory_store() requires AGENT_CORE_DATABASE_URL to be set — "
            "production must not silently fall back to InMemoryMemoryStore. "
            "For tests/local dev, use InMemoryMemoryStore() directly."
        )
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from agent_core.memory.providers.postgres import PostgresMemoryStore

    engine = create_async_engine(resolved_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return PostgresMemoryStore(db_session_factory=factory)
