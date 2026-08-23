"""Addendum §6.4/§19 Phase 3 pin test: DeepSeek Harness (or any other
ModelProvider or Runtime Adapter) must never be able to bypass COSA governance.
Executor, DeepSeekHarnessRuntimeAdapter, and AdkOrchestrator all enforce the exact
same policy/approval gating through PolicyEngine and ApprovalService."""
from __future__ import annotations

import pytest

from agentos.core.adapters.deepseek_harness_adapter import DeepSeekHarnessRuntimeAdapter
from agentos.core.approval import ApprovalService
from agentos.core.model_provider import ModelResponse, ToolCallRequest
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.policy import PolicyEngine
from agentos.core.runtime import AgentRuntime
from agentos.orchestration.adk.orchestrator import AdkOrchestrator
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


@pytest.mark.asyncio
async def test_deepseek_harness_runtime_adapter_enforces_approval_gating():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="transfer_funds", description="d", handler=_noop, permission_class="MODIFY_BUSINESS_DATA")
    )
    provider = _AlternateModelProvider(
        [ModelResponse(tool_call=ToolCallRequest(tool_name="transfer_funds", arguments={"amount": 1000}))]
    )
    approval_svc = ApprovalService()
    policy_eng = PolicyEngine()
    adapter = DeepSeekHarnessRuntimeAdapter(
        tool_registry=registry,
        model_provider=provider,
        policy_engine=policy_eng,
        approval_service=approval_svc,
    )
    runtime = AgentRuntime(
        model_provider=provider,
        tool_registry=registry,
        policy_engine=policy_eng,
        approval_service=approval_svc,
        runtime_adapter=adapter,
    )

    task = TaskContext(goal="transfer 1000", agent_key="finance_agent", workspace_id="ws1")
    result = await runtime.run(task)

    assert result.status == AgentRunStatus.WAITING_APPROVAL
    assert result.approval_id is not None


@pytest.mark.asyncio
async def test_adk_orchestrator_enforces_approval_gating_on_specialists():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="transfer_funds", description="d", handler=_noop, permission_class="MODIFY_BUSINESS_DATA")
    )
    provider = _AlternateModelProvider(
        [ModelResponse(tool_call=ToolCallRequest(tool_name="transfer_funds", arguments={"amount": 1000}))]
    )
    approval_svc = ApprovalService()
    policy_eng = PolicyEngine()
    orchestrator = AdkOrchestrator(
        model_provider=provider,
        tool_registry=registry,
        policy_engine=policy_eng,
        approval_service=approval_svc,
        default_domains=["finance"],
    )
    runtime = AgentRuntime(
        model_provider=provider,
        tool_registry=registry,
        policy_engine=policy_eng,
        approval_service=approval_svc,
        runtime_adapter=orchestrator,
    )

    task = TaskContext(goal="finance mission", agent_key="chief_of_staff", workspace_id="ws1")
    result = await runtime.run(task)

    assert result.status == AgentRunStatus.WAITING_APPROVAL
    assert result.approval_id is not None
