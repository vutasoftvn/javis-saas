"""COSA Automation MVP (Task 6) — exact approval binding to the execution
manifest, and recovery never reclaiming a terminal run."""

from __future__ import annotations

import pytest
from agent.capabilities.approval_service import DurableApprovalService
from agent.contracts.run import RunStatus
from agent.runs.models import RunCheckpointRecord, RunRecord, RunToolCallRecord
from agent.runs.recovery import RunRecoveryService
from agent.runs.repository import InMemoryRunRepository

MANIFEST_A = "a" * 64
MANIFEST_B = "b" * 64


async def _seed_pending_approval(repo: InMemoryRunRepository, manifest_hash: str):
    run = RunRecord(
        run_id="run_life_1",
        workspace_id="ws1",
        principal="system:automation:ws1",
        root_executable_id="operating.weekly-review",
        root_executable_kind="workflow",
        status=RunStatus.WAITING_APPROVAL,
    )
    await repo.create_run(run)
    await repo.save_tool_call(
        RunToolCallRecord(
            tool_call_id="call_1",
            run_id="run_life_1",
            checkpoint_ref="ckpt_1",
            capability_id="operations.write",
            payload_hash="p",
            status="waiting_approval",
        )
    )
    await repo.save_checkpoint(
        RunCheckpointRecord(checkpoint_ref="ckpt_1", run_id="run_life_1", sequence_no=1)
    )
    svc = DurableApprovalService(repository=repo)
    await svc.create_approval_request(
        run_id="run_life_1",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
        action="operations.write",
        subject="task-42",
        manifest_hash=manifest_hash,
    )
    return svc


@pytest.mark.asyncio
async def test_approval_is_rejected_when_resumed_under_a_different_manifest():
    repo = InMemoryRunRepository()
    svc = await _seed_pending_approval(repo, MANIFEST_A)
    await repo.decide_approval("appr_run_life_1_call_1", reviewer="founder-1", approved=True)

    res = await svc.verify_and_prepare_resume(
        run_id="run_life_1",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
        expected_manifest_hash=MANIFEST_B,
    )
    assert res.can_resume is False
    assert "manifest" in res.reason.lower()


@pytest.mark.asyncio
async def test_approval_passes_the_manifest_check_under_the_same_manifest():
    repo = InMemoryRunRepository()
    svc = await _seed_pending_approval(repo, MANIFEST_A)
    await repo.decide_approval("appr_run_life_1_call_1", reviewer="founder-1", approved=True)

    res = await svc.verify_and_prepare_resume(
        run_id="run_life_1",
        tool_call_id="call_1",
        checkpoint_ref="ckpt_1",
        expected_manifest_hash=MANIFEST_A,
    )
    # It may still be blocked by later checks, but never by a manifest mismatch.
    assert res.reason is None or "manifest" not in res.reason.lower()


@pytest.mark.asyncio
async def test_a_concurrent_decision_produces_exactly_one_winner():
    repo = InMemoryRunRepository()
    await _seed_pending_approval(repo, MANIFEST_A)
    first = await repo.decide_approval("appr_run_life_1_call_1", reviewer="r1", approved=True)
    second = await repo.decide_approval("appr_run_life_1_call_1", reviewer="r2", approved=False)
    assert first is not None and first.status == "approved"
    assert second is None  # CAS: only the first pending->decided transition wins


@pytest.mark.asyncio
async def test_recovery_never_reclaims_a_terminal_automation_run():
    repo = InMemoryRunRepository()
    await repo.create_run(
        RunRecord(
            run_id="run_term_1",
            workspace_id="ws1",
            principal="system:automation:ws1",
            root_executable_id="operating.weekly-review",
            root_executable_kind="workflow",
            status=RunStatus.COMPLETED,
        )
    )
    result = await RunRecoveryService(repository=repo).recover_stale_run("run_term_1")
    assert result.action_taken == "skipped"
    assert "terminal" in result.reason.lower()
