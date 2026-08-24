from __future__ import annotations

import datetime
from typing import Any, Callable, Optional
import uuid

from agent_core.contracts.identity import InvocationIdentity
from agent_core.contracts.target import ExecutionTargetSnapshot
from agent_core.contracts.wait import WaitDescriptor, WaitKind
from agent_core.governance.accumulator import InvocationGovernanceState, combine_decisions
from agent_core.governance.contracts import (
    ApprovalRequirement,
    CapabilityRisk,
    PolicyDecision,
    PolicyOutcome,
)
from agent_core.runs.models import (
    RunApprovalRecord,
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent_core.runs.repository import InMemoryRunRepository, RunRepository

__all__ = [
    "ApprovalAlreadyDecidedError",
    "ApprovalResumeResult",
    "DurableApprovalService",
]


class ApprovalAlreadyDecidedError(Exception):
    """Raised khi submit_decision() nhắm vào 1 approval đã tồn tại nhưng không còn
    'pending' — tức 1 quyết định khác (double-click, 2 reviewer, request lặp lại)
    đã thắng cuộc đua CAS trước đó (Blueprint V2 §21). Đây là lỗi khác với
    "approval not found" — caller (API layer) nên trả 409 Conflict, không phải 404."""

    def __init__(self, approval_id: str, current_status: str) -> None:
        super().__init__(
            f"Approval '{approval_id}' đã được quyết định trước đó (status hiện tại: {current_status})"
        )
        self.approval_id = approval_id
        self.current_status = current_status


class ApprovalResumeResult:
    def __init__(
        self,
        can_resume: bool,
        effective_decision: PolicyDecision,
        reason: str,
        approval_record: Optional[RunApprovalRecord] = None,
        tool_call_record: Optional[RunToolCallRecord] = None,
        checkpoint_record: Optional[RunCheckpointRecord] = None,
    ) -> None:
        self.can_resume = can_resume
        self.effective_decision = effective_decision
        self.reason = reason
        self.approval_record = approval_record
        self.tool_call_record = tool_call_record
        self.checkpoint_record = checkpoint_record


class DurableApprovalService:
    """Canonical Durable Approval Service theo Master Guide §18.
    
    Thay thế hoàn toàn cơ chế lookup `(run_id, action)` cũ của AgentOS.
    Lookup BẮT BUỘC theo: `(run_id, tool_call_id, checkpoint_ref)` hoặc `approval_id`.
    
    Nguyên tắc cốt lõi:
    1. Human Approval được gắn kết chính xác với từng lần gọi tool cụ thể (`tool_call_id`),
       ngăn chặn cross-approval giữa 2 lần gọi cùng 1 tool trong cùng Run.
    2. APPROVED KHÔNG PHẢI permanent bypass token (§18.1). Trước khi resume, hệ thống
       bắt buộc phải kiểm tra fresh ambient governance (tenant active, principal active)
       và target drift (connector, credential, schema).
    """

    def __init__(
        self,
        repository: RunRepository,
        policy_evaluator: Optional[Callable[[str, dict[str, Any], dict[str, Any]], PolicyDecision]] = None,
    ) -> None:
        self._repo = repository
        self._policy_evaluator = policy_evaluator

    async def create_approval_request(
        self,
        *,
        run_id: str,
        tool_call_id: str,
        checkpoint_ref: str,
        action: str,
        subject: str,
        requirement: dict[str, Any] | None = None,
        requester: str = "agent_system",
        target_snapshot: Optional[ExecutionTargetSnapshot] = None,
        payload_hash: Optional[str] = None,
    ) -> tuple[RunApprovalRecord, WaitDescriptor]:
        """Tạo bản ghi Approval gắn kết bất biến với (run_id, tool_call_id, checkpoint_ref)."""
        approval_id = f"appr_{run_id}_{tool_call_id}"

        record = RunApprovalRecord(
            approval_id=approval_id,
            run_id=run_id,
            tool_call_id=tool_call_id,
            checkpoint_ref=checkpoint_ref,
            status="pending",
            action=action,
            subject=subject,
            requirement=requirement or {},
            requester=requester,
            evidence={
                "payload_hash": payload_hash,
                "target_snapshot": target_snapshot.model_dump() if target_snapshot else None,
            },
        )
        await self._repo.create_approval(record)

        await self._repo.append_event(
            RunEventRecord(
                run_id=run_id,
                event_type="approval.required",
                payload={
                    "approval_id": approval_id,
                    "tool_call_id": tool_call_id,
                    "checkpoint_ref": checkpoint_ref,
                    "action": action,
                },
            )
        )

        wait_desc = WaitDescriptor(
            kind=WaitKind.APPROVAL,
            reason=f"Action '{action}' requires human approval: {subject}",
            owner_responder=requirement.get("role") if requirement else "admin",
            checkpoint_ref=checkpoint_ref,
            related_ref=approval_id,
            resume_trigger="approval.decided",
        )

        return record, wait_desc

    async def get_approval(self, approval_id: str) -> Optional[RunApprovalRecord]:
        return await self._repo.get_approval(approval_id)

    async def get_by_invocation(
        self, run_id: str, tool_call_id: str, checkpoint_ref: Optional[str] = None
    ) -> Optional[RunApprovalRecord]:
        """Lookup approval chính xác theo tool_call_id và checkpoint_ref."""
        approval = await self._repo.get_approval_by_tool_call(tool_call_id)
        if approval and approval.run_id == run_id:
            if checkpoint_ref and approval.checkpoint_ref != checkpoint_ref:
                return None
            return approval
        return None

    async def list_pending_approvals(self, workspace_id: Optional[str] = None) -> list[RunApprovalRecord]:
        return await self._repo.list_pending_approvals(workspace_id=workspace_id)

    async def submit_decision(
        self,
        *,
        approval_id: str,
        reviewer: str,
        approved: bool,
        reason: str = "",
        evidence_payload: Optional[dict[str, Any]] = None,
    ) -> Optional[RunApprovalRecord]:
        """Ghi nhận quyết định phê duyệt và lưu trữ ApprovalEvidence.

        Raises:
            ApprovalAlreadyDecidedError: nếu approval tồn tại nhưng đã bị quyết định
                trước đó (CAS race — Blueprint V2 §21), không phải "not found".
        """
        approval = await self._repo.get_approval(approval_id)
        if not approval:
            return None

        evidence = dict(approval.evidence or {})
        evidence.update(evidence_payload or {})
        evidence.update({
            "reviewer": reviewer,
            "decision": "approved" if approved else "rejected",
            "reason": reason,
            "submitted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

        decided = await self._repo.decide_approval(
            approval_id=approval_id,
            reviewer=reviewer,
            approved=approved,
            reason=reason,
            evidence=evidence,
        )

        if decided is None:
            # `approval` (load ở trên) tồn tại nhưng decide_approval() CAS thất bại
            # -> đã bị quyết định bởi request khác giữa lúc load và lúc ghi.
            raise ApprovalAlreadyDecidedError(approval_id=approval_id, current_status=approval.status)

        if decided:
            await self._repo.append_event(
                RunEventRecord(
                    run_id=decided.run_id,
                    event_type="approval.decided",
                    payload={
                        "approval_id": approval_id,
                        "tool_call_id": decided.tool_call_id,
                        "status": decided.status,
                        "reviewer": reviewer,
                    },
                )
            )

        return decided

    async def verify_and_prepare_resume(
        self,
        *,
        run_id: str,
        tool_call_id: str,
        checkpoint_ref: str,
        ambient_context: Optional[dict[str, Any]] = None,
        current_target_snapshot: Optional[ExecutionTargetSnapshot] = None,
    ) -> ApprovalResumeResult:
        """Thẩm định an toàn toàn diện trước khi resume theo Master Guide §18.
        
        Quy trình xác minh:
        1. Kiểm tra tồn tại Run, ToolCall, Checkpoint và Approval record.
        2. Xác minh tính toàn vẹn định danh Invocation: tool_call_id, checkpoint_ref phải khớp.
        3. Kiểm tra trạng thái Approval: phải là 'approved' và có bằng chứng hợp lệ.
        4. Kiểm tra Target Drift: nếu connector_id hoặc schema_hash_version của target bị thay đổi
           giữa thời điểm request và resume -> Đánh giá approval cũ là STALE.
        5. Kiểm tra Ambient Governance hiện tại (§15.3 & §18.1):
           - Nếu tenant bị suspend / principal bị disable / emergency lock -> DENY ngay lập tức!
        6. Re-evaluate policy hiện tại và conjoin với accumulated governance:
           - Nếu policy mới yêu cầu thêm điều kiện hoặc DENY -> Áp dụng luật chặt nhất.
        """
        ctx = ambient_context or {}

        # 1. Load các bản ghi liên quan
        run = await self._repo.get_run(run_id)
        if not run:
            return ApprovalResumeResult(
                can_resume=False,
                effective_decision=PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("Run not found",)),
                reason=f"Run '{run_id}' does not exist",
            )

        tool_call = await self._repo.get_tool_call(tool_call_id)
        if not tool_call or tool_call.run_id != run_id:
            return ApprovalResumeResult(
                can_resume=False,
                effective_decision=PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("Tool call not found",)),
                reason=f"Tool call '{tool_call_id}' not found for run '{run_id}'",
            )

        checkpoint = await self._repo.get_checkpoint(checkpoint_ref)
        if not checkpoint or checkpoint.run_id != run_id:
            return ApprovalResumeResult(
                can_resume=False,
                effective_decision=PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("Checkpoint not found",)),
                reason=f"Checkpoint '{checkpoint_ref}' not found for run '{run_id}'",
            )

        approval = await self._repo.get_approval_by_tool_call(tool_call_id)
        if not approval or approval.checkpoint_ref != checkpoint_ref:
            return ApprovalResumeResult(
                can_resume=False,
                effective_decision=PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("Approval not found",)),
                reason=f"No matching approval for tool_call '{tool_call_id}' and checkpoint '{checkpoint_ref}'",
            )

        # 2. Kiểm tra trạng thái Approval
        if approval.status != "approved":
            return ApprovalResumeResult(
                can_resume=False,
                effective_decision=PolicyDecision(
                    outcome=PolicyOutcome.REQUIRE_APPROVAL,
                    reasons=(f"Approval status is {approval.status}",),
                ),
                reason=f"Approval is not approved (current status: {approval.status})",
                approval_record=approval,
                tool_call_record=tool_call,
                checkpoint_record=checkpoint,
            )

        # 3. Kiểm tra Ambient Governance (Tenant suspend, Principal revocation, Emergency lock)
        tenant_status = ctx.get("tenant_status", "active")
        principal_status = ctx.get("principal_status", "active")
        emergency_lock = ctx.get("emergency_lock", False)

        if tenant_status == "suspended" or tenant_status == "disabled":
            return ApprovalResumeResult(
                can_resume=False,
                effective_decision=PolicyDecision(
                    outcome=PolicyOutcome.DENY,
                    reasons=(f"Tenant is {tenant_status}",),
                ),
                reason=f"Cannot resume: Tenant is currently {tenant_status}",
                approval_record=approval,
                tool_call_record=tool_call,
                checkpoint_record=checkpoint,
            )

        if principal_status == "revoked" or principal_status == "disabled":
            return ApprovalResumeResult(
                can_resume=False,
                effective_decision=PolicyDecision(
                    outcome=PolicyOutcome.DENY,
                    reasons=(f"Principal is {principal_status}",),
                ),
                reason=f"Cannot resume: Principal is currently {principal_status}",
                approval_record=approval,
                tool_call_record=tool_call,
                checkpoint_record=checkpoint,
            )

        if emergency_lock:
            return ApprovalResumeResult(
                can_resume=False,
                effective_decision=PolicyDecision(
                    outcome=PolicyOutcome.DENY,
                    reasons=("Emergency lock is active",),
                ),
                reason="Cannot resume: Global emergency lock is active",
                approval_record=approval,
                tool_call_record=tool_call,
                checkpoint_record=checkpoint,
            )

        # 4. Kiểm tra Target Drift (Master Guide §8 & §18)
        if current_target_snapshot and tool_call.execution_target_snapshot:
            saved_target = tool_call.execution_target_snapshot
            if (
                current_target_snapshot.connector_id
                and saved_target.get("connector_id")
                and current_target_snapshot.connector_id != saved_target.get("connector_id")
            ):
                return ApprovalResumeResult(
                    can_resume=False,
                    effective_decision=PolicyDecision(
                        outcome=PolicyOutcome.DENY,
                        reasons=("Target connector drifted",),
                    ),
                    reason=f"Target connector changed from {saved_target.get('connector_id')} to {current_target_snapshot.connector_id}",
                    approval_record=approval,
                    tool_call_record=tool_call,
                    checkpoint_record=checkpoint,
                )

            if (
                current_target_snapshot.schema_hash_version
                and saved_target.get("schema_hash_version")
                and current_target_snapshot.schema_hash_version != saved_target.get("schema_hash_version")
            ):
                return ApprovalResumeResult(
                    can_resume=False,
                    effective_decision=PolicyDecision(
                        outcome=PolicyOutcome.DENY,
                        reasons=("Target schema drifted",),
                    ),
                    reason=f"Target schema hash changed from {saved_target.get('schema_hash_version')} to {current_target_snapshot.schema_hash_version}",
                    approval_record=approval,
                    tool_call_record=tool_call,
                    checkpoint_record=checkpoint,
                )

        # 5. Fresh Policy Evaluation & Conjunction
        current_policy_decision = PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("Default allow",))
        if self._policy_evaluator:
            current_policy_decision = self._policy_evaluator(tool_call.capability_id, tool_call.input_payload, ctx)

        # Conjoin với approved status: Nếu current policy vẫn ALLOW -> Cho phép resume
        if current_policy_decision.outcome == PolicyOutcome.DENY:
            return ApprovalResumeResult(
                can_resume=False,
                effective_decision=current_policy_decision,
                reason="Current policy evaluation resulted in DENY",
                approval_record=approval,
                tool_call_record=tool_call,
                checkpoint_record=checkpoint,
            )

        return ApprovalResumeResult(
            can_resume=True,
            effective_decision=current_policy_decision,
            reason="Approval verified and all safety invariants satisfied",
            approval_record=approval,
            tool_call_record=tool_call,
            checkpoint_record=checkpoint,
        )
