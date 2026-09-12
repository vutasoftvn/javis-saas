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

__all__ = ["GatewayToolCallStep"]


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
        run_id = str(
            state.get("run_id") or state.get("workflow_id") or f"wf_run_{uuid.uuid4().hex[:12]}"
        )
        workspace_id = str(state.get(self._workspace_key) or state.get("workspace_id") or "")
        principal = str(state.get(self._principal_key) or state.get("principal") or "system")

        # tool_call_id: UUID sinh ở lần chạy đầu, lưu vào state / checkpoint
        state_key_tool_call_id = f"_tool_call_id_{self.name}"
        tool_call_id = state.get(state_key_tool_call_id)
        if not tool_call_id:
            tool_call_id = f"call_{uuid.uuid4().hex[:12]}"
            state[state_key_tool_call_id] = tool_call_id

        ckpt_ref = (
            self._checkpoint_ref or state.get("checkpoint_ref") or f"ckpt_{run_id}_{self.name}"
        )
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
                error=result.error_message
                or f"Gateway execution of '{self.tool_name}' failed with status '{result.status}'",
            )

        return StepOutcome(
            status=StepStatus.COMPLETED,
            updates={
                self._output_key: result.output_payload,
                state_key_tool_call_id: tool_call_id,
            },
        )
