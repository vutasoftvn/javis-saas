from __future__ import annotations

import string
from typing import Any, Callable, Optional, Union

from agent_core.governance.accumulator import InvocationGovernanceState
from agent_core.governance.contracts import PolicyDecision as GovernancePolicyDecision, PolicyOutcome
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.governance.store import GovernanceStateStore
from agentos.core.approval import ApprovalService, ApprovalStatus
from agentos.core.policy import (
    ExecutionMode,
    PermissionClass,
    PermissionLevel,
    PolicyDecision as LegacyPolicyDecision,
    PolicyEngine,
    ToolPermission,
    ToolRiskLevel,
)
from agentos.tools.registry import ToolRegistry
from agentos.workflows.models import StepOutcome, StepStatus


class ToolCallStep:
    """A workflow step executing a registered tool via ToolRegistry with
    strict PolicyEngine governance (roadmap §8b.4: mọi step type: tool_call
    đi qua đúng evaluate_access() như tool call bình thường — workflow không
    phải đường tắt bỏ qua governance).

    Mỗi lần run() được gọi (kể cả khi WorkflowEngine gọi lại step này lúc
    resume một workflow đang WAITING_APPROVAL), evaluate_access() được gọi
    lại — governance_store fold kết quả mới vào InvocationGovernanceState đã
    tích luỹ trước đó cho đúng invocation này (key: f"{run_id}:{tool_name}",
    khớp với key ApprovalService.find_by_run_and_action đã dùng), và step
    branch theo outcome ĐÃ TÍCH LUỸ, không phải outcome "hiện tại" một mình
    — nếu không, policy nới lỏng giữa lúc pause và lúc resume sẽ âm thầm bỏ
    qua nhánh REQUIRE_APPROVAL. Xem
    COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md Case B.
    """

    def __init__(
        self,
        name: str,
        tool_name: str,
        *,
        tool_registry: ToolRegistry,
        policy_engine: Optional[PolicyEngine] = None,
        approval_service: Optional[ApprovalService] = None,
        governance_store: Optional[GovernanceStateStore] = None,
        inputs: Optional[Union[dict[str, Any], Callable[[dict[str, Any]], dict[str, Any]]]] = None,
        output_key: Optional[str] = None,
        role: str = "founder",
        agent_permission_level: PermissionLevel = PermissionLevel.L3_EXECUTE,
        requester: str = "workflow_engine",
        workspace_key: str = "workspace_id",
        correlation_key: str = "correlation_id",
    ) -> None:
        self.name = name
        self.tool_name = tool_name
        self._tool_registry = tool_registry
        self._policy_engine = policy_engine or PolicyEngine()
        self._approval_service = approval_service or ApprovalService()
        self._governance_store = governance_store or InMemoryGovernanceStateStore()
        self._inputs = inputs or {}
        self._output_key = output_key or name
        self._role = role
        self._agent_permission_level = agent_permission_level
        self._requester = requester
        self._workspace_key = workspace_key
        self._correlation_key = correlation_key

    def _resolve_inputs(self, state: dict[str, Any]) -> dict[str, Any]:
        if callable(self._inputs):
            return self._inputs(state)

        resolved = {}
        for k, v in self._inputs.items():
            if isinstance(v, str) and v.startswith("$"):
                # Reference from state, e.g. "$evidence_items" -> state["evidence_items"]
                var_name = v[1:]
                resolved[k] = state.get(var_name)
            elif isinstance(v, str) and "{" in v and "}" in v:
                # String template substitution
                try:
                    resolved[k] = string.Template(v).safe_substitute(state)
                except Exception:
                    resolved[k] = v
            else:
                resolved[k] = v
        return resolved

    async def _accumulate_governance_decision(
        self, run_id: Any, legacy_decision: LegacyPolicyDecision
    ) -> LegacyPolicyDecision:
        if not run_id:
            return legacy_decision

        tool_call_id = f"{run_id}:{self.tool_name}"
        observation = GovernancePolicyDecision(outcome=PolicyOutcome(legacy_decision.value))

        existing = await self._governance_store.load_governance_state(str(run_id), tool_call_id)
        if existing is None:
            state = InvocationGovernanceState.start(
                run_id=str(run_id), tool_call_id=tool_call_id, initial=observation
            )
        else:
            state = existing.accumulate(observation)

        await self._governance_store.save_governance_state(state, observation=observation, source="historical")
        return LegacyPolicyDecision(state.accumulated.outcome.value)

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        spec = self._tool_registry.get(self.tool_name)
        arguments = self._resolve_inputs(state)

        workspace_id = state.get(self._workspace_key)
        correlation_id = state.get(self._correlation_key)
        run_id = state.get("run_id") or state.get("workflow_id")
        tenant_policy = state.get("tenant_policy")
        data_scope = state.get("data_scope")

        permission_enum = (
            PermissionClass(spec.permission_class) if spec.permission_class else None
        )
        approval_policy = getattr(spec, "approval_policy", "conditional")

        legacy_decision = self._policy_engine.evaluate_access(
            role=self._role,
            agent_permission_level=self._agent_permission_level,
            tool_risk_level=spec.risk_level,
            tool_permission=spec.tool_permission,
            tenant_policy=tenant_policy,
            execution_mode=ExecutionMode.APPROVED_WORKFLOW,
            data_scope=data_scope,
            permission_class=permission_enum,
            approval_policy=approval_policy,
            run_id=run_id,
            correlation_id=correlation_id,
            workspace_id=str(workspace_id) if workspace_id else None,
        )

        decision = await self._accumulate_governance_decision(run_id, legacy_decision)

        if decision == LegacyPolicyDecision.DENY:
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"Tool '{self.tool_name}' denied by policy for permission {spec.permission_class or 'DENY'}",
            )

        if decision == LegacyPolicyDecision.REQUIRE_APPROVAL:
            existing = self._approval_service.find_by_run_and_action(
                str(run_id), self.tool_name
            ) if run_id else None

            if existing is not None:
                if existing.status == ApprovalStatus.APPROVED:
                    pass  # Approved, proceed to execute
                elif existing.status == ApprovalStatus.DENIED:
                    return StepOutcome(
                        status=StepStatus.FAILED,
                        error=f"Approval for tool '{self.tool_name}' was denied: {existing.reason}",
                    )
                else:
                    return StepOutcome(
                        status=StepStatus.WAITING_APPROVAL,
                        approval_id=existing.id,
                    )
            else:
                approval = self._approval_service.request_approval(
                    action=self.tool_name,
                    subject=str(arguments),
                    requester=self._requester,
                    run_id=str(run_id) if run_id else None,
                    tool_name=self.tool_name,
                    correlation_id=correlation_id,
                )
                return StepOutcome(
                    status=StepStatus.WAITING_APPROVAL,
                    approval_id=approval.id,
                )

        try:
            result = await self._tool_registry.invoke(self.tool_name, arguments)
            return StepOutcome(
                status=StepStatus.COMPLETED,
                updates={self._output_key: result},
            )
        except Exception as exc:
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"Tool '{self.tool_name}' execution failed: {exc}",
            )
