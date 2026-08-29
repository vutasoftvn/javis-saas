from __future__ import annotations

import asyncio

import pytest

from agent.contracts.target import ExecutionTargetSnapshot
from agent.contracts.wait import WaitKind
from agent.governance.contracts import CapabilityRisk, PolicyDecision, PolicyOutcome
from agent.capabilities.approval_service import (
    ApprovalAlreadyDecidedError,
    DurableApprovalService,
)
from agent.runs.models import (
    RunApprovalRecord,
    RunCheckpointRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent.runs.repository import InMemoryRunRepository


@pytest.fixture
def approval_setup():
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repository=repo)
    return service, repo


@pytest.mark.asyncio
async def test_approval_binding_specifically_to_tool_call_id_and_checkpoint(approval_setup):
    service, repo = approval_setup

    # Tạo Run, Checkpoint, ToolCall
    run = RunRecord(run_id="run_appr_bind_1", principal="alice", root_executable_id="agent_1")
    await repo.create_run(run)

    ckpt = RunCheckpointRecord(
        checkpoint_ref="ckpt_100",
        run_id="run_appr_bind_1",
        sequence_no=1,
        step_name="step_payout",
        serialized_state={"amount": 5000},
    )
    await repo.save_checkpoint(ckpt)

    tc = RunToolCallRecord(
        tool_call_id="call_payout_100",
        run_id="run_appr_bind_1",
        checkpoint_ref="ckpt_100",
        capability_id="finance.payout.send",
        payload_hash="hash_payout_100",
        input_payload={"amount": 5000},
        status="waiting_approval",
    )
    await repo.save_tool_call(tc)

    # Tạo approval
    appr, wait = await service.create_approval_request(
        run_id="run_appr_bind_1",
        tool_call_id="call_payout_100",
        checkpoint_ref="ckpt_100",
        action="finance.payout.send",
        subject="Payout $5000 to Acme",
        requirement={"kind": "role_approval", "role": "founder"},
        payload_hash="hash_payout_100",
    )

    assert appr.approval_id == "appr_run_appr_bind_1_call_payout_100"
    assert wait.kind == WaitKind.APPROVAL
    assert wait.checkpoint_ref == "ckpt_100"

    # Lookup chính xác theo invocation
    found = await service.get_by_invocation(
        run_id="run_appr_bind_1",
        tool_call_id="call_payout_100",
        checkpoint_ref="ckpt_100",
    )
    assert found is not None
    assert found.approval_id == appr.approval_id

    # Lookup sai checkpoint_ref -> None
    wrong_ckpt = await service.get_by_invocation(
        run_id="run_appr_bind_1",
        tool_call_id="call_payout_100",
        checkpoint_ref="ckpt_999",
    )
    assert wrong_ckpt is None


@pytest.mark.asyncio
async def test_same_tool_twice_creates_independent_approvals(approval_setup):
    """Test case G (Same tool twice): 2 lần gọi cùng tool `send_email` trong cùng Run
    tạo 2 approval records độc lập; duyệt lần 1 không làm lần 2 tự động được duyệt.
    """
    service, repo = approval_setup

    run = RunRecord(run_id="run_twice_appr", principal="bob", root_executable_id="marketing_agent")
    await repo.create_run(run)

    # Tool call 1
    tc1 = RunToolCallRecord(
        tool_call_id="call_email_1",
        run_id="run_twice_appr",
        capability_id="email.send",
        payload_hash="hash_email_1",
        input_payload={"to": "user1@example.com"},
        status="waiting_approval",
    )
    await repo.save_tool_call(tc1)

    # Tool call 2
    tc2 = RunToolCallRecord(
        tool_call_id="call_email_2",
        run_id="run_twice_appr",
        capability_id="email.send",
        payload_hash="hash_email_2",
        input_payload={"to": "user2@example.com"},
        status="waiting_approval",
    )
    await repo.save_tool_call(tc2)

    appr1, _ = await service.create_approval_request(
        run_id="run_twice_appr",
        tool_call_id="call_email_1",
        checkpoint_ref="ckpt_email_1",
        action="email.send",
        subject="Email 1",
    )
    appr2, _ = await service.create_approval_request(
        run_id="run_twice_appr",
        tool_call_id="call_email_2",
        checkpoint_ref="ckpt_email_2",
        action="email.send",
        subject="Email 2",
    )

    assert appr1.approval_id != appr2.approval_id

    # Reviewer duyệt appr1
    await service.submit_decision(
        approval_id=appr1.approval_id,
        reviewer="manager_1",
        approved=True,
        reason="Approved email 1",
    )

    # Check appr1 đã approved
    appr1_refreshed = await service.get_approval(appr1.approval_id)
    assert appr1_refreshed.status == "approved"

    # Check appr2 VẪN LÀ pending (không bị cross-contamination)
    appr2_refreshed = await service.get_approval(appr2.approval_id)
    assert appr2_refreshed.status == "pending"


