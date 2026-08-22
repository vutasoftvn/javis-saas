import pytest

from agentos.core.model_provider import ModelResponse, StubModelProvider
from agentos.core.models import TaskContext
from agentos.memory.consolidation import EpisodeConsolidator
from agentos.memory.models import MemoryKind
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
