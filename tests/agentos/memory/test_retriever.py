import datetime
import pytest

from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.retriever import MemoryRetriever
from agentos.memory.store import InMemoryMemoryStore


@pytest.mark.asyncio
async def test_retrieve_returns_only_relevant_snippets():
    store = InMemoryMemoryStore()
    await store.put(
        MemoryItem(
            workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC,
            content="closed deal with acme corp", importance=0.9,
        )
    )
    await store.put(
        MemoryItem(
            workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC,
            content="unrelated note about lunch", importance=0.9,
        )
    )
    retriever = MemoryRetriever(store)
    task = TaskContext(goal="follow up on acme corp deal", agent_key="a1", workspace_id="ws1")

    snippets = await retriever.retrieve(task)

    assert snippets == ["closed deal with acme corp"]


@pytest.mark.asyncio
async def test_retrieve_returns_empty_list_when_nothing_relevant():
    store = InMemoryMemoryStore()
    await store.put(MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="unrelated"))
    retriever = MemoryRetriever(store)
    task = TaskContext(goal="follow up on acme corp deal", agent_key="a1", workspace_id="ws1")

    snippets = await retriever.retrieve(task)

    assert snippets == []


@pytest.mark.asyncio
async def test_retrieve_compresses_long_content():
    store = InMemoryMemoryStore()
    long_content = "acme corp deal " + ("details " * 100)
    await store.put(MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content=long_content))
    retriever = MemoryRetriever(store, max_chars_per_snippet=50)
    task = TaskContext(goal="acme corp deal", agent_key="a1", workspace_id="ws1")

    snippets = await retriever.retrieve(task)

    assert len(snippets) == 1
    assert len(snippets[0]) == 50
    assert snippets[0].endswith("…")


@pytest.mark.asyncio
async def test_retrieve_respects_max_snippets():
    store = InMemoryMemoryStore()
    for i in range(10):
        await store.put(
            MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content=f"acme corp deal number {i}")
        )
    retriever = MemoryRetriever(store, max_snippets=3)
    task = TaskContext(goal="acme corp deal", agent_key="a1", workspace_id="ws1")

    snippets = await retriever.retrieve(task)

    assert len(snippets) == 3


@pytest.mark.asyncio
async def test_retrieve_ranks_recent_items_higher():
    store = InMemoryMemoryStore()
    now = datetime.datetime.now(datetime.timezone.utc)
    old_time = now - datetime.timedelta(days=30)

    # Both items have identical relevance and importance, but one is newer
    await store.put(
        MemoryItem(
            workspace_id="ws1",
            agent_key="a1",
            kind=MemoryKind.EPISODIC,
            content="old deployment incident note",
            importance=0.5,
            created_at=old_time,
        )
    )
    await store.put(
        MemoryItem(
            workspace_id="ws1",
            agent_key="a1",
            kind=MemoryKind.EPISODIC,
            content="new deployment incident note",
            importance=0.5,
            created_at=now,
        )
    )

    retriever = MemoryRetriever(store, max_snippets=2)
    task = TaskContext(goal="deployment incident note", agent_key="a1", workspace_id="ws1")

    snippets = await retriever.retrieve(task)
    assert len(snippets) == 2
    assert snippets[0] == "new deployment incident note"
    assert snippets[1] == "old deployment incident note"
