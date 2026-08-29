from __future__ import annotations

from typing import TYPE_CHECKING

from agent.memory.base import MemoryStore
from agent.memory.models import MemoryItem, MemoryKind

if TYPE_CHECKING:
    from agent.memory.retention import RetentionPolicy

__all__ = ["MemoryService"]


class MemoryService:
    """Canonical Memory Service theo Master Guide §25.

    `store` là tham số BẮT BUỘC — production không được âm thầm rơi về
    InMemoryMemoryStore (P1 Task 6). Dùng `MemoryService.in_memory()` cho
    test/dev, `MemoryService.for_production()` cho composition root.
    """

    def __init__(
        self,
        store: MemoryStore,
        *,
        retention: RetentionPolicy | None = None,
    ) -> None:
        from agent.memory.retention import RetentionPolicy

        self._store = store
        self._retention: RetentionPolicy = retention or RetentionPolicy()

    @classmethod
    def in_memory(cls) -> MemoryService:
        from agent.memory.retention import RetentionPolicy
        from agent.memory.store import InMemoryMemoryStore

        return cls(InMemoryMemoryStore(), retention=RetentionPolicy.permissive())

    @classmethod
    def for_production(cls, database_url: str | None = None) -> MemoryService:
        from agent.memory.retention import RetentionPolicy
        from agent.memory.store import (
            get_memory_store,  # raise nếu thiếu AGENT_DATABASE_URL
        )

        return cls(get_memory_store(database_url), retention=RetentionPolicy())

    async def record_memory(
        self,
        *,
        workspace_id: str,
        agent_key: str,
        kind: MemoryKind,
        content: str,
        importance: float = 0.5,
        tags: tuple[str, ...] = (),
        provenance_run_id: str | None = None,
    ) -> MemoryItem:
        item = MemoryItem(
            workspace_id=workspace_id,
            agent_key=agent_key,
            kind=kind,
            content=content,
            importance=importance,
            tags=tags,
            provenance_run_id=provenance_run_id,
        )
        await self._store.put(item)
        return item

    async def retrieve_memories(
        self,
        *,
        workspace_id: str,
        agent_key: str | None = None,
        kind: MemoryKind | None = None,
        limit: int = 10,
    ) -> list[MemoryItem]:
        return await self._store.search(
            workspace_id=workspace_id,
            agent_key=agent_key,
            kind=kind,
            limit=limit,
        )
