from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from agentos.memory.models import MemoryItem, MemoryKind


class MemoryNotFoundError(Exception):
    def __init__(self, item_id: str) -> None:
        super().__init__(f"Memory item not found: {item_id}")
        self.item_id = item_id


class ConfigurationError(Exception):
    """Raised when a memory provider is improperly configured."""
    pass


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
