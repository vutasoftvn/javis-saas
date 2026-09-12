from __future__ import annotations

from datetime import datetime, UTC
import pytest

from agent.runs.models import (
    ApprovalActionOutboxRecord,
    ApprovalEventRecord,
    ApprovalSubject,
    RunApprovalRecord,
    RunCheckpointRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_change_request_is_scoped_without_a_run() -> None:
    repo = InMemoryRunRepository()
    approval = RunApprovalRecord(
        approval_id="appr_change_1",
        workspace_id="ws-a",
        binding_kind="CHANGE_REQUEST",
        run_id=None,
        tool_call_id=None,
        checkpoint_ref=None,
        action="promote_skill_candidate",
        subject_kind="skill_candidate",
        subject_ref="cand_1",
        subject_hash="sha256:candidate-v1",
        requirement={"role": "founder"},
        status="pending",
    )
    await repo.create_approval(approval)
    assert await repo.get_scoped_approval("appr_change_1", "ws-a") == approval
    assert await repo.get_scoped_approval("appr_change_1", "ws-b") is None
    assert await repo.get_approval_by_tool_call("call_any") is None


@pytest.mark.asyncio
async def test_tool_call_approval_binding_exactness() -> None:
    repo = InMemoryRunRepository()
    run = RunRecord(
        run_id="run_t1",
        principal="user_1",
        root_executable_id="workflow_1",
        workspace_id="ws-a",
    )
    await repo.create_run(run)

    ckpt = RunCheckpointRecord(
        checkpoint_ref="ckpt_1",
        run_id="run_t1",
        sequence_no=1,
    )
    await repo.save_checkpoint(ckpt)

    tc = RunToolCallRecord(
        tool_call_id="call_1",
        run_id="run_t1",
        capability_id="cap.write",
        payload_hash="sha256:p1",
    )
    await repo.save_tool_call(tc)

    approval = RunApprovalRecord(
        approval_id="appr_tool_1",
        workspace_id="ws-a",
        binding_kind="TOOL_CALL",
        run_id="run_t1",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
        action="cap.write",
        status="pending",
        requirement={"role": "operator"},
        manifest_hash="sha256:man1",
    )
    await repo.create_approval(approval)

    # Scoped lookup
    scoped = await repo.get_scoped_approval("appr_tool_1", "ws-a")
    assert scoped is not None
    assert scoped.approval_id == "appr_tool_1"
    assert scoped.binding_kind == "TOOL_CALL"
    assert scoped.run_id == "run_t1"
    assert scoped.tool_call_id == "call_1"
    assert scoped.checkpoint_ref == "ckpt_1"

    # Cross-tenant scoped lookup returns None
    assert await repo.get_scoped_approval("appr_tool_1", "ws-other") is None

    # Exact tool call lookup
    found_by_tool = await repo.get_approval_by_tool_call("call_1")
    assert found_by_tool is not None
    assert found_by_tool.approval_id == "appr_tool_1"

    # Changed tool call or checkpoint cannot match
    assert await repo.get_approval_by_tool_call("call_changed") is None
    assert await repo.get_approval_by_checkpoint("ckpt_changed") is None


@pytest.mark.asyncio
async def test_create_or_get_pending_change_approval_deduplication() -> None:
    repo = InMemoryRunRepository()
    approval1 = RunApprovalRecord(
        approval_id="appr_c1",
        workspace_id="ws-a",
        binding_kind="CHANGE_REQUEST",
        action="promote_skill_candidate",
        subject_kind="skill_candidate",
        subject_ref="cand_1",
        subject_hash="sha256:h1",
        requirement={"role": "founder"},
        status="pending",
    )
    created, is_new = await repo.create_or_get_pending_change_approval(approval1)
    assert is_new is True
    assert created.approval_id == "appr_c1"

    # Create same change approval while pending -> returns existing
    approval2 = RunApprovalRecord(
        approval_id="appr_c2",
        workspace_id="ws-a",
        binding_kind="CHANGE_REQUEST",
        action="promote_skill_candidate",
        subject_kind="skill_candidate",
        subject_ref="cand_1",
        subject_hash="sha256:h1",
        requirement={"role": "founder"},
        status="pending",
    )
    existing, is_new2 = await repo.create_or_get_pending_change_approval(approval2)
    assert is_new2 is False
    assert existing.approval_id == "appr_c1"


@pytest.mark.asyncio
async def test_decide_change_approval_and_enqueue_cas() -> None:
    repo = InMemoryRunRepository()
    approval = RunApprovalRecord(
        approval_id="appr_c1",
        workspace_id="ws-a",
        binding_kind="CHANGE_REQUEST",
        action="promote_skill_candidate",
        subject_kind="skill_candidate",
        subject_ref="cand_1",
        subject_hash="sha256:h1",
        requirement={"role": "founder"},
        status="pending",
    )
    await repo.create_approval(approval)

    # Allow-listed action inserts outbox on approval
    res = await repo.decide_change_approval_and_enqueue(
        approval_id="appr_c1",
        reviewer="founder_1",
        approved=True,
        reason="Looks good",
        evidence={"score": 0.95},
    )
    assert res is not None
    assert res.status == "approved"
    assert res.reviewer == "founder_1"

    # Check outbox has 1 record
    claims = await repo.claim_approval_actions(limit=10, worker_id="worker_1", now=datetime.now(UTC))
    assert len(claims) == 1
    assert claims[0].approval_id == "appr_c1"
    assert claims[0].workspace_id == "ws-a"
    assert claims[0].action == "promote_skill_candidate"
    assert claims[0].subject_hash == "sha256:h1"
    assert claims[0].state == "claimed"
    assert claims[0].claim_token == "worker_1"

    # Subsequent decision fails CAS
    res2 = await repo.decide_change_approval_and_enqueue(
        approval_id="appr_c1",
        reviewer="founder_2",
        approved=False,
    )
    assert res2 is None
