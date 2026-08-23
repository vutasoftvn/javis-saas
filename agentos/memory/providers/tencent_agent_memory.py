from __future__ import annotations

from typing import Any, Optional

from agentos.memory.base import MemoryStore
from agentos.memory.models import MemoryItem, MemoryKind


class TencentAgentMemoryStore:
    """Stub adapter for Tencent Cloud Agent Memory (MEM-0 / TencentDB vector memory).
    
    Planned integration for hybrid cloud environments with TencentDB vector backing.
    """

    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None) -> None:
        self._endpoint = endpoint
        self._api_key = api_key

    async def put(self, item: MemoryItem) -> None:
        raise NotImplementedError("TencentAgentMemoryStore is a stub in Phase 7.")

    async def search(
        self,
        *,
        workspace_id: str,
        agent_key: Optional[str] = None,
        kind: Optional[MemoryKind] = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        raise NotImplementedError("TencentAgentMemoryStore is a stub in Phase 7.")

    async def delete(self, item_id: str) -> None:
        raise NotImplementedError("TencentAgentMemoryStore is a stub in Phase 7.")
