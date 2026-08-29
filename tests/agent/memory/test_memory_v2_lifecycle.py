"""Wave 8 — Memory v2 lifecycle (Blueprint V2 §26, migration 009). Verify
`MemoryStatus` filtering nhất quán giữa InMemoryMemoryStore và
PostgresMemoryStore (search() chỉ trả ACTIVE mặc định) — InMemory test được vì
không cần Postgres thật."""
from __future__ import annotations

import pytest

from agent.memory.models import MemoryItem, MemoryKind, MemoryStatus
from agent.memory.store import InMemoryMemoryStore


@pytest.mark.asyncio
async def test_search_only_returns_active_memories_by_default():
    store = InMemoryMemoryStore()

    active_item = MemoryItem(
        workspace_id="ws-1", agent_key="agent-a", kind=MemoryKind.SEMANTIC, content="Đang hiệu lực"
    )
    superseded_item = MemoryItem(
        workspace_id="ws-1",
        agent_key="agent-a",
        kind=MemoryKind.SEMANTIC,
        content="Đã bị thay thế",
        status=MemoryStatus.SUPERSEDED,
    )
    await store.put(active_item)
    await store.put(superseded_item)

    results = await store.search(workspace_id="ws-1", agent_key="agent-a")

    assert len(results) == 1
    assert results[0].id == active_item.id


@pytest.mark.asyncio
async def test_memory_item_defaults_status_active_and_generic_scope_unset():
    item = MemoryItem(workspace_id="ws-1", agent_key="agent-a", kind=MemoryKind.WORKING, content="x")
    assert item.status == MemoryStatus.ACTIVE
    assert item.scope_type is None
    assert item.scope_id is None
    assert item.provenance == {}
    assert item.supersedes_memory_id is None


@pytest.mark.asyncio
async def test_memory_supersession_chain_via_supersedes_memory_id():
    store = InMemoryMemoryStore()

    original = MemoryItem(
        workspace_id="ws-1", agent_key="agent-a", kind=MemoryKind.SEMANTIC, content="Giá trị v1"
    )
    await store.put(original)

    # Superseding: đánh dấu bản cũ SUPERSEDED, tạo bản mới trỏ supersedes_memory_id.
    original.status = MemoryStatus.SUPERSEDED
    await store.put(original)

    replacement = MemoryItem(
        workspace_id="ws-1",
        agent_key="agent-a",
        kind=MemoryKind.SEMANTIC,
        content="Giá trị v2",
        supersedes_memory_id=original.id,
    )
    await store.put(replacement)

    results = await store.search(workspace_id="ws-1", agent_key="agent-a")
    assert len(results) == 1
    assert results[0].content == "Giá trị v2"
    assert results[0].supersedes_memory_id == original.id
