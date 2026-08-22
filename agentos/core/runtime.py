from __future__ import annotations

from typing import Callable, Optional

from agentos.core.approval import ApprovalService
from agentos.core.context import AgentContext
from agentos.core.context_builder import ContextBuilder
from agentos.core.events import (
    EVENT_AGENT_RUN_COMPLETED,
    EVENT_AGENT_RUN_FAILED,
    EVENT_AGENT_RUN_STARTED,
    InMemoryEventBus,
)
from agentos.core.executor import (
    Executor,
    ExecutorExhaustedError,
    ToolApprovalRequiredError,
    ToolPermissionDeniedError,
)
from agentos.core.model_provider import ModelProvider
from agentos.core.models import AgentResult, AgentRun, AgentRunStatus, TaskContext
from agentos.core.planner import Planner
from agentos.core.policy import PolicyEngine
from agentos.core.trace import TraceRecorder
from agentos.core.trace_sink import SqliteTraceSink
from agentos.memory.retriever import MemoryRetriever
from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.router import SkillRouter
from agentos.tools.registry import ToolRegistry


class AgentRuntime:
    """MVP single-agent loop implementing the `Agent` protocol (core/agent.py):
    build context, run the executor's tool-calling loop, record trace,
    manage AgentRun status transitions. Multi-agent delegation/parallel
    flows (blueprint §3.2) are out of scope for Phase 1.
    """

    def __init__(
        self,
        model_provider: ModelProvider,
        tool_registry: ToolRegistry,
        policy_engine: PolicyEngine | None = None,
        approval_service: ApprovalService | None = None,
        trace_sink: SqliteTraceSink | None = None,
        memory_retriever: MemoryRetriever | None = None,
        skill_router: SkillRouter | None = None,
        skill_instruction_loader: SkillInstructionLoader | None = None,
    ) -> None:
        self._model_provider = model_provider
        self._tool_registry = tool_registry
        self._context_builder = ContextBuilder(
            tool_registry,
            memory_retriever=memory_retriever,
            skill_router=skill_router,
            skill_instruction_loader=skill_instruction_loader,
        )
        self._policy_engine = policy_engine or PolicyEngine()
        self._approval_service = approval_service or ApprovalService()
        self._trace_sink = trace_sink
        self.last_run: AgentRun | None = None
        self.last_trace: TraceRecorder | None = None
        self.last_context: AgentContext | None = None

    async def run(
        self,
        task: TaskContext,
        on_tool_event: Optional[Callable[[str, dict], None]] = None,
    ) -> AgentResult:
        run = AgentRun(agent_key=task.agent_key, goal=task.goal)
        self.last_run = run
        event_bus = InMemoryEventBus()
        if self._trace_sink is not None:
            self._trace_sink.attach(event_bus)
        trace = TraceRecorder(
            run_id=run.id,
            event_bus=event_bus,
            correlation_id=task.correlation_id or task.metadata.get("correlation_id"),
            workspace_id=task.workspace_id or task.metadata.get("workspace_id"),
            company_id=task.company_id or task.metadata.get("company_id"),
        )
        self.last_trace = trace

        run.transition(AgentRunStatus.RUNNING)
        trace.record(EVENT_AGENT_RUN_STARTED)

        context = await self._context_builder.build(task)
        self.last_context = context
        executor = Executor(
            self._model_provider,
            self._tool_registry,
            Planner(),
            trace,
            policy_engine=self._policy_engine,
            approval_service=self._approval_service,
            requester=task.agent_key,
            on_tool_event=on_tool_event,
        )

        try:
            output, tool_calls_made = await executor.run(context)
        except ToolApprovalRequiredError as exc:
            run.transition(AgentRunStatus.WAITING_APPROVAL)
            trace.record(EVENT_AGENT_RUN_FAILED, error=str(exc), approval_id=exc.approval_id)
            return AgentResult(run_id=run.id, status=run.status, error=str(exc), approval_id=exc.approval_id)
        except ToolPermissionDeniedError as exc:
            run.transition(AgentRunStatus.FAILED)
            run.error = str(exc)
            trace.record(EVENT_AGENT_RUN_FAILED, error=str(exc))
            return AgentResult(run_id=run.id, status=run.status, error=str(exc))
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
