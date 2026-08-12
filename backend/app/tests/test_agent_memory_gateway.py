import pytest

from app.modules.agent_memory.adapters.null_adapter import NullAgentMemoryAdapter
from app.modules.agent_memory.gateway import AgentMemoryGateway


def test_gateway_is_abstract_and_cannot_be_instantiated():
    with pytest.raises(TypeError):
        AgentMemoryGateway()


@pytest.mark.asyncio
async def test_null_adapter_capture_is_noop():
    adapter = NullAgentMemoryAdapter()
    assert await adapter.capture({"any": "event"}) is None


@pytest.mark.asyncio
async def test_null_adapter_recall_and_search_return_empty_list():
    adapter = NullAgentMemoryAdapter()
    assert await adapter.recall({"q": "x"}) == []
    assert await adapter.search({"q": "x"}) == []


@pytest.mark.asyncio
async def test_null_adapter_getters_return_none():
    adapter = NullAgentMemoryAdapter()
    assert await adapter.get_task_context("task-1") is None
    assert await adapter.get_scenario("scenario-1") is None
    assert await adapter.get_profile("user-1") is None


@pytest.mark.asyncio
async def test_null_adapter_end_session_and_forget_are_noop():
    adapter = NullAgentMemoryAdapter()
    assert await adapter.end_session("sess-1") is None
    assert await adapter.forget("mem-1") is None


@pytest.mark.asyncio
async def test_null_adapter_promote_candidate_reports_unavailable():
    adapter = NullAgentMemoryAdapter()
    result = await adapter.promote_candidate("cand-1")
    assert result == {"status": "unavailable"}


@pytest.mark.asyncio
async def test_null_adapter_export_returns_empty_list():
    adapter = NullAgentMemoryAdapter()
    assert await adapter.export({"scope": "all"}) == []


def test_null_adapter_implements_every_gateway_abstract_method():
    """Guards against a future AgentMemoryGateway method being added without
    a corresponding NullAgentMemoryAdapter implementation - that would make
    the flag-off/default path raise instead of degrading gracefully."""
    missing = AgentMemoryGateway.__abstractmethods__ - set(dir(NullAgentMemoryAdapter))
    assert missing == set()