@pytest.mark.asyncio
async def test_approved_is_not_permanent_bypass_tenant_suspended_denies_resume(approval_setup):
    """Test Master Guide §18.1 (Case C): Đã được human approve, nhưng trước khi resume
    tenant bị suspend hoặc principal bị revoke -> verify_and_prepare_resume phải DENY.
    """
    service, repo = approval_setup

    run = RunRecord(run_id="run_perm_bypass", principal="finance_agent", root_executable_id="payout_agent")
    await repo.create_run(run)

    ckpt = RunCheckpointRecord(
        checkpoint_ref="ckpt_payout_secure",
        run_id="run_perm_bypass",
        sequence_no=1,
        step_name="payout_step",
        serialized_state={"amount": 10000},
    )
    await repo.save_checkpoint(ckpt)

    tc = RunToolCallRecord(
        tool_call_id="call_payout_secure_1",
        run_id="run_perm_bypass",
        checkpoint_ref="ckpt_payout_secure",
        capability_id="bank.payout.send",
        payload_hash="hash_payout_sec",
        input_payload={"amount": 10000},
        status="waiting_approval",
    )
    await repo.save_tool_call(tc)

    appr, _ = await service.create_approval_request(
        run_id="run_perm_bypass",
        tool_call_id="call_payout_secure_1",
        checkpoint_ref="ckpt_payout_secure",
        action="bank.payout.send",
        subject="Payout $10,000",
    )

    # Human reviewer approves
    await service.submit_decision(
        approval_id=appr.approval_id,
        reviewer="founder_1",
        approved=True,
        reason="Approved PO-9988",
    )

    # 1. Thẩm định khi Tenant active -> PASS
    res_active = await service.verify_and_prepare_resume(
        run_id="run_perm_bypass",
        tool_call_id="call_payout_secure_1",
        checkpoint_ref="ckpt_payout_secure",
        ambient_context={"tenant_status": "active", "principal_status": "active"},
    )
    assert res_active.can_resume is True

    # 2. Thẩm định khi Tenant bị SUSPEND trước khi resume -> DENY ngay lập tức!
    res_suspended = await service.verify_and_prepare_resume(
        run_id="run_perm_bypass",
        tool_call_id="call_payout_secure_1",
        checkpoint_ref="ckpt_payout_secure",
        ambient_context={"tenant_status": "suspended", "principal_status": "active"},
    )
    assert res_suspended.can_resume is False
    assert res_suspended.effective_decision.outcome == PolicyOutcome.DENY
    assert "suspended" in res_suspended.reason.lower()

    # 3. Thẩm định khi Principal bị REVOKED -> DENY
    res_revoked = await service.verify_and_prepare_resume(
        run_id="run_perm_bypass",
        tool_call_id="call_payout_secure_1",
        checkpoint_ref="ckpt_payout_secure",
        ambient_context={"tenant_status": "active", "principal_status": "revoked"},
    )
    assert res_revoked.can_resume is False
    assert res_revoked.effective_decision.outcome == PolicyOutcome.DENY


