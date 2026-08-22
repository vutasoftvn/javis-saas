from __future__ import annotations

from agentos.core.context_builder import ContextBuilder
from agentos.core.events import (
    EVENT_AGENT_RUN_COMPLETED,
    EVENT_AGENT_RUN_FAILED,
    EVENT_AGENT_RUN_STARTED,
    InMemoryEventBus,
)
from agentos.core.executor import Executor, ExecutorExhaustedError
from agentos.core.model_provider import ModelProvider
from agentos.core.models import AgentResult, AgentRun, AgentRunStatus, TaskContext
from agentos.core.planner import Planner
from agentos.core.trace import TraceRecorder
from agentos.tools.registry import ToolRegistry


class AgentRuntime:
    """MVP single-agent loop implementing the `Agent` protocol (core/agent.py):
    build context, run the executor's tool-calling loop, record trace,
    manage AgentRun status transitions. Multi-agent delegation/parallel
    flows (blueprint §3.2) are out of scope for Phase 1.
    """

    def __init__(self, model_provider: ModelProvider, tool_registry: ToolRegistry) -> None:
        self._model_provider = model_provider
        self._tool_registry = tool_registry
        self._context_builder = ContextBuilder(tool_registry)
        self.last_run: AgentRun | None = None

    async def run(self, task: TaskContext) -> AgentResult:
        run = AgentRun(agent_key=task.agent_key, goal=task.goal)
        self.last_run = run
        event_bus = InMemoryEventBus()
        trace = TraceRecorder(run_id=run.id, event_bus=event_bus)

        run.transition(AgentRunStatus.RUNNING)
        trace.record(EVENT_AGENT_RUN_STARTED)

        context = await self._context_builder.build(task)
        executor = Executor(self._model_provider, self._tool_registry, Planner(), trace)

        try:
            output, tool_calls_made = await executor.run(context)
        except ExecutorExhaustedError as exc:
            run.transition(AgentRunStatus.FAILED)
            run.error = str(exc)
            trace.record(EVENT_AGENT_RUN_FAILED, error=str(exc))
            return AgentResult(run_id=run.id, status=run.status, error=str(exc))

        run.transition(AgentRunStatus.COMPLETED)
        run.result = {"output": output, "tool_calls_made": tool_calls_made}
        trace.record(EVENT_AGENT_RUN_COMPLETED, output=output)

        return AgentResult(
            run_id=run.id,
            status=run.status,
            output=output,
            tool_calls_made=tool_calls_made,
        )
