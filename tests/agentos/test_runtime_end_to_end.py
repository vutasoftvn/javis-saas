import pytest

from agentos.core.agent import Agent
from agentos.core.model_provider import ModelResponse, StubModelProvider, ToolCallRequest
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.runtime import AgentRuntime
from agentos.tools.registry import ToolRegistry, ToolSpec


async def _echo(arguments: dict) -> dict:
    return {"echoed": arguments.get("text")}


def test_agent_runtime_satisfies_agent_protocol():
    runtime = AgentRuntime(StubModelProvider([]), ToolRegistry())
    assert isinstance(runtime, Agent)


@pytest.mark.asyncio
async def test_single_agent_loop_end_to_end_completes():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="echoes text", handler=_echo))
    provider = StubModelProvider(
        [
            ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"})),
            ModelResponse(text="Echoed: hi"),
        ]
    )
    runtime = AgentRuntime(provider, registry)
    task = TaskContext(goal="echo hi", agent_key="echo_agent", workspace_id="ws1")

    result = await runtime.run(task)

    assert result.status == AgentRunStatus.COMPLETED
    assert result.output == "Echoed: hi"
    assert result.tool_calls_made == 1
    assert runtime.last_run is not None
    assert runtime.last_run.is_terminal() is True
    assert runtime.last_trace is not None
    assert len(runtime.last_trace.export()) > 0


@pytest.mark.asyncio
async def test_single_agent_loop_end_to_end_no_tool_needed():
    registry = ToolRegistry()
    provider = StubModelProvider([ModelResponse(text="Hello there")])
    runtime = AgentRuntime(provider, registry)
    task = TaskContext(goal="say hi", agent_key="chat_agent", workspace_id="ws1")

    result = await runtime.run(task)

    assert result.status == AgentRunStatus.COMPLETED
    assert result.output == "Hello there"
    assert result.tool_calls_made == 0


@pytest.mark.asyncio
async def test_agent_runtime_wires_memory_and_skill_context():
    """Addendum gap (COSA_ARCHITECTURE_REVIEW_2026-08-22.md §1.1): ContextBuilder
    accepts memory_retriever/skill_router/skill_instruction_loader, but AgentRuntime
    used to hardcode ContextBuilder(tool_registry) and drop them silently."""

    class StubSkillMetadata:
        id = "demo-skill"

    class StubSkillManifest:
        metadata = StubSkillMetadata()

    class StubMemoryRetriever:
        async def retrieve(self, task):
            return ["remembered fact"]

    class StubSkillRouter:
        def select(self, goal):
            return StubSkillManifest()

    class StubSkillInstructionLoader:
        def load(self, skill_id):
            return f"instructions for {skill_id}"

    registry = ToolRegistry()
    provider = StubModelProvider([ModelResponse(text="ok")])
    runtime = AgentRuntime(
        provider,
        registry,
        memory_retriever=StubMemoryRetriever(),
        skill_router=StubSkillRouter(),
        skill_instruction_loader=StubSkillInstructionLoader(),
    )
    task = TaskContext(goal="do something", agent_key="agent1", workspace_id="ws1")

    await runtime.run(task)

    assert runtime.last_context is not None
    assert runtime.last_context.memory_snippets == ["remembered fact"]
    assert runtime.last_context.skill_instructions == ["instructions for demo-skill"]


@pytest.mark.asyncio
async def test_single_agent_loop_end_to_end_reports_failure_on_exhaustion():
    registry = ToolRegistry()
    registry.register(ToolSpec(name="echo", description="d", handler=_echo))
    responses = [
        ModelResponse(tool_call=ToolCallRequest(tool_name="echo", arguments={"text": "hi"}))
        for _ in range(5)
    ]
    provider = StubModelProvider(responses)
    runtime = AgentRuntime(provider, registry)
    task = TaskContext(goal="loop forever", agent_key="echo_agent", workspace_id="ws1")

    result = await runtime.run(task)

    assert result.status == AgentRunStatus.FAILED
    assert result.error is not None
    assert runtime.last_run.status == AgentRunStatus.FAILED