@pytest.mark.asyncio
async def test_target_drift_detects_connector_change_and_blocks_resume(approval_setup):
    """Test Master Guide §8 & §18 (Case H): Cùng payload nhưng connector đích thay đổi -> Stale approval."""
    service, repo = approval_setup

    run = RunRecord(run_id="run_target_drift", principal="user1", root_executable_id="agent_1")
    await repo.create_run(run)

    initial_target = ExecutionTargetSnapshot(
        capability_id="crm.customer.update",
        connector_id="salesforce_prod_connector_v1",
        schema_hash_version="schema_v1_hash",
    )

    ckpt = RunCheckpointRecord(
        checkpoint_ref="ckpt_crm_1",
        run_id="run_target_drift",
        sequence_no=1,
        step_name="crm_update",
        serialized_state={},
    )
    await repo.save_checkpoint(ckpt)

    tc = RunToolCallRecord(
        tool_call_id="call_crm_update_1",
        run_id="run_target_drift",
        checkpoint_ref="ckpt_crm_1",
        capability_id="crm.customer.update",
        payload_hash="hash_crm_payload",
        execution_target_snapshot=initial_target.model_dump(),
        status="waiting_approval",
    )
    await repo.save_tool_call(tc)

    appr, _ = await service.create_approval_request(
        run_id="run_target_drift",
        tool_call_id="call_crm_update_1",
        checkpoint_ref="ckpt_crm_1",
        action="crm.customer.update",
        subject="Update customer status",
        target_snapshot=initial_target,
    )

    await service.submit_decision(
        approval_id=appr.approval_id,
        reviewer="sales_lead",
        approved=True,
    )

    # Khi target snapshot không đổi -> PASS
    res_same = await service.verify_and_prepare_resume(
        run_id="run_target_drift",
        tool_call_id="call_crm_update_1",
        checkpoint_ref="ckpt_crm_1",
        current_target_snapshot=initial_target,
    )
    assert res_same.can_resume is True

    # Khi connector bị đổi sang connector khác (vd Hubspot hoặc tài khoản sandbox khác) -> Target Drift -> BLOCKED
    drifted_target = ExecutionTargetSnapshot(
        capability_id="crm.customer.update",
        connector_id="hubspot_staging_connector_v2",
        schema_hash_version="schema_v1_hash",
    )
    res_drifted = await service.verify_and_prepare_resume(
        run_id="run_target_drift",
        tool_call_id="call_crm_update_1",
        checkpoint_ref="ckpt_crm_1",
        current_target_snapshot=drifted_target,
    )
    assert res_drifted.can_resume is False
    assert "Target connector changed" in res_drifted.reason


@pytest.mark.asyncio
async def test_decide_approval_is_atomic_cas_exactly_one_decision_wins(approval_setup):
    """Blueprint V2 §21: dispatch 2 quyết định cùng lúc qua asyncio.gather() cho cùng
    1 approval_id — đúng 1 cái thắng CAS (status chuyển từ 'pending'), cái còn lại
    phải nhận ApprovalAlreadyDecidedError, không được âm thầm ghi đè.

    Lưu ý: với InMemoryRunRepository (không có await point nào giữa check và write
    trong decide_approval), asyncio.gather() ở đây không tạo ra interleaving thật —
    coroutine đầu tiên chạy hết trước khi coroutine thứ hai bắt đầu. Test này verify
    đúng outcome invariant (đúng 1 winner, 1 conflict, không silent overwrite), nhưng
    KHÔNG chứng minh an toàn dưới concurrency thật giữa nhiều connection/process —
    việc đó cần chạy lại với PostgresRunRepository trên Postgres thật (chưa có trong
    môi trường này, xem ghi chú Wave 1 C.2 trong COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN)."""
    service, repo = approval_setup

    approval = RunApprovalRecord(
        approval_id="appr_cas_race_1",
        run_id="run_cas_race_1",
        tool_call_id="call_cas_race_1",
        checkpoint_ref="ckpt_cas_race_1",
        status="pending",
        action="finance.payout.execute",
        subject="Race condition test",
    )
    await repo.create_approval(approval)

    results = await asyncio.gather(
        service.submit_decision(approval_id="appr_cas_race_1", reviewer="alice", approved=True),
        service.submit_decision(approval_id="appr_cas_race_1", reviewer="bob", approved=False),
        return_exceptions=True,
    )

    successes = [r for r in results if isinstance(r, RunApprovalRecord)]
    conflicts = [r for r in results if isinstance(r, ApprovalAlreadyDecidedError)]

    assert len(successes) == 1
    assert len(conflicts) == 1

    final = await repo.get_approval("appr_cas_race_1")
    assert final.status in ("approved", "denied")
    assert final.decision_version == 1
    # Người thắng cuộc đua phải là người quyết định trạng thái cuối cùng, nhất quán
    assert final.reviewer == successes[0].reviewer


@pytest.mark.asyncio
async def test_decide_approval_twice_sequentially_raises_already_decided(approval_setup):
    service, repo = approval_setup

    approval = RunApprovalRecord(
        approval_id="appr_double_decide_1",
        run_id="run_double_decide_1",
        tool_call_id="call_double_decide_1",
        checkpoint_ref="ckpt_double_decide_1",
        status="pending",
        action="finance.payout.execute",
        subject="Double-decide test",
    )
    await repo.create_approval(approval)

    first = await service.submit_decision(approval_id="appr_double_decide_1", reviewer="alice", approved=True)
    assert first.status == "approved"

    with pytest.raises(ApprovalAlreadyDecidedError):
        await service.submit_decision(approval_id="appr_double_decide_1", reviewer="bob", approved=False)
