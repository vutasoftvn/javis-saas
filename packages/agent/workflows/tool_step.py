from __future__ import annotations

import string
import uuid
from collections.abc import Callable
from typing import Any

from agent.capabilities.gateway import GatewayExecutionRequest
from agent.contracts.invocation import InvocationContext
from agent.governance.accumulator import InvocationGovernanceState
from agent.governance.contracts import (
    AutonomyLevel,
    CapabilityRisk,
    ExecutionMode,
    PolicyOutcome,
)
from agent.governance.contracts import (
    PolicyDecision as GovernancePolicyDecision,
)
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.governance.store import GovernanceStateStore
from agent.workflows.models import StepOutcome, StepStatus

__all__ = ["GatewayToolCallStep", "ToolCallStep"]


class ToolCallStep:
    """Bước thực thi tool/capability trong Workflow có tích hợp Governance Monotonic Accumulator.

    Khi chạy hoặc resume, gọi governance evaluation và fold kết quả vào
    InvocationGovernanceState đã tích luỹ (key: f"{run_id}:{tool_name}").
    Không để policy nới lỏng giữa chừng âm thầm bypass approval.
    """

    def __init__(
        self,
        name: str,
        tool_name: str,
        *,
        tool_registry: Any,
        policy_engine: Any | None = None,
        approval_service: Any | None = None,
        governance_store: GovernanceStateStore | None = None,
        inputs: dict[str, Any] | Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        output_key: str | None = None,
        role: str = "founder",
        autonomy_level: AutonomyLevel = AutonomyLevel.L3_AUTONOMOUS,
        requester: str = "workflow_engine",
        workspace_key: str = "workspace_id",
        correlation_key: str = "correlation_id",
    ) -> None:
        self.name = name
        self.tool_name = tool_name
        self._tool_registry = tool_registry
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._governance_store = governance_store or InMemoryGovernanceStateStore()
        self._inputs = inputs or {}
        self._output_key = output_key or name
        self._role = role
        self._autonomy_level = autonomy_level
        self._requester = requester
        self._workspace_key = workspace_key
        self._correlation_key = correlation_key

    def _resolve_inputs(self, state: dict[str, Any]) -> dict[str, Any]:
        if callable(self._inputs):
            return self._inputs(state)

        resolved = {}
        for k, v in self._inputs.items():
            if isinstance(v, str) and v.startswith("$"):
                var_name = v[1:]
                resolved[k] = state.get(var_name)
            elif isinstance(v, str) and "{" in v and "}" in v:
                try:
                    resolved[k] = string.Template(v).safe_substitute(state)
                except Exception:
                    resolved[k] = v
            else:
                resolved[k] = v
        return resolved

    async def _accumulate_governance_decision(self, run_id: Any, decision_val: str) -> str:
        if not run_id:
            return decision_val

        tool_call_id = f"{run_id}:{self.tool_name}"
        outcome_enum = PolicyOutcome.REQUIRE_APPROVAL
        if "ALLOW" in decision_val:
            outcome_enum = PolicyOutcome.ALLOW
        elif "DENY" in decision_val:
            outcome_enum = PolicyOutcome.DENY

        observation = GovernancePolicyDecision(outcome=outcome_enum)
        existing = await self._governance_store.load_governance_state(str(run_id), tool_call_id)
        if existing is None:
            new_state = InvocationGovernanceState.start(
                run_id=str(run_id), tool_call_id=tool_call_id, initial=observation
            )
        else:
            new_state = existing.accumulate(observation)

        await self._governance_store.save_governance_state(
            new_state, observation=observation, source="ToolCallStep"
        )
        return new_state.accumulated.outcome.value

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        tool = None
        if hasattr(self._tool_registry, "get"):
            tool = self._tool_registry.get(self.tool_name)

        if not tool:
            return StepOutcome(
                status=StepStatus.FAILED, error=f"Tool '{self.tool_name}' not found in registry"
            )

        # 1. Đánh giá Policy
        run_id = state.get("run_id") or state.get("workflow_id")
        workspace_id = state.get(self._workspace_key)
        correlation_id = state.get(self._correlation_key)
        tenant_policy = state.get("tenant_policy")
        data_scope = state.get("data_scope")

        effective_decision = "ALLOW"
        if self._policy_engine:
            if hasattr(self._policy_engine, "evaluate_access"):
                perm_level = getattr(
                    tool, "permission_level", getattr(tool, "autonomy_level", self._autonomy_level)
                )
                risk = getattr(tool, "risk_level", getattr(tool, "risk", CapabilityRisk.LOW))
                tool_perm = getattr(
                    tool, "permission", getattr(tool, "tool_permission", "scoped_write")
                )
                perm_class = getattr(tool, "permission_class", None)
                approval_pol = getattr(tool, "approval_policy", "conditional")

                try:
                    raw_decision = self._policy_engine.evaluate_access(
                        role=self._role,
                        agent_permission_level=perm_level,
                        tool_risk_level=risk,
                        tool_permission=tool_perm,
                        tenant_policy=tenant_policy,
                        execution_mode=ExecutionMode.APPROVED_WORKFLOW,
                        data_scope=data_scope,
                        permission_class=perm_class,
                        approval_policy=approval_pol,
                        run_id=run_id,
                        correlation_id=correlation_id,
                        workspace_id=str(workspace_id) if workspace_id else None,
                    )
                except TypeError:
                    # Fallback for simpler mocks with fewer arguments
                    raw_decision = self._policy_engine.evaluate_access(
                        role=self._role,
                        agent_permission_level=perm_level,
                        tool_risk_level=risk,
                        tool_permission=tool_perm,
                        data_scope=data_scope,
                        run_id=run_id,
                        correlation_id=correlation_id,
                        workspace_id=workspace_id,
                    )
                effective_decision = str(getattr(raw_decision, "value", raw_decision)).upper()
            elif hasattr(self._policy_engine, "evaluate"):
                raw_decision = self._policy_engine.evaluate(tool)
                effective_decision = str(getattr(raw_decision, "value", raw_decision)).upper()

        # Tích luỹ governance
        effective_decision = await self._accumulate_governance_decision(run_id, effective_decision)

        if "DENY" in effective_decision:
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"ToolCallStep '{self.name}' (tool: {self.tool_name}) is DENIED by policy",
            )

        if "REQUIRE_APPROVAL" in effective_decision:
            if not self._approval_service:
                return StepOutcome(
                    status=StepStatus.FAILED,
                    error=f"ToolCallStep '{self.name}' requires approval but no ApprovalService configured",
                )

            # Kiểm tra xem đã có pending approval trước đó chưa
            existing_approval = None
            if hasattr(self._approval_service, "find_by_run_and_action") and run_id:
                try:
                    existing_approval = self._approval_service.find_by_run_and_action(
                        str(run_id), self.tool_name
                    )
                except TypeError:
                    existing_approval = self._approval_service.find_by_run_and_action(
                        run_id=str(run_id), action=self.tool_name
                    )

            if existing_approval:
                status_str = str(getattr(existing_approval, "status", "")).upper()
                if "APPROVED" in status_str:
                    # Cho phép tiếp tục thực thi tool bên dưới
                    pass
                elif "DENIED" in status_str:
                    return StepOutcome(
                        status=StepStatus.FAILED,
                        error=f"Approval for tool '{self.tool_name}' was DENIED: {getattr(existing_approval, 'reason', '')}",
                    )
                else:
                    return StepOutcome(
                        status=StepStatus.WAITING_APPROVAL,
                        approval_id=getattr(existing_approval, "id", str(existing_approval)),
                    )
            else:
                resolved_inputs = self._resolve_inputs(state)
                req_obj = self._approval_service.request_approval(
                    action=self.tool_name,
                    subject=f"Execute tool {self.tool_name} with params {resolved_inputs}",
                    requester=self._requester,
                    run_id=str(run_id) if run_id else None,
                    workspace_id=str(workspace_id) if workspace_id else None,
                )
                return StepOutcome(
                    status=StepStatus.WAITING_APPROVAL,
                    approval_id=getattr(req_obj, "id", str(req_obj)),
                )

        # 2. Thực thi Tool
        resolved_inputs = self._resolve_inputs(state)
        try:
            if hasattr(tool, "execute"):
                import inspect

                if inspect.iscoroutinefunction(tool.execute):
                    result = await tool.execute(**resolved_inputs)
                else:
                    result = tool.execute(**resolved_inputs)
            elif callable(tool):
                import inspect

                if inspect.iscoroutinefunction(tool):
                    result = await tool(**resolved_inputs)
                else:
                    result = tool(**resolved_inputs)
            else:
                result = None

            return StepOutcome(
                status=StepStatus.COMPLETED,
                updates={self._output_key: result},
            )
        except Exception as exc:
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"ToolCallStep '{self.name}' execution failed: {exc}",
            )


