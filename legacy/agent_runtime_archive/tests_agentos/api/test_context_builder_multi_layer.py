import pytest

from agentos.core.context_builder import ContextBuilder
from agentos.core.models import TaskContext
from agentos.tools.registry import ToolRegistry


class StubMemoryRetriever:
    async def retrieve(self, task):
        if task.workspace_id == "ws-acme":
            return ["Acme is an enterprise client.", "Acme preferred currency is USD."]
        return ["Beta is a startup.", "Beta preferred currency is EUR."]


class StubHistoryProvider:
    async def get_recent_messages(self, conversation_id: str, workspace_id: str, limit: int = 10):
        if conversation_id == "conv-acme" and workspace_id == "ws-acme":
            return [
                {"role": "user", "content": "Hello, Acme bot"},
                {"role": "assistant", "content": "Hello! How can I assist Acme Corp today?"},
            ]
        elif conversation_id == "conv-beta" and workspace_id == "ws-beta":
            return [
                {"role": "user", "content": "Hello, Beta bot"},
                {"role": "assistant", "content": "Hello Beta team!"},
            ]
        return []


@pytest.mark.asyncio
async def test_context_builder_multi_layer_history_and_memory():
    registry = ToolRegistry()
    builder = ContextBuilder(
        tool_registry=registry,
        memory_retriever=StubMemoryRetriever(),
        conversation_history_provider=StubHistoryProvider(),
    )

    task = TaskContext(
        goal="Prepare Q3 report",
        agent_key="analyst",
        workspace_id="ws-acme",
        company_id="comp-acme",
        metadata={"conversation_id": "conv-acme"},
    )

    ctx = await builder.build(task)
    assert len(ctx.conversation_messages) == 2
    assert ctx.conversation_messages[0]["content"] == "Hello, Acme bot"
    assert len(ctx.memory_snippets) == 2
    assert "Acme preferred currency is USD." in ctx.memory_snippets
    assert ctx.knowledge_snippets == []  # Phase 7 graceful fallback


@pytest.mark.asyncio
async def test_context_builder_cross_tenant_isolation():
    registry = ToolRegistry()
    builder = ContextBuilder(
        tool_registry=registry,
        memory_retriever=StubMemoryRetriever(),
        conversation_history_provider=StubHistoryProvider(),
    )

    task_acme = TaskContext(
        goal="Analyze burn rate",
        agent_key="analyst",
        workspace_id="ws-acme",
        company_id="comp-acme",
        metadata={"conversation_id": "conv-acme"},
    )

    task_beta = TaskContext(
        goal="Analyze burn rate",
        agent_key="analyst",
        workspace_id="ws-beta",
        company_id="comp-beta",
        metadata={"conversation_id": "conv-beta"},
    )

    ctx_acme = await builder.build(task_acme)
    ctx_beta = await builder.build(task_beta)

    # Acme context
    assert "Acme preferred currency is USD." in ctx_acme.memory_snippets
    assert "Beta preferred currency is EUR." not in ctx_acme.memory_snippets
    assert ctx_acme.conversation_messages[0]["content"] == "Hello, Acme bot"

    # Beta context
    assert "Beta preferred currency is EUR." in ctx_beta.memory_snippets
    assert "Acme preferred currency is USD." not in ctx_beta.memory_snippets
    assert ctx_beta.conversation_messages[0]["content"] == "Hello, Beta bot"
