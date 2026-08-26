"""Conformance test cho `RealOpenAIAgentsSDKKernel` (packages/agent_integrations/
openai_agents_sdk/kernel.py) — cùng 5-test shape với
`test_langchain_kernel.py`, dùng FakeModel duck-typed implement
`agents.models.interface.Model` (không cần API key thật cho phần lớn — 1
test riêng dùng DeepSeek key thật nằm ở
`test_openai_agents_sdk_kernel_deepseek_live.py`, skip nếu thiếu env var)."""
from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("agents")

from agent_core.contracts.capability import CapabilitySpec
from agent_core.contracts.run import RunRequest, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.governance.contracts import ExecutionMode
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import (
    FakeSDKModel,
    text_response as _text_response,
    tool_call_response as _tool_call_response,
    usage as _usage,
)


def _make_spec(capability_refs: list[str] | None = None) -> AgentSpec:
    spec = AgentSpec(
        id="test_agent",
        version="1.0.0",
        instructions="You are a test agent.",
        capability_refs=capability_refs or [],
    )
    return spec.with_hash()


def _make_request(prompt: str = "hello", *, spec: AgentSpec | None = None) -> RunRequest:
    spec = spec or _make_spec()
    return RunRequest(
        input={"prompt": prompt},
        principal="test-suite",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        workspace_id="ws_test",
    )


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_basic_response():
    model = FakeSDKModel(responses=[_text_response("Hello from OpenAI Agents SDK")])
    kernel = RealOpenAIAgentsSDKKernel(model=model)
    spec = _make_spec()

    result = await kernel.run(_make_request("hi", spec=spec), spec)

    assert result.status == RunStatus.COMPLETED
    assert "Hello from OpenAI Agents SDK" in str(result.final_output)


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_model_provider_failure_is_typed_failed_not_completed():
    model = FakeSDKModel(error=RuntimeError("simulated provider outage"))
    kernel = RealOpenAIAgentsSDKKernel(model=model)
    spec = _make_spec()

    result = await kernel.run(_make_request("hi", spec=spec), spec)

    assert result.status == RunStatus.FAILED
    assert result.errors
    assert "provider outage" in result.errors[0] or "simulated" in result.errors[0]


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_tool_call_allow_path_preserves_exact_identity():
    registry = CapabilityRegistry()
    cap = CapabilitySpec(id="weather.get", description="Get weather", input_schema={"type": "object", "properties": {}})
    registry.register(cap, lambda args: {})

    captured: dict[str, str] = {}

    async def capability_executor(tool_name: str, args: dict) -> dict:
        captured["tool_name"] = tool_name
        return {"temp_c": 21}

    call_id = "call_exact_id_123"
    model = FakeSDKModel(
        responses=[
            _tool_call_response(call_id, "weather.get"),
            _text_response("It is 21C"),
        ]
    )
    kernel = RealOpenAIAgentsSDKKernel(
        model=model,
        capability_registry=registry,
        capability_executor=capability_executor,
        policy_evaluator=lambda name, args, ctx=None: "ALLOW",
    )
    spec = _make_spec(capability_refs=["weather.get"])

    result = await kernel.run(_make_request("what is the weather", spec=spec), spec)

    assert result.status == RunStatus.COMPLETED
    assert captured["tool_name"] == "weather.get"


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_approval_pause_and_resume():
    registry = CapabilityRegistry()
    cap = CapabilitySpec(id="finance.payout.execute", description="Payout", input_schema={"type": "object", "properties": {}})
    registry.register(cap, lambda args: {})

    executed: list[str] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        executed.append(tool_name)
        return {"status": "paid"}

    call_id = "call_payout_needs_approval"
    model = FakeSDKModel(
        responses=[
            _tool_call_response(call_id, "finance.payout.execute", arguments='{"amount": 1000}'),
            _text_response("Payout complete"),
        ]
    )
    kernel = RealOpenAIAgentsSDKKernel(
        model=model,
        capability_registry=registry,
        capability_executor=capability_executor,
        policy_evaluator=lambda name, args, ctx=None: "REQUIRE_APPROVAL",
    )
    spec = _make_spec(capability_refs=["finance.payout.execute"])

    result = await kernel.run(_make_request("pay the vendor", spec=spec), spec)

    assert result.status == RunStatus.WAITING_APPROVAL
    assert executed == []  # chưa thực thi tool khi đang chờ approval
    assert result.interruptions_waits
    checkpoint_ref = result.interruptions_waits[0].checkpoint_ref

    resumed = await kernel.resume(result.run_id, checkpoint_ref, {"approved": True, "approved_tool_calls": {call_id: True}})

    assert resumed.status == RunStatus.COMPLETED
    assert executed == ["finance.payout.execute"]


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_cancellation():
    model = FakeSDKModel(responses=[_text_response("should not be reached")])
    kernel = RealOpenAIAgentsSDKKernel(model=model)
    spec = _make_spec()

    run_id = "run_cancel_test"
    request = _make_request("hi", spec=spec)
    request.run_id = run_id

    await kernel.cancel(run_id, reason="user requested stop")
    result = await kernel.run(request, spec)

    assert result.status == RunStatus.CANCELLED
    assert model.call_count == 0


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_builds_policy_context_from_metadata_not_input():
    """`request.metadata` (không phải `request.input` — đó là literal prompt
    text) phải là nguồn context cho policy_evaluator — cùng bug đã fix ở
    ManualToolLoopKernel (packages/agent_core/kernel/openai_agents_kernel.py),
    xem COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §5.3."""
    registry = CapabilityRegistry()
    cap = CapabilitySpec(id="weather.get", description="Get weather", input_schema={"type": "object", "properties": {}})
    registry.register(cap, lambda args: {})

    captured_context: dict = {}

    def policy_evaluator(name: str, args: dict, ctx: dict) -> str:
        captured_context.update(ctx)
        return "ALLOW"

    call_id = "call_ctx_check"
    model = FakeSDKModel(
        responses=[
            _tool_call_response(call_id, "weather.get"),
            _text_response("done"),
        ]
    )
    kernel = RealOpenAIAgentsSDKKernel(
        model=model,
        capability_registry=registry,
        capability_executor=lambda name, args: {},
        policy_evaluator=policy_evaluator,
    )
    spec = _make_spec(capability_refs=["weather.get"])
    request = RunRequest(
        input={"prompt": "what is the weather"},
        principal="test-suite",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        workspace_id="ws_test",
        metadata={"policy_snapshot": {"company_status": "active", "principal_status": "active"}},
    )

    await kernel.run(request, spec)

    assert "policy_snapshot" in captured_context
    assert "prompt" not in captured_context
