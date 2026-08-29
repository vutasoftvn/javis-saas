from __future__ import annotations

import pytest

from agent.contracts.target import ExecutionTargetSnapshot
from agent.contracts.wait import WaitKind
from agent.governance.contracts import PolicyOutcome
from agent.capabilities.approval_service import DurableApprovalService
from agent.runs.models import (
    RunCheckpointRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_case_c_current_revocation():
    """Case C: Current revocation (Master Guide §41.1 Case C).
    
    Kịch bản:
    1. Run được human reviewer phê duyệt thành công.
    2. Trước khi resume, Principal bị thu hồi quyền (revoked) hoặc Tenant bị tạm ngưng (suspended).
    3. Resume được kích hoạt.
    4. Invariant: Current governance gate BẮT BUỘC thắng (DENY), chặn resume ngay lập tức,
       chứng minh APPROVED không phải permanent bypass token.
    """
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repository=repo)

    run_id = "run_case_c"
    tool_call_id = "call_payout_c"
    checkpoint_ref = "ckpt_payout_c"

    # Setup database records
    await repo.create_run(RunRecord(run_id=run_id, principal="contractor_1", root_executable_id="agent_c"))
    await repo.save_checkpoint(RunCheckpointRecord(
        checkpoint_ref=checkpoint_ref,
        run_id=run_id,
        sequence_no=1,
        step_name="payout_step",
        serialized_state={"amount": 25000},
    ))
    await repo.save_tool_call(RunToolCallRecord(
        tool_call_id=tool_call_id,
        run_id=run_id,
        checkpoint_ref=checkpoint_ref,
        capability_id="banking.wire.execute",
        payload_hash="hash_wire_25000",
        input_payload={"amount": 25000},
        status="waiting_approval",
    ))

    appr, _ = await service.create_approval_request(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        action="banking.wire.execute",
        subject="Wire $25,000 to vendor",
    )

    # Reviewer approves
    await service.submit_decision(
        approval_id=appr.approval_id,
        reviewer="cfo_user",
        approved=True,
        reason="Verified wire instructions",
    )

    # 1. Khi Principal bị Revoke quyền
    res_revoked = await service.verify_and_prepare_resume(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        ambient_context={"principal_status": "revoked"},
    )
    assert res_revoked.can_resume is False
    assert res_revoked.effective_decision.outcome == PolicyOutcome.DENY
    assert "Principal is currently revoked" in res_revoked.reason

    # 2. Khi Tenant bị Suspend
    res_suspended = await service.verify_and_prepare_resume(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        ambient_context={"tenant_status": "suspended"},
    )
    assert res_suspended.can_resume is False
    assert res_suspended.effective_decision.outcome == PolicyOutcome.DENY
    assert "Tenant is currently suspended" in res_suspended.reason

    # 3. Khi Emergency Lock kích hoạt
    res_lock = await service.verify_and_prepare_resume(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        ambient_context={"emergency_lock": True},
    )
    assert res_lock.can_resume is False
    assert res_lock.effective_decision.outcome == PolicyOutcome.DENY
    assert "emergency lock" in res_lock.reason.lower()

