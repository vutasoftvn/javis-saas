from __future__ import annotations

import pytest
from agent.contracts.run import RunStatus
from agent.governance.contracts import ExecutionMode
from agent.runs.models import (
    RunApprovalRecord,
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent.runs.repository import InMemoryRunRepository, RunRepository


@pytest.fixture
def in_memory_repo() -> RunRepository:
    return InMemoryRunRepository()


@pytest.mark.asyncio
async def test_run_crud_lifecycle(in_memory_repo: RunRepository):
    run = RunRecord(
        run_id="run_test_1",
        principal="founder_1",
        root_executable_id="finance_agent",
        workspace_id="ws_main",
        input_payload={"period": "Q3-2026"},
    )
    created = await in_memory_repo.create_run(run)
    assert created.run_id == "run_test_1"
    assert created.status == RunStatus.PENDING

    fetched = await in_memory_repo.get_run("run_test_1")
    assert fetched is not None
    assert fetched.principal == "founder_1"
    assert fetched.input_payload == {"period": "Q3-2026"}

    updated = await in_memory_repo.update_run_status(
        "run_test_1",
        status=RunStatus.COMPLETED,
        final_output={"summary": "processed 10 invoices"},
    )
    assert updated is not None
    assert updated.status == RunStatus.COMPLETED
    assert updated.final_output == {"summary": "processed 10 invoices"}
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_checkpoint_sequential_persistence(in_memory_repo: RunRepository):
    ckpt1 = RunCheckpointRecord(
        checkpoint_ref="ckpt_1",
        run_id="run_1",
        sequence_no=1,
        step_name="fetch_invoices",
        serialized_state={"invoices": [1, 2, 3]},
    )
    ckpt2 = RunCheckpointRecord(
        checkpoint_ref="ckpt_2",
        run_id="run_1",
        sequence_no=2,
        step_name="calculate_tax",
        serialized_state={"invoices": [1, 2, 3], "tax": 450},
    )

    await in_memory_repo.save_checkpoint(ckpt1)
    await in_memory_repo.save_checkpoint(ckpt2)

    latest = await in_memory_repo.get_latest_checkpoint("run_1")
    assert latest is not None
    assert latest.checkpoint_ref == "ckpt_2"
    assert latest.sequence_no == 2
    assert latest.serialized_state["tax"] == 450

    by_ref = await in_memory_repo.get_checkpoint("ckpt_1")
    assert by_ref is not None
    assert by_ref.sequence_no == 1

    all_ckpts = await in_memory_repo.list_checkpoints("run_1")
    assert len(all_ckpts) == 2
    assert [c.checkpoint_ref for c in all_ckpts] == ["ckpt_1", "ckpt_2"]


@pytest.mark.asyncio
async def test_events_append_and_ordering(in_memory_repo: RunRepository):
    ev1 = RunEventRecord(
        event_id="ev_1",
        run_id="run_1",
        event_type="run.started",
        payload={"agent": "finance"},
    )
    ev2 = RunEventRecord(
        event_id="ev_2",
        run_id="run_1",
        event_type="tool.requested",
        payload={"tool": "finance.invoice.list"},
    )
    ev3 = RunEventRecord(
        event_id="ev_3",
        run_id="run_1",
        event_type="tool.completed",
        payload={"count": 5},
    )

    await in_memory_repo.append_event(ev1)
    await in_memory_repo.append_event(ev2)
    await in_memory_repo.append_event(ev3)

    all_events = await in_memory_repo.list_events("run_1")
    assert len(all_events) == 3
    assert [e.event_type for e in all_events] == ["run.started", "tool.requested", "tool.completed"]
    assert [e.sequence_no for e in all_events] == [1, 2, 3]

    after_seq1 = await in_memory_repo.list_events("run_1", after_seq=1)
    assert len(after_seq1) == 2
    assert [e.event_type for e in after_seq1] == ["tool.requested", "tool.completed"]


@pytest.mark.asyncio
async def test_tool_call_exact_invocation_ledger(in_memory_repo: RunRepository):
    # Lookup by tool_call_id (KHÔNG theo (run_id, action))
    tc1 = RunToolCallRecord(
        tool_call_id="call_abc_1",
        run_id="run_1",
        checkpoint_ref="ckpt_1",
        capability_id="finance.invoice.send",
        payload_hash="hash_payload_1",
        input_payload={"invoice_id": "inv_101", "amount": 5000},
        idempotency_key="idem_key_101",
    )
    await in_memory_repo.save_tool_call(tc1)

    fetched = await in_memory_repo.get_tool_call("call_abc_1")
    assert fetched is not None
    assert fetched.capability_id == "finance.invoice.send"
    assert fetched.payload_hash == "hash_payload_1"

    # Idempotency lookup
    by_idem = await in_memory_repo.get_tool_call_by_idempotency("run_1", "idem_key_101")
    assert by_idem is not None
    assert by_idem.tool_call_id == "call_abc_1"


@pytest.mark.asyncio
async def test_approvals_bind_and_decide(in_memory_repo: RunRepository):
    # Tạo Run trước để test list_pending_approvals lọc theo workspace_id
    run = RunRecord(
        run_id="run_appr_1",
        principal="finance_user",
        root_executable_id="payout_agent",
        workspace_id="ws_finance",
    )
    await in_memory_repo.create_run(run)

    approval = RunApprovalRecord(
        approval_id="appr_99",
        run_id="run_appr_1",
        tool_call_id="call_payout_1",
        checkpoint_ref="ckpt_payout_wait",
        status="pending",
        requirement={"kind": "role_approval", "role": "founder"},
        action="payout.execute",
        subject="Payout $15,000 to vendor Acme",
    )
    await in_memory_repo.create_approval(approval)

    # Lookup theo tool_call_id & checkpoint_ref
    by_tool = await in_memory_repo.get_approval_by_tool_call("call_payout_1")
    assert by_tool is not None
    assert by_tool.approval_id == "appr_99"

    by_ckpt = await in_memory_repo.get_approval_by_checkpoint("ckpt_payout_wait")
    assert by_ckpt is not None
    assert by_ckpt.approval_id == "appr_99"

    # List pending
    pending = await in_memory_repo.list_pending_approvals(workspace_id="ws_finance")
    assert len(pending) == 1
    assert pending[0].approval_id == "appr_99"

    # Decide
    decided = await in_memory_repo.decide_approval(
        approval_id="appr_99",
        reviewer="founder_user_1",
        approved=True,
        reason="Verified invoice with PO-8899",
        evidence={"signature": "valid_sig_123"},
    )
    assert decided is not None
    assert decided.status == "approved"
    assert decided.reviewer == "founder_user_1"
    assert decided.evidence == {"signature": "valid_sig_123"}
    assert decided.decided_at is not None

    # Không còn pending
    pending_after = await in_memory_repo.list_pending_approvals(workspace_id="ws_finance")
    assert len(pending_after) == 0


@pytest.mark.asyncio
async def test_get_scoped_run_same_workspace_different_companies(in_memory_repo: RunRepository):
    """Test tenant isolation: workspace_id is the sole tenant key.
    Two runs in different workspaces should be isolated."""
    # Create run for workspace_a
    run_a = RunRecord(
        run_id="run_scoped_a",
        workspace_id="ws_a",
        principal="user:alice",
        root_executable_id="test-spec",
    )
    await in_memory_repo.create_run(run_a)

    # Create run for workspace_b
    run_b = RunRecord(
        run_id="run_scoped_b",
        workspace_id="ws_b",
        principal="user:bob",
        root_executable_id="test-spec",
    )
    await in_memory_repo.create_run(run_b)

    # Workspace A should only see their own run
    scoped_a = await in_memory_repo.get_scoped_run(
        run_id="run_scoped_a",
        workspace_id="ws_a",
    )
    assert scoped_a is not None
    assert scoped_a.workspace_id == "ws_a"

    # Workspace A trying to access Workspace B's run should get None
    scoped_a_wrong = await in_memory_repo.get_scoped_run(
        run_id="run_scoped_b",
        workspace_id="ws_a",
    )
    assert scoped_a_wrong is None

    # Workspace B should see their own run
    scoped_b = await in_memory_repo.get_scoped_run(
        run_id="run_scoped_b",
        workspace_id="ws_b",
    )
    assert scoped_b is not None
    assert scoped_b.workspace_id == "ws_b"

    # Workspace B trying to access Workspace A's run should get None
    scoped_b_wrong = await in_memory_repo.get_scoped_run(
        run_id="run_scoped_a",
        workspace_id="ws_b",
    )
    assert scoped_b_wrong is None


# ---------------------------------------------------------------------------
# Task 5: cancel_run / transition_run_status — durable cancel state machine.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_run_running_to_cancelled(in_memory_repo: RunRepository):
    """RUNNING -> CANCELLED qua cancel_run phải thành công."""
    run = RunRecord(
        run_id="run_cancel_1",
        workspace_id="ws_main",
        principal="founder_1",
        root_executable_id="finance_agent",
        status=RunStatus.RUNNING,
    )
    await in_memory_repo.create_run(run)

    cancelled = await in_memory_repo.cancel_run("run_cancel_1", reason="user requested")
    assert cancelled is not None
    assert cancelled.status == RunStatus.CANCELLED
    assert cancelled.error_details == {"reason": "user requested"}
    assert cancelled.completed_at is not None

    persisted = await in_memory_repo.get_run("run_cancel_1")
    assert persisted is not None
    assert persisted.status == RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_run_is_idempotent(in_memory_repo: RunRepository):
    """Gọi cancel_run 2 lần liên tiếp đều trả về CANCELLED, không lỗi/None."""
    run = RunRecord(
        run_id="run_cancel_2",
        workspace_id="ws_main",
        principal="founder_1",
        root_executable_id="finance_agent",
        status=RunStatus.RUNNING,
    )
    await in_memory_repo.create_run(run)

    first = await in_memory_repo.cancel_run("run_cancel_2", reason="first cancel")
    assert first is not None
    assert first.status == RunStatus.CANCELLED

    second = await in_memory_repo.cancel_run("run_cancel_2", reason="second cancel (idempotent)")
    assert second is not None
    assert second.status == RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_run_on_completed_run_is_noop(in_memory_repo: RunRepository):
    """cancel_run trên run đã COMPLETED không được đổi thành CANCELLED —
    trả về record terminal thật (COMPLETED), không phải None."""
    run = RunRecord(
        run_id="run_cancel_3",
        workspace_id="ws_main",
        principal="founder_1",
        root_executable_id="finance_agent",
        status=RunStatus.COMPLETED,
        final_output={"summary": "done"},
    )
    await in_memory_repo.create_run(run)

    result = await in_memory_repo.cancel_run("run_cancel_3", reason="too late")
    assert result is not None
    assert result.status == RunStatus.COMPLETED
    assert result.final_output == {"summary": "done"}

    persisted = await in_memory_repo.get_run("run_cancel_3")
    assert persisted is not None
    assert persisted.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_transition_run_status_rejects_from_cancelled(in_memory_repo: RunRepository):
    """CANCELLED -> COMPLETED/FAILED/WAITING_APPROVAL qua transition_run_status
    KHÔNG được đổi row — phải trả None và row giữ nguyên CANCELLED."""
    run = RunRecord(
        run_id="run_cancel_4",
        workspace_id="ws_main",
        principal="founder_1",
        root_executable_id="finance_agent",
        status=RunStatus.RUNNING,
    )
    await in_memory_repo.create_run(run)
    await in_memory_repo.cancel_run("run_cancel_4", reason="cancel before finalize")

    for target_status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.WAITING_APPROVAL):
        result = await in_memory_repo.transition_run_status(
            "run_cancel_4",
            from_statuses={RunStatus.RUNNING},
            to_status=target_status,
            final_output={"summary": "should not apply"} if target_status == RunStatus.COMPLETED else None,
        )
        assert result is None, f"transition to {target_status} should be rejected"

    persisted = await in_memory_repo.get_run("run_cancel_4")
    assert persisted is not None
    assert persisted.status == RunStatus.CANCELLED
    assert persisted.final_output is None


