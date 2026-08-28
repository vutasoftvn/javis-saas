from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING
from agent_core.memory.base import MemoryStore
from agent_core.memory.models import MemoryItem, MemoryKind

if TYPE_CHECKING:
    from agent_core.memory.retention import RetentionPolicy

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
        retention: Optional["RetentionPolicy"] = None,
    ) -> None:
        from agent_core.memory.retention import RetentionPolicy

        self._store = store
        self._retention: RetentionPolicy = retention or RetentionPolicy()

    @classmethod
    def in_memory(cls) -> "MemoryService":
        from agent_core.memory.retention import RetentionPolicy
        from agent_core.memory.store import InMemoryMemoryStore

        return cls(InMemoryMemoryStore(), retention=RetentionPolicy.permissive())

    @classmethod
    def for_production(cls, database_url: Optional[str] = None) -> "MemoryService":
        from agent_core.memory.retention import RetentionPolicy
        from agent_core.memory.store import get_memory_store  # raise nếu thiếu AGENT_CORE_DATABASE_URL

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
        tenant_id: Optional[str] = None,
        provenance_run_id: Optional[str] = None,
    ) -> MemoryItem:
        item = MemoryItem(
            workspace_id=workspace_id,
            agent_key=agent_key,
            kind=kind,
            content=content,
            importance=importance,
            tags=tags,
            tenant_id=tenant_id,
            provenance_run_id=provenance_run_id,
        )
        await self._store.put(item)
        return item

    async def retrieve_memories(
        self,
        *,
        workspace_id: str,
        agent_key: Optional[str] = None,
        kind: Optional[MemoryKind] = None,
        limit: int = 10,
    ) -> list[MemoryItem]:
        return await self._store.search(
            workspace_id=workspace_id,
            agent_key=agent_key,
            kind=kind,
            limit=limit,
        )
