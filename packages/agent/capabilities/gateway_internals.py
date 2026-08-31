from __future__ import annotations

import logging
from typing import Any

from agent.capabilities.enablements import EnablementStore, assert_enabled_for_invocation
from agent.capabilities.idempotency import IdempotencyClaimService, IdempotencyOutcome
from agent.contracts.capability import CapabilitySpec
from agent.contracts.errors import TenancyUnresolvedError
from agent.contracts.invocation import InvocationContext
from agent.contracts.wait import WaitDescriptor, WaitKind
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk
from agent.runs.models import ComplianceDecisionPayload, RunApprovalRecord, RunEventRecord

logger = logging.getLogger(__name__)

__all__ = [
    "ApprovalGateDecider",
    "ComplianceAuditor",
    "EnablementValidator",
    "IdempotencyCoordinator",
    "InputValidator",
    "TenancyVerifier",
]


class TenancyVerifier:
    """Phụ trách kiểm tra tenancy fail-closed: workspace_id + principal phải hợp lệ
    cho capability có risk cao hoặc approval policy yêu cầu luôn duyệt."""

    def __init__(self, logger_: logging.Logger | None = None) -> None:
        self._logger = logger_ or logger

    async def verify(
        self,
        spec: CapabilitySpec,
        req: Any,  # GatewayExecutionRequest
    ) -> tuple[str, str]:
        """Verify tenancy for capability execution.

        Args:
            spec: CapabilitySpec with risk/approval_policy
            req: GatewayExecutionRequest with workspace_id, principal, context

        Returns:
            Tuple of (resolved_workspace_id, resolved_principal)

        Raises:
            TenancyUnresolvedError: nếu tenancy không đủ cho capability risk.
        """
        needs_tenancy = (
            spec.risk in (CapabilityRisk.HIGH, CapabilityRisk.CRITICAL, CapabilityRisk.MEDIUM)
            or spec.approval_policy == ApprovalPolicy.ALWAYS
        )

        resolved_workspace = req.workspace_id
        resolved_principal: str | None = req.principal

        # Fallback to context nếu req không chỉ định
        if not resolved_workspace:
            if isinstance(req.context, dict):
                resolved_workspace = req.context.get("workspace_id")
            elif hasattr(req.context, "workspace_id"):
                resolved_workspace = req.context.workspace_id
        if not resolved_principal:
            if isinstance(req.context, dict):
                resolved_principal = req.context.get("principal")
            elif hasattr(req.context, "principal"):
                resolved_principal = req.context.principal

        if needs_tenancy and (
            not resolved_workspace
            or str(resolved_workspace).strip() in ("", "default", "default_workspace")
            or not resolved_principal
            or str(resolved_principal).strip() in ("", "default")
        ):
            err_msg = (
                f"Execution of '{req.capability_id}' failed: tenancy unresolved "
                f"(workspace_id={resolved_workspace!r}, principal={resolved_principal!r})"
            )
            raise TenancyUnresolvedError(err_msg, details={"capability": req.capability_id})

        return resolved_workspace or "", resolved_principal or ""


class InputValidator:
    """Kiểm tra input payload khớp với spec schema (delegate cho CapabilityRegistry)."""

    def __init__(self, registry: Any) -> None:  # CapabilityRegistry
        self._registry = registry

    def validate(self, spec: CapabilitySpec, input_payload: dict[str, Any]) -> list[str]:
        """Validate input against spec schema.

        Returns:
            List of error messages (empty = valid).
        """
        return self._registry.validate_input(spec, input_payload)


class IdempotencyCoordinator:
    """Phối hợp idempotency: claim, cached_completed, in_progress.

    Wraps IdempotencyClaimService.try_claim() nguyên trạng (atomic claim,
    INSERT ... ON CONFLICT DO NOTHING ở tầng repository đảm bảo đúng 1
    worker thắng claim cho mỗi (run_id, capability_id, idempotency_key)).
    Không tự ý retry/chờ — caller tự quyết định dựa trên outcome trả về.
    """

    def __init__(self, idempotency_service: IdempotencyClaimService) -> None:
        self._idempotency = idempotency_service

    async def coordinate(
        self,
        run_id: str,
        tool_call_id: str,
        capability_id: str,
        idempotency_key: str,
        payload_hash: str,
    ) -> tuple[IdempotencyOutcome, Any]:  # (outcome, claim)
        """Attempt idempotency claim. Returns (outcome, claim) or raises."""
        return await self._idempotency.try_claim(
            run_id=run_id,
            tool_call_id=tool_call_id,
            capability_id=capability_id,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
        )

    def should_return_cached(self, outcome: IdempotencyOutcome) -> bool:
        """Check if should return cached result."""
        return outcome == IdempotencyOutcome.CACHED_COMPLETED

    def should_return_in_progress(self, outcome: IdempotencyOutcome) -> bool:
        """Check if should return in_progress."""
        return outcome == IdempotencyOutcome.IN_PROGRESS


