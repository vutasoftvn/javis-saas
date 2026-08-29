"""Conformance test cho `PydanticAIKernel` — cùng 5-test shape với
`test_langchain_kernel.py`/`test_openai_agents_sdk_kernel.py`, dùng
`FunctionModel` của PydanticAI (fixture chính thức của framework cho test,
không cần API key thật)."""
from __future__ import annotations

import pytest

pytest.importorskip("pydantic_ai")

from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart

from agent.contracts.capability import CapabilitySpec
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.capabilities.registry import CapabilityRegistry
from agent.governance.contracts import ExecutionMode
from agent_integrations.pydantic_ai.kernel import PydanticAIKernel


def _make_spec(capability_refs: list[str] | None = None) -> AgentSpec:
    spec = AgentSpec(
        id="test_agent_pydantic_ai",
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
async def test_pydantic_ai_kernel_basic_response():
    call_count = {"n": 0}

    async def model_fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        return ModelResponse(parts=[TextPart(content="Hello from PydanticAI")])

    kernel = PydanticAIKernel(model=FunctionModel(model_fn))
    spec = _make_spec()

    result = await kernel.run(_make_request("hi", spec=spec), spec)

    assert result.status == RunStatus.COMPLETED
    assert "Hello from PydanticAI" in str(result.final_output)
    assert call_count["n"] == 1


@pytest.mark.asyncio
async def test_pydantic_ai_kernel_model_provider_failure_is_typed_failed_not_completed():
    async def model_fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise RuntimeError("simulated provider outage")

    kernel = PydanticAIKernel(model=FunctionModel(model_fn))
    spec = _make_spec()

    result = await kernel.run(_make_request("hi", spec=spec), spec)

    assert result.status == RunStatus.FAILED
    assert result.errors
    assert "simulated" in result.errors[0] or "outage" in result.errors[0]


@pytest.mark.asyncio
async def test_pydantic_ai_kernel_tool_call_allow_path_preserves_exact_identity():
    registry = CapabilityRegistry()
    cap = CapabilitySpec(id="weather.get", description="Get weather", input_schema={"type": "object", "properties": {}})
    registry.register(cap, lambda args: {})

    captured: dict[str, str] = {}

    async def capability_executor(tool_name: str, args: dict) -> dict:
        captured["tool_name"] = tool_name
        return {"temp_c": 21}

    step = {"n": 0}

    async def model_fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        step["n"] += 1
        if step["n"] == 1:
            return ModelResponse(parts=[ToolCallPart(tool_name="weather.get", args={}, tool_call_id="call_exact_1")])
        return ModelResponse(parts=[TextPart(content="It is 21C")])

    kernel = PydanticAIKernel(
        model=FunctionModel(model_fn),
        capability_registry=registry,
        capability_executor=capability_executor,
        policy_evaluator=lambda name, args, ctx=None: "ALLOW",
    )
    spec = _make_spec(capability_refs=["weather.get"])

    result = await kernel.run(_make_request("what is the weather", spec=spec), spec)

    assert result.status == RunStatus.COMPLETED
    assert captured["tool_name"] == "weather.get"


@pytest.mark.asyncio
async def test_pydantic_ai_kernel_approval_pause_and_resume():
    registry = CapabilityRegistry()
    cap = CapabilitySpec(id="finance.payout.execute", description="Payout", input_schema={"type": "object", "properties": {}})
    registry.register(cap, lambda args: {})

    executed: list[str] = []

    async def capability_executor(tool_name: str, args: dict) -> dict:
        executed.append(tool_name)
        return {"status": "paid"}

    step = {"n": 0}

    async def model_fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        step["n"] += 1
        if step["n"] == 1:
            return ModelResponse(
                parts=[ToolCallPart(tool_name="finance.payout.execute", args={"amount": 1000}, tool_call_id="call_payout_1")]
            )
        return ModelResponse(parts=[TextPart(content="Payout complete")])

    kernel = PydanticAIKernel(
        model=FunctionModel(model_fn),
        capability_registry=registry,
        capability_executor=capability_executor,
        policy_evaluator=lambda name, args, ctx=None: "REQUIRE_APPROVAL",
    )
    spec = _make_spec(capability_refs=["finance.payout.execute"])

    result = await kernel.run(_make_request("pay the vendor", spec=spec), spec)

    assert result.status == RunStatus.WAITING_APPROVAL
    assert executed == []
    assert result.interruptions_waits
    checkpoint_ref = result.interruptions_waits[0].checkpoint_ref

    resumed = await kernel.resume(
        result.run_id, checkpoint_ref, {"approved": True, "approved_tool_calls": {"call_payout_1": True}}
    )

    assert resumed.status == RunStatus.COMPLETED
    assert executed == ["finance.payout.execute"]


@pytest.mark.asyncio
async def test_pydantic_ai_kernel_cancellation():
    call_count = {"n": 0}

    async def model_fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        return ModelResponse(parts=[TextPart(content="should not be reached")])

    kernel = PydanticAIKernel(model=FunctionModel(model_fn))
    spec = _make_spec()

    run_id = "run_cancel_test_pydantic_ai"
    request = _make_request("hi", spec=spec)
    request.run_id = run_id

    await kernel.cancel(run_id, reason="user requested stop")
    result = await kernel.run(request, spec)

    assert result.status == RunStatus.CANCELLED
    assert call_count["n"] == 0
