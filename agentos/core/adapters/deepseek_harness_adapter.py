from __future__ import annotations

from typing import Optional

from agentos.core.adapters.contracts import AgentRuntimeAdapter
from agentos.core.adapters.deepseek_harness_provider import DeepSeekHarnessModelProvider
from agentos.core.approval import ApprovalService
from agentos.core.context import AgentContext
from agentos.core.executor import Executor
from agentos.core.model_provider import ModelProvider
from agentos.core.planner import Planner
from agentos.core.policy import PolicyEngine
from agentos.core.trace import TraceRecorder
from agentos.tools.registry import ToolRegistry


class DeepSeekHarnessRuntimeAdapter:
    """`AgentRuntimeAdapter` (contracts.py) driving execution backed by DeepSeek Harness SDK.
    
    Provides unified governed execution while delegating model reasoning to DeepSeek Harness.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        *,
        model_provider: Optional[ModelProvider] = None,
        policy_engine: Optional[PolicyEngine] = None,
        approval_service: Optional[ApprovalService] = None,
        api_key: Optional[str] = None,
        model_name: str = "deepseek-v4-flash",
    ) -> None:
        self._tool_registry = tool_registry
        self._policy_engine = policy_engine or PolicyEngine()
        self._approval_service = approval_service or ApprovalService()
        self._model_provider = model_provider or DeepSeekHarnessModelProvider(
            api_key=api_key, model_name=model_name
        )

    async def run(self, context: AgentContext) -> tuple[str, int]:
        trace = TraceRecorder(
            run_id=context.task.metadata.get("run_id", "dsh_run"),
            correlation_id=context.correlation_id,
            workspace_id=context.task.workspace_id,
            company_id=context.task.company_id,
        )
        executor = Executor(
            model_provider=self._model_provider,
            tool_registry=self._tool_registry,
            planner=Planner(),
            trace=trace,
            policy_engine=self._policy_engine,
            approval_service=self._approval_service,
            requester=context.task.agent_key,
        )
        return await executor.run(context)
