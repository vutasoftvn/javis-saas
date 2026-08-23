from __future__ import annotations

from typing import Any, Callable, Optional
from agentos.core.adapters.tenant_policy_client import TenantPolicyClient
from agentos.core.approval import ApprovalService, ApprovalStatus
from agentos.core.audit_sink import AuditSink
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
from agentos.core.policy import (
    DataScope,
    ExecutionMode,
    PermissionClass,
    PermissionLevel,
    PolicyDecision,
    PolicyEngine,
)
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
        audit_sink: AuditSink | None = None,
        requester: str = "agent",
        on_tool_event: Optional[Callable[[str, dict], None]] = None,
        tenant_policy_client: Optional[TenantPolicyClient] = None,
    ) -> None:
        self._model_provider = model_provider
        self._tool_registry = tool_registry
        self._planner = planner
        self._trace = trace
        self._policy_engine = policy_engine or PolicyEngine()
        self._approval_service = approval_service or ApprovalService()
        self._audit_sink = audit_sink or getattr(self._policy_engine, "_audit_sink", None)
        self._requester = requester
        self._tenant_policy_client = tenant_policy_client
        # Optional live-streaming hook (Chat API §17.1.2): fired at each tool-call
        # lifecycle point so a caller (e.g. agentos/api/chat) can surface
        # tool.requested/started/completed/failed as SSE events without the
        # Executor needing to know anything about HTTP/SSE. Never required —
        # audit_sink (durable governance record) keeps working with or without it.
        self._on_tool_event = on_tool_event

    def _emit_tool_event(self, event_type: str, payload: dict) -> None:
        if self._on_tool_event is None:
            return
        self._on_tool_event(event_type, payload)

    async def run(self, context: AgentContext) -> tuple[str, int]:
        messages: list[dict] = []
        if context.conversation_messages:
            messages.extend(context.conversation_messages)
        if not messages or messages[-1].get("content") != context.task.goal or messages[-1].get("role") != "user":
            messages.append({"role": "user", "content": context.task.goal})
        tool_calls_made = 0

        # Extract principal and correlation context
        correlation_id = (
            context.correlation_id
            or getattr(context.task, "correlation_id", None)
            or context.task.metadata.get("correlation_id")
        )
        workspace_id = (
            context.workspace_id
            or getattr(context.task, "workspace_id", None)
            or context.task.metadata.get("workspace_id")
        )
        company_id = (
            context.company_id
            or getattr(context.task, "company_id", None)
            or context.task.metadata.get("company_id")
        )
        user_id = (
            context.user_id
            or getattr(context.task, "user_id", None)
            or context.task.metadata.get("user_id")
        )
        workforce_member_id = (
            context.workforce_member_id
            or getattr(context.task, "workforce_member_id", None)
            or context.task.metadata.get("workforce_member_id")
        )
        principal = (
            f"user:{user_id}"
            if user_id
            else (f"member:{workforce_member_id}" if workforce_member_id else self._requester)
        )

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

            role = context.role or getattr(context.task, "role", "founder")
            level = context.agent_permission_level or getattr(
                context.task, "agent_permission_level", PermissionLevel.L3_EXECUTE
            )
            permission_enum = (
                PermissionClass(spec.permission_class) if spec.permission_class else None
            )
            approval_policy = getattr(spec, "approval_policy", "conditional")

            meta = getattr(context.task, "metadata", {}) or {}
            tenant_policy = getattr(context, "tenant_policy", None) or meta.get("tenant_policy")
            if tenant_policy is None and self._tenant_policy_client is not None and company_id:
                tenant_policy = await self._tenant_policy_client.get_decision(
                    company_id=str(company_id), tool_name=tool_name
                )
            execution_mode = getattr(context, "execution_mode", None) or meta.get("execution_mode") or ExecutionMode.INTERACTIVE
            data_scope = getattr(context, "data_scope", None) or meta.get("data_scope") or DataScope.WORKSPACE

            self._emit_tool_event(
                "tool.requested",
                {"tool_name": tool_name, "arguments": response.tool_call.arguments},
            )

            decision = self._policy_engine.evaluate_access(
                role=role,
                agent_permission_level=level,
                tool_risk_level=spec.risk_level,
                tool_permission=spec.tool_permission,
                tenant_policy=tenant_policy,
                execution_mode=execution_mode,
                data_scope=data_scope,
                permission_class=permission_enum,
                approval_policy=approval_policy,
                run_id=self._trace.run_id,
                correlation_id=correlation_id,
                workspace_id=str(workspace_id) if workspace_id else None,
                company_id=str(company_id) if company_id else None,
            )

            if decision is PolicyDecision.DENY:
                self._trace.record(
                    EVENT_TOOL_CALL_DENIED,
                    tool_name=tool_name,
                    permission=spec.permission_class or "DENY",
                )
                if self._audit_sink is not None:
                    self._audit_sink.record(
                        event_type="tool.denied",
                        run_id=self._trace.run_id,
                        correlation_id=correlation_id,
                        workspace_id=str(workspace_id) if workspace_id else None,
                        company_id=str(company_id) if company_id else None,
                        tool_name=tool_name,
                        principal=principal,
                        decision="DENY",
                        input_payload=response.tool_call.arguments,
                        outcome={"status": "denied", "reason": "policy_refused"},
                    )
                self._emit_tool_event(
                    "tool.failed",
                    {"tool_name": tool_name, "reason": "policy_denied"},
                )
                raise ToolPermissionDeniedError(
                    tool_name, permission_enum or PermissionClass.ACCESS_SECRET
                )

            if decision is PolicyDecision.REQUIRE_APPROVAL:
                existing_approval = self._approval_service.find_by_run_and_action(
                    self._trace.run_id, tool_name
                )
                if existing_approval is not None:
                    if existing_approval.status == ApprovalStatus.APPROVED:
                        # Human approval granted - proceed to invoke tool
                        pass
                    elif existing_approval.status == ApprovalStatus.DENIED:
                        self._trace.record(
                            EVENT_TOOL_CALL_DENIED,
                            tool_name=tool_name,
                            permission=spec.permission_class or "DENY",
                        )
                        self._emit_tool_event(
                            "tool.failed",
                            {"tool_name": tool_name, "reason": "approval_denied"},
                        )
                        raise ToolPermissionDeniedError(
                            tool_name, permission_enum or PermissionClass.ACCESS_SECRET
                        )
                    else:
                        raise ToolApprovalRequiredError(tool_name, existing_approval.id)
                else:
                    approval = self._approval_service.request_approval(
                        action=tool_name,
                        subject=str(response.tool_call.arguments),
                        requester=self._requester,
                        run_id=self._trace.run_id,
                        tool_name=tool_name,
                        checkpoint_index=tool_calls_made,
                        correlation_id=correlation_id,
                    )
                    self._trace.record(
                        EVENT_TOOL_CALL_WAITING_APPROVAL,
                        tool_name=tool_name,
                        approval_id=approval.id,
                    )
                    if self._audit_sink is not None:
                        self._audit_sink.record(
                            event_type="tool.waiting_approval",
                            run_id=self._trace.run_id,
                            correlation_id=correlation_id,
                            workspace_id=str(workspace_id) if workspace_id else None,
                            company_id=str(company_id) if company_id else None,
                            tool_name=tool_name,
                            principal=principal,
                            decision="REQUIRE_APPROVAL",
                            input_payload=response.tool_call.arguments,
                            outcome={"status": "waiting_approval", "approval_id": approval.id},
                        )
                    raise ToolApprovalRequiredError(tool_name, approval.id)


            self._trace.record(
                EVENT_TOOL_CALL_STARTED,
                tool_name=tool_name,
                arguments=response.tool_call.arguments,
            )
            self._emit_tool_event(
                "tool.started",
                {"tool_name": tool_name, "arguments": response.tool_call.arguments},
            )

            try:
                result = await self._tool_registry.invoke(tool_name, response.tool_call.arguments)
            except Exception as exc:
                self._emit_tool_event(
                    "tool.failed",
                    {"tool_name": tool_name, "error": str(exc)},
                )
                if self._audit_sink is not None:
                    self._audit_sink.record(
                        event_type="tool.failed",
                        run_id=self._trace.run_id,
                        correlation_id=correlation_id,
                        workspace_id=str(workspace_id) if workspace_id else None,
                        company_id=str(company_id) if company_id else None,
                        tool_name=tool_name,
                        principal=principal,
                        decision="ALLOW",
                        input_payload=response.tool_call.arguments,
                        outcome={"status": "error", "error": str(exc)},
                    )
                raise

            self._trace.record(
                EVENT_TOOL_CALL_COMPLETED,
                tool_name=tool_name,
                result=result,
            )
            self._emit_tool_event(
                "tool.completed",
                {"tool_name": tool_name, "result": result},
            )

            if self._audit_sink is not None:
                audit_policy = getattr(spec, "audit_policy", "full")
                self._audit_sink.record(
                    event_type="tool.executed",
                    run_id=self._trace.run_id,
                    correlation_id=correlation_id,
                    workspace_id=str(workspace_id) if workspace_id else None,
                    company_id=str(company_id) if company_id else None,
                    tool_name=tool_name,
                    principal=principal,
                    decision="ALLOW",
                    input_payload=response.tool_call.arguments if audit_policy == "full" else {"summary": "redacted_minimal"},
                    outcome={"status": "success", "result": result} if audit_policy == "full" else {"status": "success"},
                )

            tool_calls_made += 1
            messages.append({"role": "assistant", "tool_call": response.tool_call.model_dump()})
            messages.append({"role": "tool", "content": result})

        raise ExecutorExhaustedError(MAX_TOOL_ROUNDS)
