import pytest

from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.store import InMemoryMemoryStore, MemoryNotFoundError, MemoryStore


def test_in_memory_store_satisfies_protocol():
    assert isinstance(InMemoryMemoryStore(), MemoryStore)


@pytest.mark.asyncio
async def test_put_then_search_returns_item_scoped_to_workspace():
    store = InMemoryMemoryStore()
    item = MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="did X")
    await store.put(item)

    results = await store.search(workspace_id="ws1")

    assert results == [item]


@pytest.mark.asyncio
async def test_search_excludes_other_workspaces():
    store = InMemoryMemoryStore()
    await store.put(MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="x"))
    await store.put(MemoryItem(workspace_id="ws2", agent_key="a1", kind=MemoryKind.EPISODIC, content="y"))

    results = await store.search(workspace_id="ws1")

    assert len(results) == 1
    assert results[0].workspace_id == "ws1"


@pytest.mark.asyncio
async def test_search_filters_by_kind():
    store = InMemoryMemoryStore()
    await store.put(MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="e"))
    await store.put(MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.SEMANTIC, content="s"))

    results = await store.search(workspace_id="ws1", kind=MemoryKind.SEMANTIC)

    assert len(results) == 1
    assert results[0].kind == MemoryKind.SEMANTIC


@pytest.mark.asyncio
async def test_delete_missing_item_raises():
    store = InMemoryMemoryStore()
    with pytest.raises(MemoryNotFoundError):
        await store.delete("missing")


@pytest.mark.asyncio
async def test_delete_removes_item():
    store = InMemoryMemoryStore()
    item = MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="x")
    await store.put(item)
    await store.delete(item.id)

    results = await store.search(workspace_id="ws1")

    assert results == []
