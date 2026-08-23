import pytest

from agentos.core.model_provider import ModelResponse, StubModelProvider
from agentos.core.models import TaskContext
from agentos.memory.consolidation import EpisodeConsolidator, ProceduralConsolidator
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.store import InMemoryMemoryStore


@pytest.mark.asyncio
async def test_consolidate_stores_summarized_episode():
    provider = StubModelProvider([ModelResponse(text="Closed the Acme deal after three follow-ups.")])
    store = InMemoryMemoryStore()
    consolidator = EpisodeConsolidator(provider, store)
    task = TaskContext(goal="close acme deal", agent_key="sales_agent", workspace_id="ws1")

    item = await consolidator.consolidate(task, raw_episode_text="tool_call: crm.update ... tool_call: email.send ...")

    assert item.content == "Closed the Acme deal after three follow-ups."
    assert item.kind == MemoryKind.EPISODIC
    assert item.tags == ["consolidated"]
    stored = await store.search(workspace_id="ws1")
    assert stored == [item]


@pytest.mark.asyncio
async def test_consolidate_falls_back_to_raw_text_when_model_returns_no_text():
    provider = StubModelProvider([ModelResponse(text=None)])
    store = InMemoryMemoryStore()
    consolidator = EpisodeConsolidator(provider, store)
    task = TaskContext(goal="close acme deal", agent_key="sales_agent", workspace_id="ws1")

    item = await consolidator.consolidate(task, raw_episode_text="raw trace text")

    assert item.content == "raw trace text"


async def _put_episode(store: InMemoryMemoryStore, *, content: str, tags: list[str]) -> None:
    await store.put(
        MemoryItem(workspace_id="ws1", agent_key="sales_agent", kind=MemoryKind.EPISODIC, content=content, tags=tags)
    )


@pytest.mark.asyncio
async def test_procedural_consolidator_returns_none_below_the_occurrence_threshold():
    provider = StubModelProvider([])
    store = InMemoryMemoryStore()
    await _put_episode(store, content="episode 1", tags=["weekly-review"])
    await _put_episode(store, content="episode 2", tags=["weekly-review"])
    consolidator = ProceduralConsolidator(provider, store)

    item = await consolidator.maybe_consolidate(
        workspace_id="ws1", agent_key="sales_agent", pattern_tag="weekly-review", min_occurrences=3
    )

    assert item is None


@pytest.mark.asyncio
async def test_procedural_consolidator_creates_procedural_memory_once_threshold_reached():
    provider = StubModelProvider([ModelResponse(text="Run weekly review: check KRs, then log blockers.")])
    store = InMemoryMemoryStore()
    for i in range(3):
        await _put_episode(store, content=f"episode {i}", tags=["weekly-review"])
    consolidator = ProceduralConsolidator(provider, store)

    item = await consolidator.maybe_consolidate(
        workspace_id="ws1", agent_key="sales_agent", pattern_tag="weekly-review", min_occurrences=3
    )

    assert item is not None
    assert item.kind == MemoryKind.PROCEDURAL
    assert item.content == "Run weekly review: check KRs, then log blockers."
    assert item.tags == ["weekly-review", "procedural"]
    assert item.metadata["derived_from_episode_count"] == 3

    stored = await store.search(workspace_id="ws1", kind=MemoryKind.PROCEDURAL)
    assert stored == [item]


@pytest.mark.asyncio
async def test_procedural_consolidator_does_not_duplicate_when_called_again():
    provider = StubModelProvider([ModelResponse(text="Run weekly review: check KRs, then log blockers.")])
    store = InMemoryMemoryStore()
    for i in range(3):
        await _put_episode(store, content=f"episode {i}", tags=["weekly-review"])
    consolidator = ProceduralConsolidator(provider, store)
    first = await consolidator.maybe_consolidate(
        workspace_id="ws1", agent_key="sales_agent", pattern_tag="weekly-review", min_occurrences=3
    )
    assert first is not None

    second = await consolidator.maybe_consolidate(
        workspace_id="ws1", agent_key="sales_agent", pattern_tag="weekly-review", min_occurrences=3
    )

    assert second is None
    stored = await store.search(workspace_id="ws1", kind=MemoryKind.PROCEDURAL)
    assert len(stored) == 1


@pytest.mark.asyncio
async def test_procedural_consolidator_ignores_episodes_with_a_different_pattern_tag():
    provider = StubModelProvider([])
    store = InMemoryMemoryStore()
    for i in range(3):
        await _put_episode(store, content=f"episode {i}", tags=["other-pattern"])
    consolidator = ProceduralConsolidator(provider, store)

    item = await consolidator.maybe_consolidate(
        workspace_id="ws1", agent_key="sales_agent", pattern_tag="weekly-review", min_occurrences=3
    )

    assert item is None
