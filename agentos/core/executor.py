from __future__ import annotations

from agentos.core.approval import ApprovalService
from agentos.core.context import AgentContext
from agentos.core.events import (
    EVENT_MODEL_GENERATION_COMPLETED,
    EVENT_TOOL_CALL_COMPLETED,
    EVENT_TOOL_CALL_DENIED,
    EVENT_TOOL_CALL_STARTED,
    EVENT_TOOL_CALL_WAITING_APPROVAL,
)
from agentos.core.model_provider import ModelProvider
from agentos.core.planner import PlanAction, Planner
from agentos.core.policy import PermissionClass, PolicyDecision, PolicyEngine
from agentos.core.trace import TraceRecorder
from agentos.tools.registry import ToolRegistry

MAX_TOOL_ROUNDS = 5


class ExecutorExhaustedError(Exception):
    def __init__(self, max_rounds: int) -> None:
        super().__init__(f"Executor exceeded MAX_TOOL_ROUNDS={max_rounds} without finishing")


class ToolPermissionDeniedError(Exception):
    """Raised when a tool call is blocked outright by the PolicyEngine
    (CLAUDE.md §11 — permission decisions are deterministic code, never an
    LLM judgment call). Distinct from ExecutorExhaustedError so callers can
    tell "policy refused" apart from "ran out of rounds".
    """

    def __init__(self, tool_name: str, permission: PermissionClass) -> None:
        super().__init__(f"Tool '{tool_name}' denied by policy for permission {permission.value}")
        self.tool_name = tool_name
        self.permission = permission


class ToolApprovalRequiredError(Exception):
    """Raised when a tool call requires human approval before it can run.
    The executor stops here rather than proceeding or auto-approving —
    resuming the run after a decision is out of scope for this loop shape
    (blueprint §49/§50 — approval hardening happens at the workflow layer).
    """

    def __init__(self, tool_name: str, approval_id: str) -> None:
        super().__init__(f"Tool '{tool_name}' requires approval (approval_id={approval_id})")
        self.tool_name = tool_name
        self.approval_id = approval_id


class Executor:
    def __init__(
        self,
        model_provider: ModelProvider,
        tool_registry: ToolRegistry,
        planner: Planner,
        trace: TraceRecorder,
        policy_engine: PolicyEngine | None = None,
        approval_service: ApprovalService | None = None,
        requester: str = "agent",
    ) -> None:
        self._model_provider = model_provider
        self._tool_registry = tool_registry
        self._planner = planner
        self._trace = trace
        self._policy_engine = policy_engine or PolicyEngine()
        self._approval_service = approval_service or ApprovalService()
        self._requester = requester

    async def run(self, context: AgentContext) -> tuple[str, int]:
        messages: list[dict] = [{"role": "user", "content": context.task.goal}]
        tool_calls_made = 0

        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._model_provider.generate(
                system_prompt=context.system_policy, messages=messages
            )
            self._trace.record(
                EVENT_MODEL_GENERATION_COMPLETED,
                model=response.model,
                input_tokens=response.usage.input_tokens if response.usage else None,
                output_tokens=response.usage.output_tokens if response.usage else None,
            )
            action = self._planner.decide(response)

            if action is PlanAction.FINISH:
                return response.text or "", tool_calls_made

            assert response.tool_call is not None
            tool_name = response.tool_call.tool_name
            spec = self._tool_registry.get(tool_name)

            if spec.permission_class:
                permission = PermissionClass(spec.permission_class)
                decision = self._policy_engine.evaluate(permission, run_id=self._trace.run_id)

                if decision is PolicyDecision.DENY:
                    self._trace.record(
                        EVENT_TOOL_CALL_DENIED, tool_name=tool_name, permission=permission.value
                    )
                    raise ToolPermissionDeniedError(tool_name, permission)

                if decision is PolicyDecision.REQUIRE_APPROVAL:
                    approval = self._approval_service.request_approval(
                        action=tool_name,
                        subject=str(response.tool_call.arguments),
                        requester=self._requester,
                        run_id=self._trace.run_id,
                    )
                    self._trace.record(
                        EVENT_TOOL_CALL_WAITING_APPROVAL,
                        tool_name=tool_name,
                        approval_id=approval.id,
                    )
                    raise ToolApprovalRequiredError(tool_name, approval.id)

            self._trace.record(
                EVENT_TOOL_CALL_STARTED,
                tool_name=tool_name,
                arguments=response.tool_call.arguments,
            )
            result = await spec.handler(response.tool_call.arguments)
            self._trace.record(
                EVENT_TOOL_CALL_COMPLETED,
                tool_name=tool_name,
                result=result,
            )
            tool_calls_made += 1
            messages.append({"role": "assistant", "tool_call": response.tool_call.model_dump()})
            messages.append({"role": "tool", "content": result})

        raise ExecutorExhaustedError(MAX_TOOL_ROUNDS)
