from __future__ import annotations

import pytest

from agentos.memory.base import MemoryStore
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.providers import (
    ConfigurationError,
    InMemoryMemoryStore,
    PostgresMemoryStore,
    TencentAgentMemoryStore,
)


def test_providers_exports_and_protocols():
    assert issubclass(InMemoryMemoryStore, MemoryStore)
    assert issubclass(PostgresMemoryStore, MemoryStore)
    assert issubclass(TencentAgentMemoryStore, MemoryStore)


@pytest.mark.asyncio
async def test_tencent_agent_memory_stub_raises():
    stub = TencentAgentMemoryStore()
    item = MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="stub")

    with pytest.raises(NotImplementedError):
        await stub.put(item)

    with pytest.raises(NotImplementedError):
        await stub.search(workspace_id="ws1")

    with pytest.raises(NotImplementedError):
        await stub.delete("some-id")