class GatewayToolCallStep:
    """Bước thực thi Capability trong Workflow thông qua CapabilityGateway.

    Tuân thủ FounderStack Harness & Blueprint V2:
    - Side-effect trong Workflow bắt buộc gọi qua CapabilityGateway.
    - tool_call_id: UUID sinh ở lần chạy đầu, lưu vào workflow state/checkpoint,
      tái sử dụng khi retry/resume để bảo toàn định danh exact invocation.
    - Không gọi trực tiếp handler, bắt buộc qua Gateway pipeline.
    """

    def __init__(
        self,
        name: str,
        tool_name: str,
        *,
        gateway: Any,
        inputs: dict[str, Any] | Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        output_key: str | None = None,
        workspace_key: str = "workspace_id",
        principal_key: str = "principal",
        checkpoint_ref: str | None = None,
    ) -> None:
        self.name = name
        self.tool_name = tool_name
        self._gateway = gateway
        self._inputs = inputs or {}
        self._output_key = output_key or name
        self._workspace_key = workspace_key
        self._principal_key = principal_key
        self._checkpoint_ref = checkpoint_ref

    def _resolve_inputs(self, state: dict[str, Any]) -> dict[str, Any]:
        if callable(self._inputs):
            return self._inputs(state)

        resolved = {}
        for k, v in self._inputs.items():
            if isinstance(v, str) and v.startswith("$"):
                var_name = v[1:]
                resolved[k] = state.get(var_name)
            elif isinstance(v, str) and "{" in v and "}" in v:
                try:
                    resolved[k] = string.Template(v).safe_substitute(state)
                except Exception:
                    resolved[k] = v
            else:
                resolved[k] = v
        return resolved

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        run_id = str(state.get("run_id") or state.get("workflow_id") or f"wf_run_{uuid.uuid4().hex[:12]}")
        workspace_id = str(state.get(self._workspace_key) or state.get("workspace_id") or "")
        principal = str(state.get(self._principal_key) or state.get("principal") or "system")

        # tool_call_id: UUID sinh ở lần chạy đầu, lưu vào state / checkpoint
        state_key_tool_call_id = f"_tool_call_id_{self.name}"
        tool_call_id = state.get(state_key_tool_call_id)
        if not tool_call_id:
            tool_call_id = f"call_{uuid.uuid4().hex[:12]}"
            state[state_key_tool_call_id] = tool_call_id

        ckpt_ref = self._checkpoint_ref or state.get("checkpoint_ref") or f"ckpt_{run_id}_{self.name}"
        resolved_inputs = self._resolve_inputs(state)

        inv_ctx = InvocationContext(
            run_id=run_id,
            tool_call_id=tool_call_id,
            checkpoint_ref=ckpt_ref,
            workspace_id=workspace_id,
            principal=principal,
            conversation_id=state.get("conversation_id"),
            correlation_id=state.get("correlation_id"),
            policy_snapshot=state.get("policy_snapshot"),
            root_spec_identity=state.get("workflow_name") or state.get("workflow_spec_id"),
            capability_identity=self.tool_name,
            execution_mode=ExecutionMode.APPROVED_WORKFLOW,
            metadata=dict(state),
        )

        req = GatewayExecutionRequest(
            run_id=run_id,
            capability_id=self.tool_name,
            input_payload=resolved_inputs,
            principal=principal,
            checkpoint_ref=ckpt_ref,
            tool_call_id=tool_call_id,
            execution_mode=ExecutionMode.APPROVED_WORKFLOW,
            workspace_id=workspace_id,
            context=inv_ctx,
        )

        result = await self._gateway.execute(req)

        if result.status == "waiting_approval":
            approval_id = (
                result.wait_descriptor.related_ref
                if result.wait_descriptor
                else f"appr_{run_id}_{tool_call_id}"
            )
            return StepOutcome(
                status=StepStatus.WAITING_APPROVAL,
                approval_id=approval_id,
            )

        if result.status in ("denied", "failed"):
            return StepOutcome(
                status=StepStatus.FAILED,
                error=result.error_message or f"Gateway execution of '{self.tool_name}' failed with status '{result.status}'",
            )

        return StepOutcome(
            status=StepStatus.COMPLETED,
            updates={
                self._output_key: result.output_payload,
                state_key_tool_call_id: tool_call_id,
            },
        )

