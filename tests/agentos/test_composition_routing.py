from __future__ import annotations

import pytest

from agentos.core.adapters.deepseek_harness_adapter import DeepSeekHarnessRuntimeAdapter
from agentos.core.executor import Executor
from agentos.core.model_provider import ModelResponse, StubModelProvider
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.runtime import AgentRuntime
from agentos.core.trace import TraceRecorder
from agentos.orchestration.adk.orchestrator import AdkOrchestrator
from agentos.tools.registry import ToolRegistry


def test_runtime_adapter_resolution():
    model_provider = StubModelProvider([ModelResponse(text="Done")])
    tool_registry = ToolRegistry()
    runtime = AgentRuntime(model_provider=model_provider, tool_registry=tool_registry)
    trace = TraceRecorder(run_id="test_run")

    # 1. Default request -> Native Executor
    task_default = TaskContext(goal="Simple task", agent_key="agent1", workspace_id="ws1")
    adapter_default = runtime._resolve_adapter(task_default, trace)
    assert isinstance(adapter_default, Executor)

    # 2. Multi-agent request -> AdkOrchestrator
    task_multi = TaskContext(
        goal="Launch marketing campaign",
        agent_key="chief_of_staff",
        workspace_id="ws1",
        metadata={"orchestration_mode": "multi_agent"},
    )
    adapter_multi = runtime._resolve_adapter(task_multi, trace)
    assert isinstance(adapter_multi, AdkOrchestrator)

    # 3. DeepSeek Harness request -> DeepSeekHarnessRuntimeAdapter
    task_dsh = TaskContext(
        goal="Deep reasoning task",
        agent_key="analyst",
        workspace_id="ws1",
        metadata={"preferred_runtime": "deepseek_harness"},
    )
    adapter_dsh = runtime._resolve_adapter(task_dsh, trace)
    assert isinstance(adapter_dsh, DeepSeekHarnessRuntimeAdapter)


@pytest.mark.asyncio
async def test_runtime_end_to_end_multi_agent_execution():
    model_provider = StubModelProvider([
        ModelResponse(text="Sales report: 5 deals closed."),
        ModelResponse(text="Finance report: Budget balanced."),
        ModelResponse(text="Executive synthesis: Healthy growth."),
    ])
    tool_registry = ToolRegistry()
    runtime = AgentRuntime(model_provider=model_provider, tool_registry=tool_registry)

    task = TaskContext(
        goal="Quarterly review",
        agent_key="chief_of_staff",
        workspace_id="ws1",
        metadata={"orchestration_mode": "multi_agent", "domains": ["sales", "finance"]},
    )

    result = await runtime.run(task)
    assert result.status == AgentRunStatus.COMPLETED
    assert "Executive synthesis" in result.output
