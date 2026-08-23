from __future__ import annotations

import pytest

from agentos.core.model_provider import ModelProvider, ModelResponse
from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.providers.in_memory import InMemoryMemoryStore
from agentos.memory.service import MemoryService


class _MockModelProvider(ModelProvider):
    def __init__(self, response_text: str = "Summary of episode") -> None:
        self.response_text = response_text

    async def generate(self, system_prompt: str, messages: list[dict]) -> ModelResponse:
        return ModelResponse(text=self.response_text)


@pytest.mark.asyncio
async def test_memory_service_remember_and_recall():
    store = InMemoryMemoryStore()
    service = MemoryService(store=store)

    item1 = await service.remember(
        "Khách hàng VIP yêu cầu hợp đồng trước thứ 6",
        workspace_id="ws1",
        agent_key="sales",
        kind=MemoryKind.SEMANTIC,
        importance=0.9,
        tags=["contract", "vip"],
    )
    assert item1.workspace_id == "ws1"
    assert item1.content == "Khách hàng VIP yêu cầu hợp đồng trước thứ 6"

    # Recall by workspace and query
    recalled = await service.recall(workspace_id="ws1", query_text="hợp đồng khách hàng")
    assert len(recalled) == 1
    assert recalled[0].id == item1.id


@pytest.mark.asyncio
async def test_memory_service_forget():
    store = InMemoryMemoryStore()
    service = MemoryService(store=store)

    item = await service.remember(
        "Temporary task note",
        workspace_id="ws1",
        agent_key="sales",
    )
    recalled = await service.recall(workspace_id="ws1")
    assert len(recalled) == 1

    await service.forget(item.id)
    recalled_after = await service.recall(workspace_id="ws1")
    assert recalled_after == []


@pytest.mark.asyncio
async def test_memory_service_consolidation():
    store = InMemoryMemoryStore()
    model_provider = _MockModelProvider("Consolidated procedure summary")
    service = MemoryService(store=store, model_provider=model_provider)

    task = TaskContext(workspace_id="ws1", agent_key="sales", goal="Close deal")
    consolidated = await service.consolidate_episode(task, "User chatted with agent and closed deal")
    assert consolidated.kind == MemoryKind.EPISODIC
    assert consolidated.content == "Consolidated procedure summary"

    # Add multiple episodic memories with a pattern_tag
    for i in range(3):
        await store.put(
            MemoryItem(
                workspace_id="ws1",
                agent_key="sales",
                kind=MemoryKind.EPISODIC,
                content=f"Run step {i} of deployment",
                tags=["deploy_pattern"],
            )
        )

    procedural = await service.consolidate_procedural(
        workspace_id="ws1",
        agent_key="sales",
        pattern_tag="deploy_pattern",
        min_occurrences=3,
    )
    assert procedural is not None
    assert procedural.kind == MemoryKind.PROCEDURAL
    assert "deploy_pattern" in procedural.tags
