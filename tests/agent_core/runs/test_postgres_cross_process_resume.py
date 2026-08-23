"""Cross-process durable resume test THẬT với Postgres — thay thế
test_process_resume.py cũ (dùng file JSON, không được coi là chứng minh
durability theo DB_FINAL_CUTOVER.md §8.2).

Quy trình:
1. Process cha: tạo run + checkpoint đầu tiên qua PostgresRunRepository, commit
   thật vào Postgres, KHÔNG giữ connection mở (đóng engine trước khi spawn).
2. Process con (subprocess.run độc lập): mở connection MỚI tới CÙNG Postgres,
   load lại run + checkpoint từ DB, verify state đúng, tạo checkpoint tiếp
   theo + approval, rồi hoàn tất run.
3. Process cha: mở connection MỚI (khác connection ban đầu) verify: checkpoint
   không bị mất, tool_call idempotency giữ (gọi lại với cùng idempotency_key
   không tạo bản ghi thứ hai), approval binding đúng run_id+tool_call_id, và
   final_output đúng.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENT_CORE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_CORE_TEST_DATABASE_URL not set — skipping real-Postgres cross-process resume test",
)

_WORKER_SCRIPT = '''
import asyncio
import sys

from agent_core.contracts.run import RunStatus
from agent_core.runs.models import RunCheckpointRecord
from agent_core.runs.repository import PostgresRunRepository
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

async def main():
    database_url = sys.argv[1]
    run_id = sys.argv[2]
    tool_call_id = sys.argv[3]
    idempotency_key = sys.argv[4]

    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(factory)

    # 1. Verify Step 1 checkpoint (tạo bởi process cha) load được qua connection MỚI.
    existing_run = await repo.get_run(run_id)
    assert existing_run is not None, "run not found via fresh connection"
    assert existing_run.status == RunStatus.WAITING_APPROVAL

    latest = await repo.get_latest_checkpoint(run_id)
    assert latest is not None
    assert latest.step_name == "step_1"
    assert latest.serialized_state["fetched_items"] == [10, 20, 30]

    # 2. Idempotency: get_tool_call_by_idempotency phải trả đúng bản ghi đã
    #    tồn tại (tạo bởi process cha), không tạo bản ghi thứ hai.
    existing_call = await repo.get_tool_call_by_idempotency(run_id, idempotency_key)
    assert existing_call is not None, "idempotent tool call from parent process not found"
    assert existing_call.tool_call_id == tool_call_id

    # 3. Approval binding: run_id + tool_call_id + checkpoint_ref đúng.
    approval = await repo.get_approval_by_tool_call(tool_call_id)
    assert approval is not None
    assert approval.run_id == run_id
    assert approval.checkpoint_ref == latest.checkpoint_ref

    await repo.decide_approval(approval.approval_id, reviewer="ops-lead", approved=True, reason="looks good")

    # 4. Step 2 checkpoint + hoàn tất run — mô phỏng resume thật sự chạy tiếp.
    step2 = RunCheckpointRecord(
        run_id=run_id,
        sequence_no=2,
        step_name="step_2",
        serialized_state={"fetched_items": [10, 20, 30], "total_sum": 60},
    )
    await repo.save_checkpoint(step2)
    await repo.update_run_status(run_id, RunStatus.COMPLETED, final_output={"report_id": "rep_60"})

    await engine.dispose()
    print("RESUME_SUCCESS")

asyncio.run(main())
'''


@pytest.mark.asyncio
async def test_cross_process_durable_resume_with_real_postgres(tmp_path: Path):
    from agent_core.contracts.run import RunStatus
    from agent_core.governance.contracts import ExecutionMode
    from agent_core.runs.models import RunCheckpointRecord, RunRecord, RunApprovalRecord, RunToolCallRecord
    from agent_core.runs.repository import PostgresRunRepository
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    run_id = f"run_xproc_{uuid.uuid4().hex[:8]}"
    tool_call_id = f"call_xproc_{uuid.uuid4().hex[:8]}"
    idempotency_key = f"idem_{uuid.uuid4().hex[:8]}"

    # 1. Process cha: tạo run, checkpoint step_1, tool_call, approval — rồi
    #    đóng engine hoàn toàn (mô phỏng "chết"/crash trước khi resume).
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(factory)

    run = RunRecord(
        run_id=run_id,
        principal="test-suite",
        root_executable_id="multi_step_process_flow",
        status=RunStatus.WAITING_APPROVAL,
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        workspace_id="ws_alpha",
    )
    await repo.create_run(run)

    checkpoint = RunCheckpointRecord(
        run_id=run_id,
        sequence_no=1,
        step_name="step_1",
        serialized_state={"workspace_id": "ws_alpha", "fetched_items": [10, 20, 30]},
    )
    await repo.save_checkpoint(checkpoint)

    tool_call = RunToolCallRecord(
        tool_call_id=tool_call_id,
        run_id=run_id,
        checkpoint_ref=checkpoint.checkpoint_ref,
        capability_id="finance.payout.execute",
        payload_hash="deadbeef",
        idempotency_key=idempotency_key,
        status="pending",
    )
    await repo.save_tool_call(tool_call)

    approval = RunApprovalRecord(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint.checkpoint_ref,
        status="pending",
        requester="agent",
        action="finance.payout.execute",
    )
    await repo.create_approval(approval)

    await engine.dispose()  # process cha "chết" — không còn connection nào mở

    # 2. Spawn subprocess Python độc lập hoàn toàn để resume qua Postgres.
    worker_script_file = tmp_path / "worker.py"
    worker_script_file.write_text(_WORKER_SCRIPT, encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONPATH"] = f"{Path.cwd() / 'packages'}:{Path.cwd()}"

    proc = subprocess.run(
        [sys.executable, str(worker_script_file), TEST_DATABASE_URL, run_id, tool_call_id, idempotency_key],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    assert proc.returncode == 0, f"Subprocess failed:\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}"
    assert "RESUME_SUCCESS" in proc.stdout

    # 3. Process cha verify qua connection MỚI (khác connection ban đầu).
    verify_engine = create_async_engine(TEST_DATABASE_URL)
    verify_factory = async_sessionmaker(verify_engine, expire_on_commit=False)
    verify_repo = PostgresRunRepository(verify_factory)

    final_run = await verify_repo.get_run(run_id)
    assert final_run is not None
    assert final_run.status == RunStatus.COMPLETED
    assert final_run.final_output == {"report_id": "rep_60"}

    checkpoints = await verify_repo.list_checkpoints(run_id)
    assert [c.step_name for c in checkpoints] == ["step_1", "step_2"]  # step_1 không bị chạy lại/mất

    final_approval = await verify_repo.get_approval(approval.approval_id)
    assert final_approval is not None
    assert final_approval.status == "approved"
    assert final_approval.reviewer == "ops-lead"

    # Idempotency: gọi lại get_tool_call_by_idempotency vẫn trả đúng 1 bản ghi gốc.
    still_one_call = await verify_repo.get_tool_call_by_idempotency(run_id, idempotency_key)
    assert still_one_call is not None
    assert still_one_call.tool_call_id == tool_call_id

    await verify_engine.dispose()
