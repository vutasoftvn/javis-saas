from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Callable, Optional

from agent_core.contracts.capability import (
    CapabilityReadiness,
    CapabilityReadinessReason,
    CapabilitySpec,
)
from agent_core.contracts.identity import InvocationIdentity
from agent_core.contracts.target import ExecutionTargetSnapshot
from agent_core.capabilities.readiness import (
    CapabilityReadinessChecker,
    RegistryCapabilityReadinessChecker,
)

logger = logging.getLogger(__name__)

from agent_core.contracts.wait import WaitDescriptor, WaitKind
from agent_core.governance.accumulator import InvocationGovernanceState
from agent_core.governance.contracts import CapabilityRisk, ExecutionMode, PolicyDecision, PolicyOutcome, PrincipalAuthorization
from agent_core.capabilities.canonicalization import canonicalize_payload, compute_payload_hash
from agent_core.capabilities.registry import CapabilityRegistration, CapabilityRegistry
from agent_core.runs.models import RunApprovalRecord, RunEventRecord, RunToolCallRecord
from agent_core.runs.repository import InMemoryRunRepository, RunRepository

__all__ = ["GatewayExecutionRequest", "GatewayExecutionResult", "CapabilityGateway"]


class GatewayExecutionRequest:
    def __init__(
        self,
        run_id: str,
        capability_id: str,
        input_payload: dict[str, Any],
        principal: str = "system",
        checkpoint_ref: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        execution_mode: ExecutionMode = ExecutionMode.WORKFLOW,
        workspace_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        self.run_id = run_id
        self.capability_id = capability_id
        self.input_payload = input_payload
        self.principal = principal
        self.checkpoint_ref = checkpoint_ref or f"ckpt_{run_id}_initial"
        self.tool_call_id = tool_call_id or f"call_{uuid.uuid4().hex[:12]}"
        self.idempotency_key = idempotency_key
        self.execution_mode = execution_mode
        self.workspace_id = workspace_id
        self.context = context or {}


class GatewayExecutionResult:
    def __init__(
        self,
        tool_call_id: str,
        status: str,  # "completed" | "failed" | "waiting_approval" | "denied"
        output_payload: Optional[Any] = None,
        error_message: Optional[str] = None,
        validation_errors: Optional[list[str]] = None,
        wait_descriptor: Optional[WaitDescriptor] = None,
        cached_idempotency: bool = False,
    ) -> None:
        self.tool_call_id = tool_call_id
        self.status = status
        self.output_payload = output_payload
        self.error_message = error_message
        self.validation_errors = validation_errors or []
        self.wait_descriptor = wait_descriptor
        self.cached_idempotency = cached_idempotency


class CapabilityGateway:
    """Canonical Capability Gateway theo Master Guide §16 & §17.
    
    Cung cấp pipeline 10 bước thực thi an toàn, idempotent, và tích hợp quản trị:
    1. Resolve capability
    2. Validate input schema
    3. Resolve connector/grant & construct target snapshot
    4. Construct stable InvocationIdentity
    5. Canonicalize payload & calculate payload_hash
    6. Policy evaluate (governance)
    7. Accumulate governance (monotonic)
    8. Approval gate check
    9. Idempotency check (tránh duplicate side-effects)
    10. Execute handler, audit events, persist tool_call record
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        repository: Optional[RunRepository] = None,
        policy_evaluator: Optional[Callable[[str, dict[str, Any], dict[str, Any]], str]] = None,
        readiness_checker: Optional[CapabilityReadinessChecker] = None,
    ) -> None:
        self._registry = registry
        self._repo = repository or InMemoryRunRepository()
        self._policy_evaluator = policy_evaluator
        self._readiness_checker = readiness_checker or RegistryCapabilityReadinessChecker(registry)
        self._gov_states: dict[tuple[str, str], InvocationGovernanceState] = {}

    async def execute(self, req: GatewayExecutionRequest) -> GatewayExecutionResult:
        # Bước 1: Resolve capability
        reg = self._registry.get(req.capability_id)
        if not reg:
            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="failed",
                error_message=f"Capability '{req.capability_id}' not found in registry",
            )

        spec = reg.spec

        # Bước 2: Validate input schema
        val_errors = self._registry.validate_input(spec, req.input_payload)
        if val_errors:
            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="failed",
                validation_errors=val_errors,
                error_message=f"Validation failed for capability '{req.capability_id}': {', '.join(val_errors)}",
            )

        # Bước 3: Canonicalize payload & tính payload_hash (Master Guide §17.2)
        payload_hash = compute_payload_hash(req.input_payload)
        idempotency_key = req.idempotency_key or f"{req.run_id}:{req.capability_id}:{payload_hash}"

        # Bước 4: Construct stable InvocationIdentity & ExecutionTargetSnapshot
        inv_identity = InvocationIdentity(
            tool_call_id=req.tool_call_id,
            run_id=req.run_id,
            capability_id=req.capability_id,
            payload_hash=payload_hash,
            idempotency_key=idempotency_key,
        )
        target_snapshot = ExecutionTargetSnapshot(
            capability_id=req.capability_id,
            connector_id=spec.connector_requirements.get("connector_id"),
            capability_risk_at_request_time=spec.risk,
            schema_hash_version=spec.metadata.get("definition_hash", "hash_default"),
        )

        # Bước 4.5: Capability Readiness Check (Hermes/LangGraph Phase 4)
        readiness = await self._readiness_checker.check(req.capability_id, req.context)
        if not readiness.ready:
            if readiness.reason_code == CapabilityReadinessReason.MISSING_CREDENTIAL:
                return GatewayExecutionResult(
                    tool_call_id=req.tool_call_id,
                    status="failed",
                    error_message=f"Capability readiness error: missing credential ({readiness.details})",
                )
            elif readiness.reason_code == CapabilityReadinessReason.CONNECTOR_OFFLINE:
                logger.warning(
                    f"[Gateway] Capability '{req.capability_id}' connector '{readiness.connector_ref}' is offline. Proceeding with warning - governance makes ultimate decision."
                )


        # Bước 5: Idempotency Check (Master Guide §17.3)
        existing_tc = await self._repo.get_tool_call_by_idempotency(req.run_id, idempotency_key)
        if not existing_tc:
            existing_tc = await self._repo.get_tool_call(req.tool_call_id)

        if existing_tc and existing_tc.status == "completed":
            # Đã thực thi thành công trước đó -> Trả về kết quả cached, KHÔNG chạy lại side effect
            return GatewayExecutionResult(
                tool_call_id=existing_tc.tool_call_id,
                status="completed",
                output_payload=existing_tc.output_payload,
                cached_idempotency=True,
            )

        # Lưu bản ghi tool_call vào exact invocation ledger ở trạng thái running
        tc_record = RunToolCallRecord(
            tool_call_id=req.tool_call_id,
            run_id=req.run_id,
            checkpoint_ref=req.checkpoint_ref,
            capability_id=req.capability_id,
            payload_hash=payload_hash,
            input_payload=req.input_payload,
            execution_target_snapshot=target_snapshot.model_dump(),
            idempotency_key=idempotency_key,
            status="running",
        )
        await self._repo.save_tool_call(tc_record)
        await self._repo.append_event(
            RunEventRecord(
                run_id=req.run_id,
                event_type="tool.requested",
                payload={"tool_call_id": req.tool_call_id, "capability": req.capability_id, "payload_hash": payload_hash},
            )
        )

        # Bước 6: Policy Evaluate
        if self._policy_evaluator:
            eval_res = self._policy_evaluator(req.capability_id, req.input_payload, req.context)
            if isinstance(eval_res, PolicyDecision):
                current_decision = eval_res
                decision_str = eval_res.outcome.value
            else:
                outcome_str = str(eval_res).upper()
                outcome_map = {
                    "ALLOW": PolicyOutcome.ALLOW,
                    "REQUIRE_APPROVAL": PolicyOutcome.REQUIRE_APPROVAL,
                    "DENY": PolicyOutcome.DENY,
                }
                outcome = outcome_map.get(outcome_str, PolicyOutcome.ALLOW)
                current_decision = PolicyDecision(outcome=outcome, reasons=(f"Decision: {outcome_str}",))
                decision_str = outcome.value
        elif spec.risk == CapabilityRisk.HIGH:
            current_decision = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, reasons=("High risk capability",))
            decision_str = "REQUIRE_APPROVAL"
        elif ("transfer" in req.capability_id or "payout" in req.capability_id) and spec.risk != CapabilityRisk.LOW:
            current_decision = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, reasons=("Payout action",))
            decision_str = "REQUIRE_APPROVAL"
        else:
            current_decision = PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("Default allow",))
            decision_str = "ALLOW"

        await self._repo.append_event(
            RunEventRecord(
                run_id=req.run_id,
                event_type="policy.evaluated",
                payload={"tool_call_id": req.tool_call_id, "decision": decision_str},
            )
        )

        # Bước 7: Accumulate Governance (Monotonic Governance Accumulator)
        state_key = (req.run_id, req.tool_call_id)
        if state_key not in self._gov_states:
            self._gov_states[state_key] = InvocationGovernanceState.start(
                run_id=req.run_id,
                tool_call_id=req.tool_call_id,
                initial=current_decision,
            )
        else:
            self._gov_states[state_key] = self._gov_states[state_key].accumulate(current_decision)


        gov_state = self._gov_states[state_key]
        effective_outcome = gov_state.accumulated.outcome

        # Bước 8: Approval Gate Check
        if effective_outcome == PolicyOutcome.REQUIRE_APPROVAL:
            # Kiểm tra xem có approval record đã duyệt chưa
            approval = await self._repo.get_approval_by_tool_call(req.tool_call_id)
            if not approval or approval.status != "approved":
                if not approval:
                    appr_id = f"appr_{req.run_id}_{req.tool_call_id}"
                    approval = RunApprovalRecord(
                        approval_id=appr_id,
                        run_id=req.run_id,
                        tool_call_id=req.tool_call_id,
                        checkpoint_ref=req.checkpoint_ref,
                        status="pending",
                        action=req.capability_id,
                        subject=f"Approval needed for {req.capability_id} (payload_hash: {payload_hash[:8]})",
                        requirement={"kind": "role_approval", "role": "founder"},
                    )
                    await self._repo.create_approval(approval)
                    await self._repo.append_event(
                        RunEventRecord(
                            run_id=req.run_id,
                            event_type="approval.required",
                            payload={"approval_id": appr_id, "tool_call_id": req.tool_call_id},
                        )
                    )

                wait = WaitDescriptor(
                    kind=WaitKind.APPROVAL,
                    reason=f"Action '{req.capability_id}' requires human approval",
                    checkpoint_ref=req.checkpoint_ref,
                    related_ref=approval.approval_id,
                    resume_trigger="approval.decided",
                )
                tc_record.status = "waiting_approval"
                tc_record.governance_state = gov_state.model_dump()
                await self._repo.save_tool_call(tc_record)

                return GatewayExecutionResult(
                    tool_call_id=req.tool_call_id,
                    status="waiting_approval",
                    wait_descriptor=wait,
                )

        if effective_outcome == PolicyOutcome.DENY:
            tc_record.status = "denied"
            await self._repo.save_tool_call(tc_record)
            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="denied",
                error_message=f"Execution of '{req.capability_id}' denied by policy",
            )

        # Bước 9 & 10: Execute Handler
        await self._repo.append_event(
            RunEventRecord(
                run_id=req.run_id,
                event_type="tool.started",
                payload={"tool_call_id": req.tool_call_id, "capability": req.capability_id},
            )
        )

        try:
            handler = reg.handler
            if asyncio.iscoroutinefunction(handler):
                output = await handler(req.input_payload, req.context)
            else:
                output = handler(req.input_payload, req.context)

            # Persist status completed & audit
            tc_record.status = "completed"
            tc_record.output_payload = output
            tc_record.governance_state = gov_state.model_dump()
            await self._repo.save_tool_call(tc_record)


            await self._repo.append_event(
                RunEventRecord(
                    run_id=req.run_id,
                    event_type="tool.completed",
                    payload={"tool_call_id": req.tool_call_id, "output": output},
                )
            )

            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="completed",
                output_payload=output,
            )

        except Exception as exc:
            tc_record.status = "failed"
            tc_record.error_message = str(exc)
            await self._repo.save_tool_call(tc_record)

            await self._repo.append_event(
                RunEventRecord(
                    run_id=req.run_id,
                    event_type="tool.failed",
                    payload={"tool_call_id": req.tool_call_id, "error": str(exc)},
                )
            )

            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="failed",
                error_message=str(exc),
            )
