import pytest

from agentos.core.context_builder import ContextBuilder, DEFAULT_SYSTEM_POLICY
from agentos.core.models import TaskContext
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.retriever import MemoryRetriever
from agentos.memory.store import InMemoryMemoryStore
from agentos.tools.registry import ToolRegistry, ToolSpec


async def _noop(arguments: dict) -> dict:
    return {}


@pytest.mark.asyncio
async def test_build_includes_registered_tool_names_and_default_policy():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_noop))
    builder = ContextBuilder(registry)
    task = TaskContext(goal="say hi", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.task == task
    assert context.tool_names == ["echo"]
    assert context.system_policy == DEFAULT_SYSTEM_POLICY


@pytest.mark.asyncio
async def test_build_without_memory_retriever_returns_empty_snippets():
    registry = ToolRegistry()
    builder = ContextBuilder(registry)
    task = TaskContext(goal="say hi", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.memory_snippets == []


@pytest.mark.asyncio
async def test_build_populates_memory_snippets_from_retriever():
    registry = ToolRegistry()
    store = InMemoryMemoryStore()
    await store.put(
        MemoryItem(workspace_id="ws1", agent_key="fake", kind=MemoryKind.EPISODIC, content="closed acme corp deal")
    )
    retriever = MemoryRetriever(store)
    builder = ContextBuilder(registry, memory_retriever=retriever)
    task = TaskContext(goal="follow up acme corp deal", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.memory_snippets == ["closed acme corp deal"]
