"""Contract and smoke tests for RealOpenAIAgentsSDKKernel.

Asserts:
- Adapter initializes cleanly with minimal config and no side effects.
- kernel.run(RunRequest) -> RunResult with full standard event stream vocabulary.
- Tool call round-trip: model requests tool -> adapter calls handler -> result fed back to model.
- Provider errors are mapped to contract errors (RunStatus.FAILED) without leaking unhandled raw exceptions.
"""

from __future__ import annotations

import pytest

pytest.importorskip("agents")

from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import ExecutionMode
from agent.runs.repository import InMemoryRunRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
from agent_testkit.fake_sdk_model import (
    FakeSDKModel,
    text_response,
    tool_call_response,
)


def _build_spec(cap_refs: list[str] | None = None) -> AgentSpec:
    return AgentSpec(
        id="test_contract_agent",
        version="1.0.0",
        instructions="You are a test contract agent.",
        capability_refs=cap_refs or [],
    ).with_hash()


def _build_request(prompt: str = "contract test", spec: AgentSpec | None = None) -> RunRequest:
    s = spec or _build_spec()
    return RunRequest(
        input={"prompt": prompt},
        principal="test-contract-runner",
        root_executable_ref=s.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_contract",
    )


@pytest.mark.asyncio
async def test_openai_agents_sdk_adapter_initialization():
    """Adapter initializes with zero config / default repository, without side effects."""
    kernel = RealOpenAIAgentsSDKKernel()
    assert kernel._repo is not None
    assert kernel._spec_registry is not None
    assert kernel._cancelled_runs == set()


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_event_stream_vocabulary():
    """Execution produces standard event stream: run.started, run.completed."""
    repo = InMemoryRunRepository()
    model = FakeSDKModel(responses=[text_response("Contract output")])
    kernel = RealOpenAIAgentsSDKKernel(repository=repo, model=model)
    spec = _build_spec()
    request = _build_request("run vocabulary test", spec=spec)

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert result.final_output == "Contract output"

    events = await repo.list_events(result.run_id)
    event_types = [e.event_type for e in events]
    assert "run.started" in event_types
    assert "run.completed" in event_types


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_tool_roundtrip_contract():
    """Tool call round-trip: model asks for tool -> adapter executes handler -> returns result to model."""
    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="calculator.add",
        description="Add two numbers",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )
    registry.register(cap, lambda args: {})

    executed_args: list[dict] = []

    async def executor(tool_name: str, args: dict) -> dict:
        executed_args.append(args)
        return {"sum": args.get("a", 0) + args.get("b", 0)}

    call_id = "call_calc_42"
    model = FakeSDKModel(
        responses=[
            tool_call_response(call_id, "calculator.add", arguments='{"a": 20, "b": 22}'),
            text_response("The answer is 42"),
        ]
    )

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=executor,
        model=model,
        policy_evaluator=lambda name, args, ctx=None: "ALLOW",
    )
    spec = _build_spec(cap_refs=["calculator.add"])
    request = _build_request("Add 20 and 22", spec=spec)

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert "42" in str(result.final_output)
    assert len(executed_args) == 1
    assert executed_args[0] == {"a": 20, "b": 22}

    events = await repo.list_events(result.run_id)
    event_types = [e.event_type for e in events]
    assert "run.started" in event_types
    assert "tool.started" in event_types
    assert "tool.completed" in event_types
    assert "run.completed" in event_types


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_provider_error_mapped_to_contract():
    """Provider failure maps to RunStatus.FAILED without leaking unhandled raw exception."""
    repo = InMemoryRunRepository()
    model = FakeSDKModel(error=ConnectionResetError("Simulated LLM network drop"))
    kernel = RealOpenAIAgentsSDKKernel(repository=repo, model=model)
    spec = _build_spec()
    request = _build_request("trigger failure", spec=spec)

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.FAILED
    assert result.errors
    assert any("Simulated LLM network drop" in err for err in result.errors)

    events = await repo.list_events(result.run_id)
    event_types = [e.event_type for e in events]
    assert "run.started" in event_types
    assert "run.failed" in event_types


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_propagates_invocation_context():
    """Assert workspace_id, principal, correlation_id reach executor via InvocationContext."""
    from agent.contracts.invocation import InvocationContext
    from agent.capabilities.gateway import GatewayExecutionRequest

    repo = InMemoryRunRepository()
    registry = CapabilityRegistry()
    cap = CapabilitySpec(
        id="test.context.probe",
        description="Probe invocation context",
        input_schema={"type": "object"},
    )
    registry.register(cap, lambda args, ctx=None: {})

    captured_requests: list[GatewayExecutionRequest] = []

    # Mock gateway execution function that takes GatewayExecutionRequest
    async def gateway_executor(req: GatewayExecutionRequest):
        captured_requests.append(req)
        return {"probed": True}

    call_id = "call_probe_99"
    model = FakeSDKModel(
        responses=[
            tool_call_response(call_id, "test.context.probe", arguments='{"x": 1}'),
            text_response("Probe completed"),
        ]
    )

    kernel = RealOpenAIAgentsSDKKernel(
        repository=repo,
        capability_registry=registry,
        capability_executor=gateway_executor,
        model=model,
        policy_evaluator=lambda name, args, ctx=None: "ALLOW",
    )
    spec = _build_spec(cap_refs=["test.context.probe"])
    request = RunRequest(
        input={"prompt": "Probe test"},
        principal="founder_alice",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_tenant_42",
        correlation_id="corr_999",
        conversation_id="conv_888",
    )

    result = await kernel.run(request, spec)
    assert result.status == RunStatus.COMPLETED

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.workspace_id == "ws_tenant_42"
    assert req.principal == "founder_alice"
    assert isinstance(req.context, InvocationContext)
    assert req.context.workspace_id == "ws_tenant_42"
    assert req.context.principal == "founder_alice"
    assert req.context.correlation_id == "corr_999"
    assert req.context.conversation_id == "conv_888"


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_output_schema_validation_success():
    """Valid JSON output conforming to output_schema completes with parsed output."""
    repo = InMemoryRunRepository()
    model = FakeSDKModel(responses=[text_response('{"score": 95, "verdict": "pass"}')])
    kernel = RealOpenAIAgentsSDKKernel(repository=repo, model=model)
    spec = _build_spec()
    spec.output_schema = {
        "type": "object",
        "required": ["score", "verdict"],
        "properties": {"score": {"type": "integer"}, "verdict": {"type": "string"}},
    }
    request = _build_request("Evaluate code", spec=spec)
    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert isinstance(result.final_output, dict)
    assert result.final_output["score"] == 95


@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_output_schema_validation_failure():
    """Invalid JSON output failing output_schema fails with structured ValidationFailure."""
    repo = InMemoryRunRepository()
    model = FakeSDKModel(responses=[text_response('{"score": "not_a_number"}')])
    kernel = RealOpenAIAgentsSDKKernel(repository=repo, model=model)
    spec = _build_spec()
    spec.output_schema = {
        "type": "object",
        "required": ["score", "verdict"],
        "properties": {"score": {"type": "integer"}, "verdict": {"type": "string"}},
    }
    request = _build_request("Evaluate code", spec=spec)
    result = await kernel.run(request, spec)

    assert result.status == RunStatus.FAILED
    assert any("Output validation failed" in err for err in result.errors)
    assert result.final_output["is_valid"] is False


