from __future__ import annotations

import asyncio
import time
import pytest

from agentos.core.approval import ApprovalService
from agentos.core.context import AgentContext
from agentos.core.executor import ToolApprovalRequiredError
from agentos.core.model_provider import ModelProvider, ModelResponse, ToolCallRequest
from agentos.core.models import TaskContext
from agentos.core.policy import PolicyEngine, ToolPermission, ToolRiskLevel
from agentos.orchestration.adk.orchestrator import AdkOrchestrator
from agentos.tools.registry import ToolRegistry, ToolSpec
from agentos.tools.spec import ToolSpecV2


class _SlowDomainModelProvider(ModelProvider):
    async def generate(self, system_prompt: str, messages: list[dict]) -> ModelResponse:
        # Simulate thinking delay per specialist
        await asyncio.sleep(0.08)
        return ModelResponse(text="Specialist domain analysis complete.")


class _ToolRequiringApprovalModel(ModelProvider):
    async def generate(self, system_prompt: str, messages: list[dict]) -> ModelResponse:
        return ModelResponse(
            tool_call=ToolCallRequest(tool_name="finance.transfer.funds", arguments={"amount": 5000})
        )


@pytest.mark.asyncio
async def test_adk_orchestrator_runs_specialists_in_parallel():
    registry = ToolRegistry()
    model_provider = _SlowDomainModelProvider()

    orchestrator = AdkOrchestrator(
        model_provider=model_provider,
        tool_registry=registry,
        default_domains=["sales", "finance"],
    )

    task = TaskContext(
        goal="Scale revenue and optimize budget",
        agent_key="chief_of_staff",
        workspace_id="ws1",
    )
    context = AgentContext(task=task, system_policy="Chief of staff policy")

    start_time = time.perf_counter()
    output, tool_calls = await orchestrator.run(context)
    elapsed = time.perf_counter() - start_time

    assert "Specialist domain analysis complete" in output
    assert "SALES" in output
    assert "FINANCE" in output

    # 2 specialists (each taking 0.08s) + synthesis (0.08s) running concurrently:
    # Parallel execution takes ~0.16s (0.08 parallel specialists + 0.08 synthesis)
    # Sequential would take ~0.24s (0.08 + 0.08 + 0.08)
    assert elapsed < 0.22, f"Orchestrator took {elapsed:.3f}s, expected parallel execution < 0.22s"


@pytest.mark.asyncio
async def test_adk_orchestrator_respects_governance_and_approval_gate():
    async def transfer_handler(args):
        return {"transferred": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpecV2(
            name="finance.transfer.funds",
            description="Transfer funds",
            handler=transfer_handler,
            risk_level=ToolRiskLevel.HIGH,
            tool_permission=ToolPermission.ADMIN_WRITE,
            approval_policy="always",
        )
    )

    approval_service = ApprovalService()
    policy_engine = PolicyEngine()
    model_provider = _ToolRequiringApprovalModel()

    orchestrator = AdkOrchestrator(
        model_provider=model_provider,
        tool_registry=registry,
        policy_engine=policy_engine,
        approval_service=approval_service,
        default_domains=["finance"],
    )

    task = TaskContext(
        goal="Execute capital transfer",
        agent_key="chief_of_staff",
        workspace_id="ws1",
    )
    context = AgentContext(task=task, system_policy="Chief of staff policy")

    # When specialist attempts high-risk tool requiring approval, ToolApprovalRequiredError is raised
    with pytest.raises(ToolApprovalRequiredError) as exc_info:
        await orchestrator.run(context)

    assert exc_info.value.tool_name == "finance.transfer.funds"
    assert exc_info.value.approval_id is not None