class ComplianceAuditor:
    """Ghi nhận compliance audit decision và kiểm tra deployment status.

    Nếu `compliance_snapshot` trong context có status khác `APPROVED_FOR_USE`
    (deployment bị suspend/chưa duyệt), execution bị deny ngay — bất kể policy
    decision bên dưới thế nào — và một event `compliance.decision` với
    decision=DENY/reason_code=DEPLOYMENT_SUSPENDED vẫn được ghi lại (để phục vụ
    audit trail, không được bỏ qua dù early-return).
    """

    def __init__(self, repo: Any) -> None:  # RunRepository
        self._repo = repo

    def extract_compliance_snapshot(self, context: Any) -> dict[str, Any] | None:
        """Extract compliance_snapshot từ context (InvocationContext.metadata hoặc dict)."""
        if isinstance(context, InvocationContext):
            meta = context.metadata
        elif isinstance(context, dict):
            meta = context
        else:
            meta = {}

        return meta.get("compliance_snapshot") if isinstance(meta, dict) else None

    async def audit(
        self,
        context: Any,
        run_id: str,
        workspace_id: str,
        tool_call_id: str,
        checkpoint_ref: str,
        capability_id: str,
        current_decision: Any,  # PolicyDecision
        payload_hash: str,
    ) -> tuple[bool, Any | None, RunEventRecord | None]:
        # (should_continue, early_return_result_if_denied, pending_deny_event)
        """Audit compliance. Returns (should_continue, early_return_result, pending_deny_event).

        Nếu should_continue=False, early_return_result là GatewayExecutionResult
        cần trả về ngay (deployment suspended) VÀ pending_deny_event là
        RunEventRecord (`compliance.decision`, decision=DENY) mà CALLER phải tự
        append SAU KHI đã cập nhật tc_record.status/save_tool_call/idempotency.fail
        — KHÔNG được append ngay trong hàm này. Lý do: phải giữ đúng thứ tự
        side-effect gốc của gateway.py (tc_record save + idempotency.fail TRƯỚC
        event append) để một crash giữa hai bước không khiến lần retry sau
        (idempotency claim chưa bị fail) chạy lại audit() và ghi trùng event DENY
        thứ hai trước khi claim mới thực sự bị fail — vi phạm invariant
        durable/monotonic (không trùng lặp event) khi resume sau restart.

        Nhánh allow (should_continue=True, snapshot APPROVED_FOR_USE hoặc không
        có snapshot) không có bước tc_record/idempotency nào xen giữa, nên event
        được append trực tiếp trong hàm này như cũ (pending_deny_event=None).
        """
        # Import cục bộ để tránh circular import: gateway.py import module này ở
        # top-level, nên gateway_internals.py không được import gateway.py ở top-level.
        from agent.capabilities.gateway import GatewayExecutionResult

        ctx_meta = (
            context.metadata
            if isinstance(context, InvocationContext)
            else (context if isinstance(context, dict) else {})
        )
        snap = self.extract_compliance_snapshot(context)

        if not snap:
            return True, None, None

        snap_status = (
            snap.get("status") if isinstance(snap, dict) else getattr(snap, "status", None)
        )

        snapshot_hash = str(
            snap.get("snapshot_hash")
            if isinstance(snap, dict)
            else getattr(snap, "snapshot_hash", "")
        )
        policy_snapshot_hash = str(
            snap.get("policy_snapshot_hash")
            if isinstance(snap, dict)
            else getattr(snap, "policy_snapshot_hash", "")
        )
        deployment_id = str(
            snap.get("deployment_id")
            if isinstance(snap, dict)
            else getattr(snap, "deployment_id", "")
        )
        evidence_hashes = list(
            (
                snap.get("evidence_hashes")
                if isinstance(snap, dict)
                else getattr(snap, "evidence_hashes", [])
            )
            or []
        )
        rule_version_ids = list(
            (
                snap.get("rule_version_ids")
                if isinstance(snap, dict)
                else getattr(snap, "rule_version_ids", [])
            )
            or []
        )
        provider_model_ref = (
            snap.get("provider_profile_version")
            if isinstance(snap, dict)
            else getattr(snap, "provider_profile_version", None)
        )
        delegation_jti = ctx_meta.get("delegation_jti") or ctx_meta.get("_delegation_jti")

        # Deployment bị suspend/chưa duyệt: deny execution, vẫn ghi audit event.
        # LƯU Ý: nhánh DENY dùng công thức `str(provider_model_ref) or None` — KHÁC
        # nhánh ALLOW bên dưới (`str(x) if x else None`) — đây là hành vi gốc
        # nguyên trạng (str(None) == "None", một chuỗi truthy nên KHÔNG bị "or None"
        # rút gọn về None). Giữ nguyên byte-for-byte, không phải bug được sửa ở đây.
        if snap_status and snap_status != "APPROVED_FOR_USE":
            # KHÔNG append_event() ở đây — trả event về cho caller để caller tự
            # append SAU tc_record.save/idempotency.fail (giữ đúng thứ tự side
            # effect gốc, xem docstring của audit()).
            deny_event = RunEventRecord(
                run_id=run_id,
                event_type="compliance.decision",
                payload=ComplianceDecisionPayload(
                    run_id=run_id,
                    workspace_id=workspace_id,
                    deployment_id=deployment_id,
                    snapshot_hash=snapshot_hash,
                    policy_snapshot_hash=policy_snapshot_hash,
                    capability_id=capability_id,
                    tool_call_id=tool_call_id,
                    checkpoint_ref=checkpoint_ref or "",
                    decision="DENY",
                    reason_code="DEPLOYMENT_SUSPENDED",
                    rule_version_ids=rule_version_ids,
                    evidence_hashes=evidence_hashes,
                    provider_model_ref=str(
                        snap.get("provider_profile_version")
                        if isinstance(snap, dict)
                        else getattr(snap, "provider_profile_version", "")
                    )
                    or None,
                    delegation_jti=str(
                        ctx_meta.get("delegation_jti") or ctx_meta.get("_delegation_jti") or ""
                    )
                    or None,
                ).model_dump(),
            )
            return (
                False,
                GatewayExecutionResult(
                    tool_call_id=tool_call_id,
                    status="denied",
                    error_message="Execution denied: AI deployment is suspended or not approved",
                ),
                deny_event,
            )

        # Record compliance decision event (normal path)
        await self._repo.append_event(
            RunEventRecord(
                run_id=run_id,
                event_type="compliance.decision",
                payload=ComplianceDecisionPayload(
                    run_id=run_id,
                    workspace_id=workspace_id,
                    deployment_id=deployment_id,
                    snapshot_hash=snapshot_hash,
                    policy_snapshot_hash=policy_snapshot_hash,
                    capability_id=capability_id,
                    tool_call_id=tool_call_id,
                    checkpoint_ref=checkpoint_ref or "",
                    decision=current_decision.outcome.value,
                    reason_code=getattr(current_decision, "reason_code", None),
                    rule_version_ids=rule_version_ids,
                    evidence_hashes=evidence_hashes,
                    provider_model_ref=str(provider_model_ref) if provider_model_ref else None,
                    delegation_jti=str(delegation_jti) if delegation_jti else None,
                ).model_dump(),
            )
        )

        return True, None, None


