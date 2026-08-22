import pytest

from agentos.core.context import AgentContext
from agentos.core.events import InMemoryEventBus
from agentos.core.executor import Executor, ExecutorExhaustedError
from agentos.core.model_provider import ModelResponse, StubModelProvider, ToolCallRequest
from agentos.core.models import TaskContext
from agentos.core.planner import Planner
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
    assert [s["name"] for s in trace.export()] == ["tool_call.started", "tool_call.completed"]


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
