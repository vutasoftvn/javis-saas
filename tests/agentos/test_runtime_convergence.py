"""Addendum §6.4/§19 Phase 3 pin test: DeepSeek Harness (or any other
ModelProvider) must never be able to bypass COSA governance. Executor's
policy/approval gating (agentos/core/executor.py:94-116) runs on the tool
call decision, not on which ModelProvider produced it — this test proves
that by using a ModelProvider implementation that is structurally distinct
from StubModelProvider (not a subclass, no shared code), so the gate
provably isn't special-casing a specific provider class."""
from __future__ import annotations

import pytest

from agentos.core.model_provider import ModelResponse, ToolCallRequest
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.runtime import AgentRuntime
from agentos.tools.registry import ToolRegistry, ToolSpec


async def _noop(arguments: dict) -> dict:
    return {}


class _AlternateModelProvider:
    """Deliberately not StubModelProvider and not a subclass of it —
    only duck-types the ModelProvider protocol (agentos/core/model_provider.py),
    the same way agentos.core.adapters.deepseek_harness_provider.DeepSeekHarnessModelProvider does."""

    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = list(responses)

    async def generate(self, *, system_prompt: str, messages: list[dict]) -> ModelResponse:
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_business_write_tool_gates_through_approval_regardless_of_model_provider():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="task_create", description="d", handler=_noop, permission_class="MODIFY_BUSINESS_DATA")
    )
    provider = _AlternateModelProvider(
        [ModelResponse(tool_call=ToolCallRequest(tool_name="task_create", arguments={"title": "x"}))]
    )
    runtime = AgentRuntime(provider, registry)
    task = TaskContext(goal="create a task", agent_key="agent1", workspace_id="ws1")

    result = await runtime.run(task)

    assert result.status == AgentRunStatus.WAITING_APPROVAL
    assert result.approval_id is not None
