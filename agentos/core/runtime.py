from __future__ import annotations

from typing import Any, Callable, Optional

from agentos.core.adapters.contracts import AgentRuntimeAdapter
from agentos.core.adapters.tenant_policy_client import TenantPolicyClient
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
    """MVP and Multi-Agent loop implementing the `Agent` protocol (core/agent.py):
    build context, route to the appropriate runtime adapter (Native Executor,
    DeepSeek Harness, or ADK Multi-Agent Orchestrator), record trace, and manage
    AgentRun status transitions.
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
        knowledge_retriever: Any | None = None,
        runtime_adapter: AgentRuntimeAdapter | None = None,
        tenant_policy_client: TenantPolicyClient | None = None,
    ) -> None:
        self._model_provider = model_provider
        self._tool_registry = tool_registry
        self._knowledge_retriever = knowledge_retriever
        self._context_builder = ContextBuilder(
            tool_registry,
            memory_retriever=memory_retriever,
            skill_router=skill_router,
            skill_instruction_loader=skill_instruction_loader,
            knowledge_retriever=knowledge_retriever,
        )
        self._policy_engine = policy_engine or PolicyEngine()
        self._approval_service = approval_service or ApprovalService()
        self._trace_sink = trace_sink
        self._runtime_adapter = runtime_adapter
        self._tenant_policy_client = tenant_policy_client
        self.last_run: AgentRun | None = None
        self.last_trace: TraceRecorder | None = None
        self.last_context: AgentContext | None = None

    def _resolve_adapter(self, task: TaskContext, trace: TraceRecorder, on_tool_event: Optional[Callable[[str, dict], None]] = None) -> AgentRuntimeAdapter:
        if self._runtime_adapter is not None:
            return self._runtime_adapter

        meta = task.metadata or {}
        orchestration_mode = meta.get("orchestration_mode")
        is_multi_agent = orchestration_mode == "multi_agent" or bool(meta.get("is_mission")) or bool(meta.get("multi_agent"))
        preferred_runtime = meta.get("preferred_runtime")

        if is_multi_agent:
            from agentos.orchestration.adk.orchestrator import AdkOrchestrator

            return AdkOrchestrator(
                model_provider=self._model_provider,
                tool_registry=self._tool_registry,
                policy_engine=self._policy_engine,
                approval_service=self._approval_service,
                context_builder=self._context_builder,
            )

        if preferred_runtime == "deepseek_harness":
            from agentos.core.adapters.deepseek_harness_adapter import DeepSeekHarnessRuntimeAdapter

            return DeepSeekHarnessRuntimeAdapter(
                tool_registry=self._tool_registry,
                model_provider=self._model_provider,
                policy_engine=self._policy_engine,
                approval_service=self._approval_service,
            )

        # Default: Native Executor
        return Executor(
            self._model_provider,
            self._tool_registry,
            Planner(),
            trace,
            policy_engine=self._policy_engine,
            approval_service=self._approval_service,
            tenant_policy_client=self._tenant_policy_client,
            requester=task.agent_key,
            on_tool_event=on_tool_event,
        )

    async def run(
        self,
        task: TaskContext,
        on_tool_event: Optional[Callable[[str, dict], None]] = None,
    ) -> AgentResult:
        requested_run_id = task.metadata.get("run_id") if task.metadata else None
        run = (
            AgentRun(id=requested_run_id, agent_key=task.agent_key, goal=task.goal)
            if requested_run_id
            else AgentRun(agent_key=task.agent_key, goal=task.goal)
        )
        self.last_run = run
        event_bus = InMemoryEventBus()
        if self._trace_sink is not None:
            self._trace_sink.attach(event_bus)
        trace = TraceRecorder(
            run_id=run.id,
            event_bus=event_bus,
            correlation_id=task.correlation_id or (task.metadata.get("correlation_id") if task.metadata else None),
            workspace_id=task.workspace_id or (task.metadata.get("workspace_id") if task.metadata else None),
            company_id=task.company_id or (task.metadata.get("company_id") if task.metadata else None),
        )
        self.last_trace = trace

        run.transition(AgentRunStatus.RUNNING)
        trace.record(EVENT_AGENT_RUN_STARTED)

        context = await self._context_builder.build(task)
        self.last_context = context

        adapter = self._resolve_adapter(task, trace, on_tool_event)

        try:
            output, tool_calls_made = await adapter.run(context)
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
