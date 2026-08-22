"""Production composition root (addendum §7 / COSA_ARCHITECTURE_REVIEW_2026-08-22.md
§2 mục "Quyết định đã chốt"): `build_cosa_agent_plane()` must wire cluster tools,
memory retrieval, and skill routing into the `AgentRuntime` it returns — not just
leave them available in source but unused by production composition."""
from __future__ import annotations

import pytest

from agentos.core.audit_sink import SqliteAuditSink
from agentos.core.factory import build_cosa_agent_plane
from agentos.core.model_provider import ModelResponse, StubModelProvider, ToolCallRequest
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.store import InMemoryMemoryStore


@pytest.mark.asyncio
async def test_build_cosa_agent_plane_wires_cluster_tools_memory_and_skills():
    memory_store = InMemoryMemoryStore()
    await memory_store.put(
        MemoryItem(
            workspace_id="ws1",
            agent_key="agent1",
            kind=MemoryKind.SEMANTIC,
            content="the weekly review always starts with blockers",
            importance=1.0,
        )
    )
    provider = StubModelProvider([ModelResponse(text="done")])

    runtime = build_cosa_agent_plane(model_provider=provider, memory_store=memory_store)
    task = TaskContext(goal="run a weekly review", agent_key="agent1", workspace_id="ws1")

    result = await runtime.run(task)

    assert result.status == AgentRunStatus.COMPLETED
    assert runtime.last_context is not None
    assert "task_create" in runtime.last_context.tool_names
    assert runtime.last_context.memory_snippets != []
    assert any("review" in instruction.lower() for instruction in runtime.last_context.skill_instructions)


@pytest.mark.asyncio
async def test_build_cosa_agent_plane_gates_business_write_tools_through_shared_audit_trail(tmp_path):
    """A cluster tool with permission_class=MODIFY_BUSINESS_DATA (e.g. task_create) must
    stop at REQUIRE_APPROVAL, and PolicyEngine + ApprovalService must share one audit
    trail — proving policy gate, approval gate, and audit/trace are wired together,
    not three independent mechanisms that happen to coexist."""
    audit_sink = SqliteAuditSink(db_path=tmp_path / "audit.sqlite3")
    provider = StubModelProvider(
        [ModelResponse(tool_call=ToolCallRequest(tool_name="task_create", arguments={"title": "x"}))]
    )

    runtime = build_cosa_agent_plane(model_provider=provider, audit_sink=audit_sink)
    task = TaskContext(goal="create a task", agent_key="agent1", workspace_id="ws1")

    result = await runtime.run(task)

    assert result.status == AgentRunStatus.WAITING_APPROVAL
    assert result.approval_id is not None

    events = audit_sink.export_run(runtime.last_run.id)
    event_types = [e["event_type"] for e in events]
    assert "policy.evaluated" in event_types
    assert "approval.requested" in event_types


def test_build_cosa_agent_plane_initializes_non_empty_tool_registry():
    provider = StubModelProvider([])
    runtime = build_cosa_agent_plane(model_provider=provider)
    assert len(runtime._tool_registry.list_tools()) > 0
    assert "task_create" in runtime._tool_registry.names()