class EnablementValidator:
    """Xác thực scoped capability enablement cho workspace/action_class/skill."""

    def __init__(self, enablement_store: EnablementStore) -> None:
        self._enablement_store = enablement_store

    def extract_action_class(self, spec: CapabilitySpec, context: Any) -> str:
        """Extract action_class from context or spec, default to 'R'."""
        if isinstance(context, dict):
            return context.get("action_class") or spec.metadata.get("action_class") or "R"
        elif hasattr(context, "action_class") and context.action_class:
            return context.action_class
        else:
            return str(spec.metadata.get("action_class") or getattr(spec, "action_class", "R"))

    def extract_skill_hash(self, context: Any) -> str | None:
        """Extract skill_hash from context."""
        if isinstance(context, dict):
            skill_hash = context.get("skill_hash") or context.get("definition_hash")
            if not skill_hash:
                pinned = context.get("pinned_skill") or context.get("skill_ref")
                if isinstance(pinned, dict):
                    skill_hash = pinned.get("definition_hash") or pinned.get("skill_hash")
                elif pinned is not None and hasattr(pinned, "definition_hash"):
                    skill_hash = pinned.definition_hash
            return skill_hash
        elif hasattr(context, "skill_hash"):
            return getattr(context, "skill_hash", None)
        return None

    async def validate(
        self,
        spec: CapabilitySpec,
        capability_id: str,
        workspace_id: str,
        context: Any,
    ) -> tuple[bool, str | None]:
        """Validate scoped enablement.

        Returns:
            (is_enabled, error_message) — if is_enabled=False, error_message is not None.
        """
        action_class = self.extract_action_class(spec, context)
        skill_hash = self.extract_skill_hash(context)

        is_enabled, enb_error = await assert_enabled_for_invocation(
            enablement_store=self._enablement_store,
            workspace_id=workspace_id,
            capability_id=capability_id,
            skill_hash=skill_hash,
            action_class=action_class,
            target_fingerprint="*",
        )

        return is_enabled, enb_error if not is_enabled else None


