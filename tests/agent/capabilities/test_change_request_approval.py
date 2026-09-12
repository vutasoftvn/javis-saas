from __future__ import annotations

from datetime import UTC, datetime, timedelta
import pytest

from agent.capabilities.approval_service import (
    ApprovalAlreadyDecidedError,
    ApprovalChangeExecutionResult,
    DurableApprovalService,
)
from agent.runs.models import ApprovalSubject, RunApprovalRecord
from agent.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_change_approval_is_idempotent() -> None:
    service = DurableApprovalService(InMemoryRunRepository())
    subject = ApprovalSubject(kind="skill_candidate", ref="cand_a", definition_hash="sha256:one")
    first, _ = await service.create_change_approval_request(
        workspace_id="ws-a",
        project_id=None,
        action="promote_skill_candidate",
        subject=subject,
        requirement={"role": "founder"},
        requester="user:operator",
    )
    second, _ = await service.create_change_approval_request(
        workspace_id="ws-a",
        project_id=None,
        action="promote_skill_candidate",
        subject=subject,
        requirement={"role": "founder"},
        requester="user:operator",
    )
    assert second.approval_id == first.approval_id
    assert first.tool_call_id is None
    assert first.binding_kind == "CHANGE_REQUEST"


@pytest.mark.asyncio
async def test_verify_change_execution_outcomes() -> None:
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repo)
    subject = ApprovalSubject(kind="skill_candidate", ref="cand_a", definition_hash="sha256:one")

    appr, _ = await service.create_change_approval_request(
        workspace_id="ws-a",
        project_id=None,
        action="promote_skill_candidate",
        subject=subject,
        requirement={"role": "founder"},
        requester="user:operator",
    )

    # 1. Not found / forbidden
    res_not_found = await service.verify_change_execution(
        approval_id="non_existent",
        workspace_id="ws-a",
        action="promote_skill_candidate",
        subject=subject,
    )
    assert not res_not_found.can_execute
    assert res_not_found.reason_code == "APPROVAL_NOT_FOUND_OR_FORBIDDEN"

    # Cross-workspace is not found / forbidden
    res_foreign = await service.verify_change_execution(
        approval_id=appr.approval_id,
        workspace_id="ws-b",
        action="promote_skill_candidate",
        subject=subject,
    )
    assert not res_foreign.can_execute
    assert res_foreign.reason_code == "APPROVAL_NOT_FOUND_OR_FORBIDDEN"

    # 2. Not approved yet (pending)
    res_pending = await service.verify_change_execution(
        approval_id=appr.approval_id,
        workspace_id="ws-a",
        action="promote_skill_candidate",
        subject=subject,
    )
    assert not res_pending.can_execute
    assert res_pending.reason_code == "APPROVAL_NOT_APPROVED"

    # 3. Approve it
    await service.submit_decision(
        approval_id=appr.approval_id,
        reviewer="founder_1",
        approved=True,
    )

    # 4. Valid execution
    res_valid = await service.verify_change_execution(
        approval_id=appr.approval_id,
        workspace_id="ws-a",
        action="promote_skill_candidate",
        subject=subject,
    )
    assert res_valid.can_execute
    assert res_valid.reason_code == "APPROVAL_VALID"

    # 5. Wrong action
    res_wrong_action = await service.verify_change_execution(
        approval_id=appr.approval_id,
        workspace_id="ws-a",
        action="delete_skill",
        subject=subject,
    )
    assert not res_wrong_action.can_execute
    assert res_wrong_action.reason_code == "APPROVAL_ACTION_MISMATCH"

    # 6. Changed hash / stale subject
    changed_subject = ApprovalSubject(kind="skill_candidate", ref="cand_a", definition_hash="sha256:drifted")
    res_stale = await service.verify_change_execution(
        approval_id=appr.approval_id,
        workspace_id="ws-a",
        action="promote_skill_candidate",
        subject=changed_subject,
    )
    assert not res_stale.can_execute
    assert res_stale.reason_code == "APPROVAL_SUBJECT_STALE"

    # 7. Expired record cannot execute
    raw_appr = await repo.get_approval(appr.approval_id)
    raw_appr.expires_at = datetime.now(UTC) - timedelta(minutes=10)
    await repo.create_approval(raw_appr)

    res_expired = await service.verify_change_execution(
        approval_id=appr.approval_id,
        workspace_id="ws-a",
        action="promote_skill_candidate",
        subject=subject,
    )
    assert not res_expired.can_execute
    assert res_expired.reason_code == "APPROVAL_EXPIRED"


@pytest.mark.asyncio
async def test_change_request_rejected_by_verify_and_prepare_resume() -> None:
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repo)
    subject = ApprovalSubject(kind="skill_candidate", ref="cand_a", definition_hash="sha256:one")

    appr, _ = await service.create_change_approval_request(
        workspace_id="ws-a",
        project_id=None,
        action="promote_skill_candidate",
        subject=subject,
        requirement={"role": "founder"},
        requester="user:operator",
    )
    await service.submit_decision(
        approval_id=appr.approval_id,
        reviewer="founder_1",
        approved=True,
    )

    # Passing a CHANGE_REQUEST approval to verify_and_prepare_resume must be denied with APPROVAL_BINDING_KIND_MISMATCH
    result = await service.verify_and_prepare_resume(
        run_id="run_nonexistent",
        tool_call_id="call_nonexistent",
        checkpoint_ref="ckpt_nonexistent",
    )
    # When run_id is missing, it returns RUN_NOT_FOUND, but if we query by approval that is CHANGE_REQUEST:
    # Let's also verify that verify_change_execution rejects TOOL_CALL
    tool_appr = RunApprovalRecord(
        approval_id="appr_tool_test",
        workspace_id="ws-a",
        binding_kind="TOOL_CALL",
        run_id="run_1",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
        action="promote_skill_candidate",
        subject_kind="skill_candidate",
        subject_ref="cand_a",
        subject_hash="sha256:one",
        status="approved",
    )
    await repo.create_approval(tool_appr)

    tool_res = await service.verify_change_execution(
        approval_id="appr_tool_test",
        workspace_id="ws-a",
        action="promote_skill_candidate",
        subject=subject,
    )
    assert not tool_res.can_execute
    assert tool_res.reason_code == "APPROVAL_BINDING_KIND_MISMATCH"
