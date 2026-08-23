from __future__ import annotations

from typing import Any, Optional
from agent_core.memory.base import MemoryStore
from agent_core.memory.models import MemoryItem, MemoryKind
from agent_core.memory.store import InMemoryMemoryStore

__all__ = ["MemoryService"]


class MemoryService:
    """Canonical Memory Service theo Master Guide §25."""

    def __init__(self, store: Optional[MemoryStore] = None) -> None:
        self._store = store or InMemoryMemoryStore()

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
