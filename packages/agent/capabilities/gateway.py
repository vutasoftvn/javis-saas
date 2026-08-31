from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from agent.capabilities.grants import ConnectorGrant, verify_connector_grant
from agent.capabilities.readiness import (
    CapabilityReadinessChecker,
    RegistryCapabilityReadinessChecker,
)
from agent.contracts.capability import (
    CapabilityReadinessReason,
)
from agent.contracts.identity import InvocationIdentity
from agent.contracts.target import ExecutionTargetSnapshot

logger = logging.getLogger(__name__)

from agent.capabilities.canonicalization import compute_payload_hash
from agent.capabilities.enablements import EnablementStore, InMemoryEnablementStore
from agent.capabilities.gateway_internals import (
    ComplianceAuditor,
    EnablementValidator,
    IdempotencyCoordinator,
    InputValidator,
    TenancyVerifier,
)
from agent.capabilities.idempotency import IdempotencyClaimService
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.errors import TenancyUnresolvedError
from agent.contracts.invocation import InvocationContext
from agent.contracts.wait import WaitDescriptor, WaitKind
from agent.governance.accumulator import InvocationGovernanceState
from agent.governance.ambient import verify_ambient_governance
from agent.governance.contracts import (
    ExecutionMode,
    PolicyOutcome,
)
from agent.governance.floor import capability_floor, conjoin
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.governance.store import GovernanceStateStore
from agent.runs.models import (
    RunApprovalRecord,
    RunEventRecord,
    RunToolCallRecord,
)
from agent.runs.repository import InMemoryRunRepository, RunRepository

__all__ = ["CapabilityGateway", "GatewayExecutionRequest", "GatewayExecutionResult"]


class GatewayExecutionRequest:
    def __init__(
        self,
        run_id: str,
        capability_id: str,
        input_payload: dict[str, Any],
        principal: str = "system",
        checkpoint_ref: str | None = None,
        tool_call_id: str | None = None,
        idempotency_key: str | None = None,
        execution_mode: ExecutionMode = ExecutionMode.WORKFLOW,
        workspace_id: str | None = None,
        context: InvocationContext | dict[str, Any] | None = None,
    ) -> None:
        self.run_id = run_id
        self.capability_id = capability_id
        self.input_payload = input_payload
        self.workspace_id: str | None
        self.context: Any
        if isinstance(context, InvocationContext):
            self.workspace_id = workspace_id or context.workspace_id
            self.principal = (
                context.principal if (principal == "system" and context.principal) else principal
            )
            self.checkpoint_ref = checkpoint_ref or context.checkpoint_ref
            self.tool_call_id = tool_call_id or context.tool_call_id
            self.execution_mode = context.execution_mode
            self.context = context
        else:
            ctx_dict = dict(context) if isinstance(context, dict) else {}
            raw_ws = workspace_id or ctx_dict.get("workspace_id")
            self.workspace_id = str(raw_ws) if raw_ws is not None else None
            self.principal = (
                principal if principal != "system" else (ctx_dict.get("principal") or "system")
            )
            self.checkpoint_ref = checkpoint_ref or f"ckpt_{run_id}_initial"
            self.tool_call_id = tool_call_id or f"call_{uuid.uuid4().hex[:12]}"
            self.execution_mode = execution_mode
            if self.workspace_id and "workspace_id" not in ctx_dict:
                ctx_dict["workspace_id"] = self.workspace_id
            if self.principal and "principal" not in ctx_dict:
                ctx_dict["principal"] = self.principal
            if "run_id" not in ctx_dict:
                ctx_dict["run_id"] = self.run_id
            if "tool_call_id" not in ctx_dict:
                ctx_dict["tool_call_id"] = self.tool_call_id
            if "checkpoint_ref" not in ctx_dict:
                ctx_dict["checkpoint_ref"] = self.checkpoint_ref
            self.context = ctx_dict

        self.idempotency_key = idempotency_key


