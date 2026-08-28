"""Integration test for RealOpenAIAgentsSDKKernel checkpoint and resume with real tool schemas.

Covers:
1. Run execution encountering REQUIRE_APPROVAL policy pauses in WAITING_APPROVAL.
2. Checkpoint and RunApprovalRecord are stored with correct approval_id (`appr_{run_id}_{tool_call_id}`).
3. Resume with approved=True executes the tool and completes the run.
4. Resume with approved=False rejects the interruption and finishes/handles gracefully without crash.
5. Optional live DeepSeek test when DEEPSEEK_API_KEY is available.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("agents")

from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.contracts.capability import CapabilitySpec
from agent_core.contracts.run import RunRequest, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.governance.contracts import ExecutionMode
from agent_core.runs.repository import InMemoryRunRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import (
    FakeSDKModel,
    text_response,
    tool_call_response,
)


def _build_finance_spec() -> AgentSpec:
    return AgentSpec(
        id="finance_payout_agent",
        version="1.0.0",
        instructions="You are an authorized finance disbursement agent.",
        capability_refs=["finance.payout.execute"],
    ).with_hash()


def _build_request(
    prompt: str = "Disburse payout $500", spec: AgentSpec | None = None
) -> RunRequest:
    s = spec or _build_finance_spec()
    return RunRequest(
        input={"prompt": prompt},
        principal="test-finance-lead",
        root_executable_ref=s.to_pinned_identity(),
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        workspace_id="ws_finance_test",
        metadata={"policy_snapshot": {"company_status": "active"}},
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_checkpoint_resume_approval_approved_path():
    """Checkpoint and resume on approved tool call."""
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="finance.payout.execute",
        description="Execute financial payout",
        input_schema={
            "type": "object",
            "properties": {"amount": {"type": "number"}, "vendor": {"type": "string"}},
            "required": ["amount", "vendor"],
        },
    )
    registry.register(cap, lambda args: {})

    executed_tools: list[dict] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        executed_tools.append({"tool": tool_name, "args": args})
        return {"status": "paid", "transaction_ref": "tx_999"}

    call_id = "call_payout_chk_1"
    model = FakeSDKModel(
        responses=[
            tool_call_response(
                call_id,
                "finance.payout.execute",
                arguments='{"amount": 500, "vendor": "Acme Corp"}',
            ),
            text_response("Payout of $500 to Acme Corp successfully executed."),
        ]
    )

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=capability_executor,
        model=model,
        policy_evaluator=lambda name, args, ctx=None: "REQUIRE_APPROVAL",
    )
    spec = _build_finance_spec()
    request = _build_request(spec=spec)

    # 1. First invocation pauses on approval
    result = await kernel.run(request, spec)

    assert result.status == RunStatus.WAITING_APPROVAL
    assert len(executed_tools) == 0
    assert result.interruptions_waits is not None
    assert len(result.interruptions_waits) == 1

    wait_desc = result.interruptions_waits[0]
    expected_appr_id = f"appr_{result.run_id}_{call_id}"
    assert wait_desc.related_ref == expected_appr_id

    # Verify saved checkpoint in repo
    checkpoint = await repo.get_checkpoint(wait_desc.checkpoint_ref)
    assert checkpoint is not None
    assert checkpoint.run_id == result.run_id

    # Verify approval record in repo
    approval = await repo.get_approval(expected_appr_id)
    assert approval is not None
    assert approval.status == "pending"
    assert approval.action == "finance.payout.execute"
    assert approval.tool_call_id == call_id

    # 2. Resume with approval
    resumed = await kernel.resume(
        result.run_id,
        wait_desc.checkpoint_ref,
        {"approved": True, "approved_tool_calls": {call_id: True}},
    )

    assert resumed.status == RunStatus.COMPLETED
    assert len(executed_tools) == 1
    assert executed_tools[0]["args"] == {"amount": 500, "vendor": "Acme Corp"}
    assert "Acme Corp" in str(resumed.final_output)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_checkpoint_resume_approval_rejected_path():
    """Checkpoint and resume on rejected tool call."""
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="finance.payout.execute",
        description="Execute financial payout",
        input_schema={
            "type": "object",
            "properties": {"amount": {"type": "number"}, "vendor": {"type": "string"}},
            "required": ["amount", "vendor"],
        },
    )
    registry.register(cap, lambda args: {})

    executed_tools: list[dict] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        executed_tools.append({"tool": tool_name, "args": args})
        return {"status": "paid"}

    call_id = "call_payout_chk_reject"
    model = FakeSDKModel(
        responses=[
            tool_call_response(
                call_id,
                "finance.payout.execute",
                arguments='{"amount": 500, "vendor": "Acme Corp"}',
            ),
            text_response("Payout was rejected by finance lead."),
        ]
    )

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=capability_executor,
        model=model,
        policy_evaluator=lambda name, args, ctx=None: "REQUIRE_APPROVAL",
    )
    spec = _build_finance_spec()
    request = _build_request(spec=spec)

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.WAITING_APPROVAL
    wait_desc = result.interruptions_waits[0]

    # Resume with rejection
    resumed = await kernel.resume(
        result.run_id,
        wait_desc.checkpoint_ref,
        {"approved": False},
    )

    # Tool handler must NOT have been executed
    assert len(executed_tools) == 0
    # Status completed with graceful rejection acknowledgment
    assert resumed.status == RunStatus.COMPLETED
    assert "rejected" in str(resumed.final_output).lower()


DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.live_provider
@pytest.mark.skipif(
    not DEEPSEEK_API_KEY,
    reason="DEEPSEEK_API_KEY not set — skipping live DeepSeek checkpoint/resume tool call test",
)
async def test_openai_agents_sdk_kernel_live_deepseek_tool_call():
    """Live provider test: DeepSeek generates real tool call and completes round-trip."""
    from agents.extensions.models.litellm_model import LitellmModel

    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="calculator_multiply",
        description="Multiply two numbers a and b",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )
    registry.register(cap, lambda args: {})

    captured: list[dict] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        captured.append(args)
        return {"result": args.get("a", 0) * args.get("b", 0)}

    model = LitellmModel(
        model="deepseek/deepseek-chat",
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        api_key=DEEPSEEK_API_KEY,
    )
    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=capability_executor,
        model=model,
        policy_evaluator=lambda name, args, ctx=None: "ALLOW",
    )
    spec = AgentSpec(
        id="deepseek_live_calc_agent",
        version="1.0.0",
        instructions="You are a helpful assistant. Always use calculator_multiply to multiply numbers.",
        capability_refs=["calculator_multiply"],
    ).with_hash()

    request = RunRequest(
        input={"prompt": "Multiply 6 by 7 using calculator_multiply tool."},
        principal="test-suite",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_live_test",
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert len(captured) >= 1
    assert "42" in str(result.final_output)
