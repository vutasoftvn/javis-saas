import pytest

from agentos.core.approval import ApprovalService, ApprovalStatus
from agentos.core.context import AgentContext
from agentos.core.events import InMemoryEventBus
from agentos.core.executor import (
    Executor,
    ExecutorExhaustedError,
    ToolApprovalRequiredError,
    ToolPermissionDeniedError,
)
from agentos.core.model_provider import ModelResponse, StubModelProvider, TokenUsage, ToolCallRequest
from agentos.core.models import TaskContext
from agentos.core.planner import Planner
from agentos.core.policy import PermissionClass, PolicyDecision, PolicyEngine
from agentos.core.trace import TraceRecorder
from agentos.tools.registry import ToolRegistry, ToolSpec


async def _echo(arguments: dict) -> dict:
    return {"echoed": arguments.get("text")}


def _make_context() -> AgentContext:
    task = TaskContext(goal="echo hi", agent_key="fake", workspace_id="ws1")
    return AgentContext(task=task, system_policy="p", tool_names=["echo"])


@pytest.mark.asyncio
async def test_executor_calls_tool_then_finishes():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_echo))
    provider = StubModelProvider(
        [
            ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"})),
            ModelResponse(text="echoed hi back"),
        ]
    )
    trace = TraceRecorder(run_id="r1", event_bus=InMemoryEventBus())
    executor = Executor(provider, registry, Planner(), trace)

    output, tool_calls_made = await executor.run(_make_context())

    assert output == "echoed hi back"
    assert tool_calls_made == 1
    assert [s["name"] for s in trace.export()] == [
        "model_generation.completed",
        "tool_call.started",
        "tool_call.completed",
        "model_generation.completed",
    ]


@pytest.mark.asyncio
async def test_executor_finishes_immediately_without_tool_call():
    registry = ToolRegistry()
    provider = StubModelProvider([ModelResponse(text="hello")])
    trace = TraceRecorder(run_id="r1", event_bus=InMemoryEventBus())
    executor = Executor(provider, registry, Planner(), trace)

    output, tool_calls_made = await executor.run(_make_context())

    assert output == "hello"
    assert tool_calls_made == 0


@pytest.mark.asyncio
async def test_executor_raises_when_max_rounds_exceeded():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_echo))
    responses = [
        ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"}))
        for _ in range(5)
    ]
    provider = StubModelProvider(responses)
    trace = TraceRecorder(run_id="r1", event_bus=InMemoryEventBus())
    executor = Executor(provider, registry, Planner(), trace)

    with pytest.raises(ExecutorExhaustedError):
        await executor.run(_make_context())


@pytest.mark.asyncio
async def test_executor_raises_on_denied_permission_without_invoking_tool():
    invoked = False

    async def _guarded(arguments: dict) -> dict:
        nonlocal invoked
        invoked = True
        return {}

    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="guarded", description="d", handler=_guarded, permission_class="ACCESS_SECRET")
    )
    provider = StubModelProvider(
        [ModelResponse(tool_call=ToolCallRequest(tool_name="guarded", arguments={}))]
    )
    trace = TraceRecorder(run_id="r1", event_bus=InMemoryEventBus())
    executor = Executor(provider, registry, Planner(), trace)

    with pytest.raises(ToolPermissionDeniedError):
        await executor.run(_make_context())

    assert invoked is False
    assert "tool_call.denied" in [s["name"] for s in trace.export()]


@pytest.mark.asyncio
async def test_executor_pauses_for_approval_without_invoking_tool():
    invoked = False

    async def _guarded(arguments: dict) -> dict:
        nonlocal invoked
        invoked = True
        return {}

    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="guarded", description="d", handler=_guarded, permission_class="FINANCIAL_ACTION")
    )
    provider = StubModelProvider(
        [ModelResponse(tool_call=ToolCallRequest(tool_name="guarded", arguments={"amount": 100}))]
    )
    trace = TraceRecorder(run_id="r1", event_bus=InMemoryEventBus())
    approval_service = ApprovalService()
    executor = Executor(provider, registry, Planner(), trace, approval_service=approval_service)

    with pytest.raises(ToolApprovalRequiredError) as exc_info:
        await executor.run(_make_context())

    assert invoked is False
    approval = approval_service.get(exc_info.value.approval_id)
    assert approval.status == ApprovalStatus.PENDING
    assert "tool_call.waiting_approval" in [s["name"] for s in trace.export()]


@pytest.mark.asyncio
async def test_executor_records_real_token_usage_on_the_model_generation_span():
    registry = ToolRegistry()
    provider = StubModelProvider(
        [ModelResponse(text="hello", model="test-model", usage=TokenUsage(input_tokens=10, output_tokens=3))]
    )
    trace = TraceRecorder(run_id="r1", event_bus=InMemoryEventBus())
    executor = Executor(provider, registry, Planner(), trace)

    await executor.run(_make_context())

    [span] = [s for s in trace.export() if s["name"] == "model_generation.completed"]
    assert span["model"] == "test-model"
    assert span["input_tokens"] == 10
    assert span["output_tokens"] == 3


@pytest.mark.asyncio
async def test_executor_threads_run_id_into_policy_and_approval_audit_trail():
    class _RecordingAuditSink:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def record(self, **kwargs) -> None:
            self.calls.append(kwargs)

    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="guarded", description="d", handler=_echo, permission_class="FINANCIAL_ACTION")
    )
    provider = StubModelProvider(
        [ModelResponse(tool_call=ToolCallRequest(tool_name="guarded", arguments={"amount": 100}))]
    )
    trace = TraceRecorder(run_id="run-audit-1", event_bus=InMemoryEventBus())
    sink = _RecordingAuditSink()
    policy_engine = PolicyEngine(audit_sink=sink)
    approval_service = ApprovalService(audit_sink=sink)
    executor = Executor(
        provider, registry, Planner(), trace, policy_engine=policy_engine, approval_service=approval_service
    )

    with pytest.raises(ToolApprovalRequiredError):
        await executor.run(_make_context())

    assert sink.calls[0] == {
        "event_type": "policy.evaluated",
        "run_id": "run-audit-1",
        "subject": "FINANCIAL_ACTION",
        "decision": "REQUIRE_APPROVAL",
    }
    assert sink.calls[1]["event_type"] == "approval.requested"
    assert sink.calls[1]["run_id"] == "run-audit-1"


@pytest.mark.asyncio
async def test_executor_allows_tool_when_policy_overridden():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="echo", description="d", handler=_echo, permission_class="SEND_MESSAGE")
    )
    provider = StubModelProvider(
        [
            ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"})),
            ModelResponse(text="done"),
        ]
    )
    trace = TraceRecorder(run_id="r1", event_bus=InMemoryEventBus())
    policy_engine = PolicyEngine({PermissionClass.SEND_MESSAGE: PolicyDecision.ALLOW})
    executor = Executor(provider, registry, Planner(), trace, policy_engine=policy_engine)

    output, tool_calls_made = await executor.run(_make_context())

    assert output == "done"
    assert tool_calls_made == 1