class GatewayExecutionResult:
    def __init__(
        self,
        tool_call_id: str,
        status: str,  # "completed" | "failed" | "waiting_approval" | "denied"
        output_payload: Any | None = None,
        error_message: str | None = None,
        validation_errors: list[str] | None = None,
        wait_descriptor: WaitDescriptor | None = None,
        cached_idempotency: bool = False,
        failure: Any | None = None,
    ) -> None:
        self.tool_call_id = tool_call_id
        self.status = status
        self.output_payload = output_payload
        self.error_message = error_message
        self.validation_errors = validation_errors or []
        self.wait_descriptor = wait_descriptor
        self.cached_idempotency = cached_idempotency
        self.failure = failure


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
        repository: RunRepository | None = None,
        policy_evaluator: Callable[..., Any] | None = None,
        readiness_checker: CapabilityReadinessChecker | None = None,
        governance_store: GovernanceStateStore | None = None,
        connector_grant_resolver: Callable[
            [str, GatewayExecutionRequest], Awaitable[ConnectorGrant | None]
        ]
        | None = None,
        enablement_store: EnablementStore | None = None,
    ) -> None:
        self._registry = registry
        self._repo = repository or InMemoryRunRepository()
        self._policy_evaluator = policy_evaluator
        self._readiness_checker = readiness_checker or RegistryCapabilityReadinessChecker(registry)
        # Durable governance accumulator (agent_governance.invocation_governance_state,
        # migration 002) — TRƯỚC ĐÂY `self._gov_states` là dict in-memory riêng của
        # Gateway, không load lại khi process restart, vi phạm invariant "monotonic
        # across restart" (Blueprint V2 §9.2). `packages/agent/workflows/{engine,
        # tool_step}.py` đã dùng đúng GovernanceStateStore từ trước — Gateway giờ dùng
        # lại CÙNG store thay vì có state riêng, không tạo cơ chế song song.
        self._governance_store = governance_store or InMemoryGovernanceStateStore()
        self._idempotency = IdempotencyClaimService(self._repo)
        self._connector_grant_resolver = connector_grant_resolver
        self._enablement_store = enablement_store or InMemoryEnablementStore()

    async def execute(self, req: GatewayExecutionRequest) -> GatewayExecutionResult:
        from opentelemetry import trace

        tracer = trace.get_tracer("agent.gateway")
        with tracer.start_as_current_span(
            "capability.execute",
            attributes={
                "run_id": req.run_id,
                "tool_call_id": req.tool_call_id,
                "capability": req.capability_id,
                "workspace_id": req.workspace_id or "",
            },
        ):
            return await self._execute_internal(req)

    async def _execute_internal(self, req: GatewayExecutionRequest) -> GatewayExecutionResult:
        # Bước 1: Resolve capability
        reg = self._registry.get(req.capability_id)
        if not reg:
            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="failed",
                error_message=f"Capability '{req.capability_id}' not found in registry",
            )

        spec = reg.spec

        # Bước 1.5: Tenancy Fail-Closed Verification (A2)
        verifier = TenancyVerifier()
        try:
            # resolved_principal không được dùng lại sau bước tenancy (chỉ resolved_workspace
            # được dùng ở các bước sau) — giữ tên rõ nghĩa qua verify(), không đổi hành vi.
            resolved_workspace, _resolved_principal = await verifier.verify(spec, req)
        except TenancyUnresolvedError as e:
            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="failed",
                error_message=str(e),
                failure=e,
            )

        # Bước 2: Validate input schema
        validator = InputValidator(self._registry)
        val_errors = validator.validate(spec, req.input_payload)
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
        InvocationIdentity(
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
        readiness_ctx = (
            req.context.metadata if isinstance(req.context, InvocationContext) else req.context
        )
        readiness = await self._readiness_checker.check(req.capability_id, readiness_ctx)
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

        # Bước 4.8: Scoped Capability Enablement Verification (Tranche C / Task 1)
        enablement_validator = EnablementValidator(self._enablement_store)
        is_enabled, enb_error = await enablement_validator.validate(
            spec=spec,
            capability_id=req.capability_id,
            workspace_id=str(resolved_workspace or ""),
            context=req.context,
        )
        if not is_enabled:
            skill_hash = enablement_validator.extract_skill_hash(req.context)
            def_hash_val = spec.metadata.get("definition_hash") or getattr(
                spec, "definition_hash", None
            )
            tc_record = RunToolCallRecord(
                tool_call_id=req.tool_call_id,
                run_id=req.run_id,
                checkpoint_ref=req.checkpoint_ref,
                capability_id=req.capability_id,
                payload_hash=payload_hash,
                input_payload=req.input_payload,
                execution_target_snapshot=target_snapshot.model_dump(),
                idempotency_key=idempotency_key,
                status="denied",
                spec_version=getattr(spec, "version", "1.0.0"),
                definition_hash=def_hash_val or skill_hash,
                error_message=enb_error,
            )
            await self._repo.save_tool_call(tc_record)
            await self._repo.append_event(
                RunEventRecord(
                    run_id=req.run_id,
                    event_type="capability.enablement_denied",
                    payload={
                        "tool_call_id": req.tool_call_id,
                        "capability": req.capability_id,
                        "reason": enb_error,
                        "action_class": enablement_validator.extract_action_class(
                            spec, req.context
                        ),
                    },
                )
            )
            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="denied",
                error_message=f"Execution of '{req.capability_id}' denied: {enb_error}",
            )

        # Bước 5: Idempotency Check — atomic claim (Blueprint V2 §20; thay
        # check-then-act cũ vốn có race window giữa 2 worker cùng đọc "chưa completed"
        # rồi cùng chạy handler). INSERT ... ON CONFLICT DO NOTHING ở tầng repository
        # đảm bảo đúng 1 worker thắng claim cho mỗi (run_id, capability_id, idempotency_key).
        idem_coordinator = IdempotencyCoordinator(self._idempotency)
        idem_outcome, idem_claim = await idem_coordinator.coordinate(
            run_id=req.run_id,
            tool_call_id=req.tool_call_id,
            capability_id=req.capability_id,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
        )

        if idem_coordinator.should_return_cached(idem_outcome):
            # Đã thực thi thành công trước đó -> Trả về kết quả cached, KHÔNG chạy lại side effect
            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="completed",
                output_payload=idem_claim.result_payload,
                cached_idempotency=True,
            )

        if idem_coordinator.should_return_in_progress(idem_outcome):
            # Worker/request khác đang giữ claim này — KHÔNG chạy handler để tránh
            # duplicate side effect. Caller (kernel/workflow engine) tự quyết định
            # retry/backoff; gateway không tự ý chờ (tránh block hot path vô thời hạn).
            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="in_progress",
                error_message=(
                    f"Capability '{req.capability_id}' đang được thực thi bởi lần gọi khác "
                    f"với cùng idempotency_key (claim_id={idem_claim.claim_id})"
                ),
            )

        inv_ctx = req.context if isinstance(req.context, InvocationContext) else None
        def_hash = spec.metadata.get("definition_hash") or getattr(spec, "definition_hash", None)
        pol_ref = (
            inv_ctx.policy_snapshot_ref
            if inv_ctx
            else (req.context.get("policy_snapshot_ref") if isinstance(req.context, dict) else None)
        )

        # idem_outcome in (CLAIMED, RETRIED) -> ta giữ claim, được quyền tiếp tục.
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
            spec_version=getattr(spec, "version", "1.0.0"),
            definition_hash=def_hash,
            policy_snapshot_ref=pol_ref,
        )
        await self._repo.save_tool_call(tc_record)
        await self._repo.append_event(
            RunEventRecord(
                run_id=req.run_id,
                event_type="tool.requested",
                payload={
                    "tool_call_id": req.tool_call_id,
                    "capability": req.capability_id,
                    "payload_hash": payload_hash,
                },
            )
        )

        # Bước 6: Policy Evaluate
        floor_outcome = capability_floor(spec.risk, spec.approval_policy)
        tenant_eval_res = None
        if self._policy_evaluator:
            ctx_payload = (
                req.context.metadata if isinstance(req.context, InvocationContext) else req.context
            )
            if (
                isinstance(ctx_payload, dict)
                and resolved_workspace
                and "workspace_id" not in ctx_payload
            ):
                ctx_payload = {**ctx_payload, "workspace_id": resolved_workspace}
            tenant_eval_res = self._policy_evaluator(
                req.capability_id, req.input_payload, ctx_payload
            )

        current_decision = conjoin(floor_outcome, tenant_eval_res)
        decision_str = current_decision.outcome.value

        await self._repo.append_event(
            RunEventRecord(
                run_id=req.run_id,
                event_type="policy.evaluated",
                payload={"tool_call_id": req.tool_call_id, "decision": decision_str},
            )
        )

        # Compliance audit decision event (Task 9) — extracted vào ComplianceAuditor
        # (Task 6 modular-boundary-hardening): kiểm tra deployment status, ghi
        # `compliance.decision` event, deny sớm nếu deployment bị suspend/chưa duyệt.
        compliance_auditor = ComplianceAuditor(self._repo)
        should_continue, early_deny_result, pending_deny_event = await compliance_auditor.audit(
            context=req.context,
            run_id=req.run_id,
            workspace_id=str(resolved_workspace or ""),
            tool_call_id=req.tool_call_id,
            checkpoint_ref=req.checkpoint_ref or "",
            capability_id=req.capability_id,
            current_decision=current_decision,
            payload_hash=payload_hash,
        )
        if not should_continue:
            # Thứ tự PHẢI khớp nguyên bản: tc_record save + idempotency.fail
            # TRƯỚC compliance.decision DENY event append — nếu crash giữa
            # save/fail và event append, retry sau đó thấy claim đã fail nên
            # KHÔNG re-enter audit() nữa, tránh ghi trùng event DENY (xem
            # docstring ComplianceAuditor.audit()).
            tc_record.status = "denied"
            await self._repo.save_tool_call(tc_record)
            await self._idempotency.fail(
                idem_claim.claim_id, error_message="Deployment suspended or not approved"
            )
            if pending_deny_event is not None:
                await self._repo.append_event(pending_deny_event)
            return early_deny_result

        # Bước 7: Accumulate Governance (Monotonic Governance Accumulator) — durable,
        # load lại từ governance_store thay vì dict in-memory (đúng invariant monotonic
        # across restart: cùng (run_id, tool_call_id) quay lại sau restart phải tiếp
        # tục accumulate, không bắt đầu lại từ đầu).
        existing_gov_state = await self._governance_store.load_governance_state(
            req.run_id, req.tool_call_id
        )
        if existing_gov_state is None:
            gov_state = InvocationGovernanceState.start(
                run_id=req.run_id,
                tool_call_id=req.tool_call_id,
                initial=current_decision,
            )
        else:
            gov_state = existing_gov_state.accumulate(current_decision)
        await self._governance_store.save_governance_state(
            gov_state, observation=current_decision, source="capability_gateway"
        )

        effective_outcome = gov_state.accumulated.outcome

        # Bước 8: Approval Gate Check
        if effective_outcome == PolicyOutcome.REQUIRE_APPROVAL:
            # Kiểm tra xem có approval record đã duyệt chưa
            # Exact invocation matching: khớp cả tool_call_id và checkpoint_ref
            approval = await self._repo.get_approval_by_tool_call(req.tool_call_id)
            checkpoint_mismatch = bool(
                approval
                and req.checkpoint_ref
                and approval.checkpoint_ref
                and approval.checkpoint_ref != req.checkpoint_ref
            )
            if not approval or approval.status != "approved" or checkpoint_mismatch:
                if not approval or checkpoint_mismatch:
                    appr_id = f"appr_{req.run_id}_{req.tool_call_id}"
                    req_model = current_decision.requirement
                    req_dict = (
                        req_model.model_dump()
                        if req_model is not None and hasattr(req_model, "model_dump")
                        else {"kind": "role_approval", "role": "founder"}
                    )
                    approval = RunApprovalRecord(
                        approval_id=appr_id,
                        run_id=req.run_id,
                        tool_call_id=req.tool_call_id,
                        checkpoint_ref=req.checkpoint_ref,
                        status="pending",
                        action=req.capability_id,
                        subject=f"Approval needed for {req.capability_id} (payload_hash: {payload_hash[:8]})",
                        requirement=req_dict,
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
            # DENY là terminal — giải phóng claim để lần gọi sau (payload khác, sau khi
            # policy đổi) không bị chặn vĩnh viễn bởi claim "running" không bao giờ hoàn tất.
            await self._idempotency.fail(idem_claim.claim_id, error_message="Denied by policy")
            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="denied",
                error_message=f"Execution of '{req.capability_id}' denied by policy",
            )

        # Bước 8.5: Re-verify Connector Grant — chạy lại ở MỌI lần execute(),
        # kể cả lần resume sau approval (approval được duyệt không có nghĩa
        # grant vẫn còn hiệu lực tại thời điểm side effect thực sự xảy ra).
        connector_id = spec.connector_requirements.get("connector_id")
        if connector_id and self._connector_grant_resolver:
            try:
                grant = await self._connector_grant_resolver(connector_id, req)
            except Exception as e:
                # Resolver gọi HTTP tới control-plane có thể timeout/connection error.
                # Fail-closed: không được execute handler nếu grant status không xác nhận được.
                # Reuse pattern từ verification.is_allowed == False branch.
                error_msg = str(e)
                tc_record.status = "denied"
                tc_record.error_message = f"Connector grant resolver error: {error_msg}"
                await self._repo.save_tool_call(tc_record)
                await self._idempotency.fail(idem_claim.claim_id, error_message=error_msg)
                await self._repo.append_event(
                    RunEventRecord(
                        run_id=req.run_id,
                        event_type="connector_grant.resolver_error",
                        payload={
                            "tool_call_id": req.tool_call_id,
                            "connector_id": connector_id,
                            "error": error_msg,
                        },
                    )
                )
                return GatewayExecutionResult(
                    tool_call_id=req.tool_call_id,
                    status="denied",
                    error_message=f"Execution of '{req.capability_id}' denied: connector grant verification failed",
                )

            verification = verify_connector_grant(
                grant,
                action=req.capability_id,
                tenant_id=req.workspace_id or "",
                principal=req.principal,
            )
            if not verification.is_allowed:
                tc_record.status = "denied"
                tc_record.error_message = f"Connector grant check failed: {verification.reason}"
                await self._repo.save_tool_call(tc_record)
                await self._idempotency.fail(idem_claim.claim_id, error_message=verification.reason)
                await self._repo.append_event(
                    RunEventRecord(
                        run_id=req.run_id,
                        event_type="connector_grant.denied",
                        payload={
                            "tool_call_id": req.tool_call_id,
                            "connector_id": connector_id,
                            "reason": verification.reason,
                        },
                    )
                )
                return GatewayExecutionResult(
                    tool_call_id=req.tool_call_id,
                    status="denied",
                    error_message=f"Execution of '{req.capability_id}' denied: {verification.reason}",
                )
            # Grant hợp lệ — cập nhật target_snapshot với thông tin grant
            target_snapshot.connection_account_id = (
                grant.metadata.get("connection_account_id") if grant else None
            )
            target_snapshot.credential_grant_version = grant.grant_id if grant else None

        # Bước 8.7: Ambient Governance Re-check ngay trước side effect (A4)
        is_ambient_ok, ambient_reason = verify_ambient_governance(req.context)
        if not is_ambient_ok:
            tc_record.status = "denied"
            tc_record.error_message = f"Ambient governance denied: {ambient_reason}"
            await self._repo.save_tool_call(tc_record)
            await self._idempotency.fail(idem_claim.claim_id, error_message=ambient_reason)
            await self._repo.append_event(
                RunEventRecord(
                    run_id=req.run_id,
                    event_type="governance.denied",
                    payload={"tool_call_id": req.tool_call_id, "reason": ambient_reason},
                )
            )
            return GatewayExecutionResult(
                tool_call_id=req.tool_call_id,
                status="denied",
                error_message=f"Execution of '{req.capability_id}' denied: {ambient_reason}",
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
            handler_ctx = (
                req.context.metadata if isinstance(req.context, InvocationContext) else req.context
            )
            if asyncio.iscoroutinefunction(handler):
                output = await handler(req.input_payload, handler_ctx)
            else:
                output = handler(req.input_payload, handler_ctx)

            # Persist status completed & audit
            tc_record.status = "completed"
            tc_record.output_payload = output
            tc_record.governance_state = gov_state.model_dump()
            await self._repo.save_tool_call(tc_record)
            await self._idempotency.complete(
                idem_claim.claim_id, result_payload=output, result_hash=compute_payload_hash(output)
            )

            # Audit event `tool.completed` chỉ lưu HASH của output, không lưu nội dung
            # thô — nhất quán với cách hệ thống audit `snapshot_hash`/`evidence_hashes`
            # (chỉ hash, không lưu content) và với `result_hash` idempotency ở trên.
            # Output thật (không redact) vẫn đi tới caller qua GatewayExecutionResult
            # (`output_payload`) — kênh hợp lệ để hiển thị/xử lý cho người dùng; chỉ
            # audit event log persist Postgres mới bị redact (Task 9).
            await self._repo.append_event(
                RunEventRecord(
                    run_id=req.run_id,
                    event_type="tool.completed",
                    payload={
                        "tool_call_id": req.tool_call_id,
                        "output_hash": compute_payload_hash(output),
                        "output_present": output is not None,
                    },
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
            await self._idempotency.fail(idem_claim.claim_id, error_message=str(exc))

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