class ApprovalGateDecider:
    """Quyết định approval gate (Bước 8 pipeline gateway).

    REQUIRE_APPROVAL: tra cứu approval record đã có theo (tool_call_id,
    checkpoint_ref) — nếu chưa có/chưa approved/checkpoint lệch, tạo approval
    record mới (status=pending) + ghi event `approval.required`, rồi trả về
    wait descriptor. DENY: trả deny result. ALLOW (hoặc approval đã approved
    khớp checkpoint): should_execute=True, pipeline tiếp tục.

    LƯU Ý về thứ tự side effect: hàm `decide()` chỉ làm phần "tạo approval
    record + ghi event approval.required" (nếu cần) và KHÔNG tự lưu
    `tc_record`/gọi `idempotency.fail` — đây là những side effect gắn với
    tool_call ledger mà caller (gateway._execute_internal) vẫn tự làm SAU khi
    nhận kết quả từ decide(), giữ nguyên đúng thứ tự gốc: (a) approval
    record + event `approval.required` trước, (b) tc_record.status/
    governance_state + save_tool_call sau (nhánh waiting_approval); hoặc
    (a) tc_record.status=denied + save_tool_call rồi idempotency.fail
    (nhánh denied) — không có event nào cần append thêm ở nhánh deny.
    """

    def __init__(self, repo: Any) -> None:  # RunRepository
        self._repo = repo

    async def decide(
        self,
        run_id: str,
        tool_call_id: str,
        checkpoint_ref: str,
        capability_id: str,
        payload_hash: str,
        effective_outcome: Any,  # PolicyOutcome
        current_decision: Any,  # PolicyDecision
    ) -> tuple[bool, Any | None, Any | None]:
        # (should_execute, wait_result_if_waiting, deny_result_if_denied)
        """Quyết định approval gate.

        Returns:
            Tuple (should_execute, wait_result, deny_result). Nếu
            should_execute=False, đúng một trong wait_result/deny_result
            được set (GatewayExecutionResult).
        """
        # Import cục bộ để tránh circular import: gateway.py import module
        # này ở top-level, nên gateway_internals.py không được import
        # gateway.py ở top-level.
        from agent.capabilities.gateway import GatewayExecutionResult
        from agent.governance.contracts import PolicyOutcome

        if effective_outcome == PolicyOutcome.REQUIRE_APPROVAL:
            # Kiểm tra xem có approval record đã duyệt chưa. Exact invocation
            # matching: khớp cả tool_call_id và checkpoint_ref.
            approval = await self._repo.get_approval_by_tool_call(tool_call_id)
            checkpoint_mismatch = bool(
                approval
                and checkpoint_ref
                and approval.checkpoint_ref
                and approval.checkpoint_ref != checkpoint_ref
            )
            if not approval or approval.status != "approved" or checkpoint_mismatch:
                if not approval or checkpoint_mismatch:
                    appr_id = f"appr_{run_id}_{tool_call_id}"
                    req_model = current_decision.requirement
                    req_dict = (
                        req_model.model_dump()
                        if req_model is not None and hasattr(req_model, "model_dump")
                        else {"kind": "role_approval", "role": "founder"}
                    )
                    approval = RunApprovalRecord(
                        approval_id=appr_id,
                        run_id=run_id,
                        tool_call_id=tool_call_id,
                        checkpoint_ref=checkpoint_ref,
                        status="pending",
                        action=capability_id,
                        subject=f"Approval needed for {capability_id} (payload_hash: {payload_hash[:8]})",
                        requirement=req_dict,
                    )
                    await self._repo.create_approval(approval)
                    await self._repo.append_event(
                        RunEventRecord(
                            run_id=run_id,
                            event_type="approval.required",
                            payload={"approval_id": appr_id, "tool_call_id": tool_call_id},
                        )
                    )

                wait = WaitDescriptor(
                    kind=WaitKind.APPROVAL,
                    reason=f"Action '{capability_id}' requires human approval",
                    checkpoint_ref=checkpoint_ref,
                    related_ref=approval.approval_id,
                    resume_trigger="approval.decided",
                )

                return (
                    False,
                    GatewayExecutionResult(
                        tool_call_id=tool_call_id,
                        status="waiting_approval",
                        wait_descriptor=wait,
                    ),
                    None,
                )

        if effective_outcome == PolicyOutcome.DENY:
            return (
                False,
                None,
                GatewayExecutionResult(
                    tool_call_id=tool_call_id,
                    status="denied",
                    error_message=f"Execution of '{capability_id}' denied by policy",
                ),
            )

        return True, None, None
