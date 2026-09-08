"""Cross-process race THẬT giữa cancel_run và transition_run_status(..., COMPLETED)
qua Postgres — chứng minh CAS atomic UPDATE ... WHERE status = ANY(:from_statuses)
đóng được race cancel-vs-complete kể cả khi 2 phía chạy trên 2 OS process/
connection khác nhau hoàn toàn (không phải 2 asyncio task cùng process — CLAUDE.md
rule 6 và Task 5 Global Constraints coi đó KHÔNG phải chứng minh durability thật).

Quy trình (mô hình theo test_postgres_cross_process_resume.py):
1. Process cha: tạo run RUNNING qua PostgresRunRepository, commit thật vào
   Postgres, đóng engine trước khi spawn subprocess (không giữ connection mở).
2. Subprocess (subprocess.run độc lập hoàn toàn, mở connection MỚI tới CÙNG
   Postgres): gọi cancel_run(run_id, reason=...) — mô phỏng cancel đến từ 1
   process/worker khác.
3. Process cha (sau khi subprocess đã hoàn tất và thoát hẳn): mở connection
   MỚI (khác connection ban đầu), gọi transition_run_status(..., to_status=
   COMPLETED, from_statuses={RUNNING}) — mô phỏng 1 worker đã bắt đầu xử lý
   run TỪ TRƯỚC khi biết nó bị cancel, giờ mới ghi kết quả hoàn tất (late-
   arriving finalize write).
4. Assert: transition trả None (bị CAS chặn), và trạng thái persist cuối cùng
   (đọc qua 1 connection thứ ba, mới hoàn toàn) là CANCELLED — không bị
   complete-write ghi đè.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytest.importorskip("asyncpg")

_RAW_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if _RAW_DB_URL and "postgresql+asyncpg://" not in _RAW_DB_URL and "postgresql://" in _RAW_DB_URL:
    TEST_DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    TEST_DATABASE_URL = _RAW_DB_URL

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENT_TEST_DATABASE_URL not set — skipping real-Postgres cancel/complete race test",
)

_WORKER_SCRIPT = '''
import asyncio
import sys

from agent.contracts.run import RunStatus
from agent.runs.repository import PostgresRunRepository
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

async def main():
    database_url = sys.argv[1]
    run_id = sys.argv[2]
    reason = sys.argv[3]

    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(factory)

    # Verify Step 1 state (tạo bởi process cha) load được qua connection MỚI.
    existing_run = await repo.get_run(run_id)
    assert existing_run is not None, "run not found via fresh connection"
    assert existing_run.status == RunStatus.RUNNING

    cancelled = await repo.cancel_run(run_id, reason=reason)
    assert cancelled is not None
    assert cancelled.status == RunStatus.CANCELLED

    await engine.dispose()
    print("CANCEL_SUCCESS")

asyncio.run(main())
'''


@pytest.mark.asyncio
async def test_cancel_vs_late_complete_race_resolves_to_cancelled_across_processes(
    tmp_path: Path,
):
    from agent.contracts.run import RunStatus
    from agent.governance.contracts import ExecutionMode
    from agent.runs.models import RunRecord
    from agent.runs.repository import PostgresRunRepository
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    run_id = f"run_cancel_race_{uuid.uuid4().hex[:8]}"

    # 1. Process cha: tạo run RUNNING, đóng engine hoàn toàn trước khi spawn
    #    subprocess (mô phỏng "chết"/handoff sang worker khác).
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = PostgresRunRepository(factory)

    run = RunRecord(
        run_id=run_id,
        principal="test-suite",
        root_executable_id="cancel_complete_race_flow",
        status=RunStatus.RUNNING,
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_race",
    )
    await repo.create_run(run)
    await engine.dispose()  # process cha "chết" — không còn connection nào mở

    # 2. Spawn subprocess Python độc lập hoàn toàn — nó cancel_run trên CÙNG
    #    Postgres qua connection MỚI, không liên quan gì tới process cha.
    worker_script_file = tmp_path / "cancel_worker.py"
    worker_script_file.write_text(_WORKER_SCRIPT, encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONPATH"] = f"{Path.cwd() / 'packages'}:{Path.cwd()}"

    proc = subprocess.run(
        [sys.executable, str(worker_script_file), TEST_DATABASE_URL, run_id, "cancelled by other process"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    assert proc.returncode == 0, f"Subprocess failed:\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}"
    assert "CANCEL_SUCCESS" in proc.stdout

    # 3. Process cha (sau khi subprocess đã thoát hẳn): mở connection MỚI,
    #    cố hoàn tất run — mô phỏng late-arriving finalize write từ 1 worker
    #    đã bắt đầu xử lý run TRƯỚC khi cancel xảy ra.
    late_engine = create_async_engine(TEST_DATABASE_URL)
    late_factory = async_sessionmaker(late_engine, expire_on_commit=False)
    late_repo = PostgresRunRepository(late_factory)

    finalize_result = await late_repo.transition_run_status(
        run_id,
        from_statuses={RunStatus.RUNNING},
        to_status=RunStatus.COMPLETED,
        final_output={"summary": "late completion should be rejected"},
    )
    assert finalize_result is None, "late COMPLETED write must be rejected by CAS after cancel"

    await late_engine.dispose()

    # 4. Verify qua connection thứ BA, hoàn toàn mới: trạng thái cuối cùng
    #    phải là CANCELLED, KHÔNG bị ghi đè bởi complete-write muộn.
    verify_engine = create_async_engine(TEST_DATABASE_URL)
    verify_factory = async_sessionmaker(verify_engine, expire_on_commit=False)
    verify_repo = PostgresRunRepository(verify_factory)

    final_run = await verify_repo.get_run(run_id)
    assert final_run is not None
    assert final_run.status == RunStatus.CANCELLED
    assert final_run.final_output is None

    await verify_engine.dispose()