@pytest.mark.asyncio
async def test_worker_sees_cancelled_before_finalize_race(in_memory_repo: RunRepository):
    """Mô phỏng race cancel-vs-complete: cancel trước, sau đó một "worker"
    (đã bắt đầu xử lý từ trước khi biết run bị cancel) cố hoàn tất run bằng
    transition_run_status(..., to_status=COMPLETED, from_statuses={RUNNING}).
    Phải trả None và run phải ở CANCELLED khi worker get_run() lại."""
    run = RunRecord(
        run_id="run_cancel_5",
        workspace_id="ws_main",
        principal="founder_1",
        root_executable_id="finance_agent",
        status=RunStatus.RUNNING,
    )
    await in_memory_repo.create_run(run)

    # Cancel "đến trước" (vd. từ 1 request/process khác).
    cancelled = await in_memory_repo.cancel_run("run_cancel_5", reason="race: cancel wins")
    assert cancelled is not None
    assert cancelled.status == RunStatus.CANCELLED

    # Worker đọc lại run trước khi finalize -> phải thấy CANCELLED.
    seen_by_worker = await in_memory_repo.get_run("run_cancel_5")
    assert seen_by_worker is not None
    assert seen_by_worker.status == RunStatus.CANCELLED

    # Worker cố hoàn tất (late-arriving finalize write) -> phải bị từ chối.
    finalize_result = await in_memory_repo.transition_run_status(
        "run_cancel_5",
        from_statuses={RunStatus.RUNNING},
        to_status=RunStatus.COMPLETED,
        final_output={"summary": "late completion attempt"},
    )
    assert finalize_result is None

    final_state = await in_memory_repo.get_run("run_cancel_5")
    assert final_state is not None
    assert final_state.status == RunStatus.CANCELLED
    assert final_state.final_output is None


@pytest.mark.asyncio
async def test_transition_run_status_succeeds_from_matching_active_state(
    in_memory_repo: RunRepository,
):
    """Sanity check tích cực: transition_run_status thành công bình thường khi
    status hiện tại nằm trong from_statuses (không phải lúc nào cũng None)."""
    run = RunRecord(
        run_id="run_transition_ok",
        workspace_id="ws_main",
        principal="founder_1",
        root_executable_id="finance_agent",
        status=RunStatus.RUNNING,
    )
    await in_memory_repo.create_run(run)

    result = await in_memory_repo.transition_run_status(
        "run_transition_ok",
        from_statuses={RunStatus.RUNNING},
        to_status=RunStatus.COMPLETED,
        final_output={"summary": "ok"},
    )
    assert result is not None
    assert result.status == RunStatus.COMPLETED
    assert result.final_output == {"summary": "ok"}
