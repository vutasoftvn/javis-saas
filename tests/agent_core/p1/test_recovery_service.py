from __future__ import annotations

import pytest

from agent_core.contracts.run import RunStatus
from agent_core.runs.models import RunCheckpointRecord, RunRecord
from agent_core.runs.recovery import RunRecoveryService
from agent_core.runs.repository import InMemoryRunRepository



@pytest.mark.asyncio
async def test_recovery_service_liveness_restore():
    """Kiểm thử RunRecoveryService (§21 & §43.6):
    Khôi phục liveness an toàn, không bypass approval gate, load đúng checkpoint gần nhất.
    """
    repo = InMemoryRunRepository()
    recovery_svc = RunRecoveryService(repo)

    # 1. Run ở WAITING_APPROVAL -> Recovery giữ nguyên trạng thái chờ, không bypass
    run_wait = RunRecord(
        run_id="run_paused_approval",
        principal="user:1",
        root_executable_id="spec_1",
        root_executable_kind="agent",
        root_executable_version="1.0.0",
        root_definition_hash="hash_1",
        status=RunStatus.WAITING_APPROVAL,
    )
    await repo.create_run(run_wait)

    res_wait = await recovery_svc.recover_stale_run("run_paused_approval")
    assert res_wait.action_taken == "skipped"
    assert res_wait.status == RunStatus.WAITING_APPROVAL.value

    # 2. Run bị crash khi đang RUNNING, có checkpoint -> Resume từ latest checkpoint
    run_running = RunRecord(
        run_id="run_crashed_midway",
        principal="user:1",
        root_executable_id="spec_1",
        root_executable_kind="agent",
        root_executable_version="1.0.0",
        root_definition_hash="hash_1",
        status=RunStatus.RUNNING,
    )
    await repo.create_run(run_running)
    ckpt = RunCheckpointRecord(
        checkpoint_ref="ckpt_crashed_step3",
        run_id="run_crashed_midway",
        sequence_no=3,
        step_name="step_analytics",
        state_kind="kernel_state",
        serialized_state={"step_index": 3},
    )
    await repo.save_checkpoint(ckpt)

    resumed_calls = []

    async def mock_resume_executor(run_id: str, ckpt_ref: str):
        resumed_calls.append((run_id, ckpt_ref))

    res_recover = await recovery_svc.recover_stale_run(
        "run_crashed_midway",
        resume_executor=mock_resume_executor,
    )
    assert res_recover.action_taken == "resumed"
    assert res_recover.checkpoint_ref == "ckpt_crashed_step3"
    assert len(resumed_calls) == 1
    assert resumed_calls[0] == ("run_crashed_midway", "ckpt_crashed_step3")
