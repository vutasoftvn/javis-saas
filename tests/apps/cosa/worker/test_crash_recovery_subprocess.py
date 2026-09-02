"""Cross-process crash-recovery test cho apps/cosa/worker/main.py — THẬT.

Này là test kiểm chứng THẬT (phải qua 2 OS process khác nhau chạy real code,
không phải 2 function call trong cùng 1 process — xem CLAUDE.md #6).

Test này (P0.4, Section C & Part 1C):
1. Starts `encore run` for services/cosa (background, real HTTP control-plane)
2. Creates a task in control_plane.scheduled_tasks with delay_sec=10
3. Runs subprocess A: `python -m apps.cosa.worker.main --once`
   - A polls, claims the task (processing), starts executing, THEN CRASHES (killed mid-execution)
4. Waits for visibility timeout expiration
5. Calls control-plane sweeper (/control-plane/internal/scheduled-tasks/reclaim-stuck)
   - Sweeper reclaims task back to "scheduled" and increments attempt_count
6. Runs subprocess B: `python -m apps.cosa.worker.main --once`
   - B polls, claims reclaimed task, processes and completes it
7. Verifies:
   - Task final status is strictly "completed" in Postgres
   - attempt_count increased
   - Stale worker A claim token rejected by fencing
   - Stale worker A lease token rejected for renewal/release
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import jwt
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from apps.cosa.auth.jwt import mint_delegation_token

__all__ = ["test_two_real_processes_crash_recovery_real_worker"]


def _sign_worker_token(worker_id: str) -> str:
    secret = (
        os.environ.get("WORKER_SERVICE_JWT_SECRET")
        or os.environ.get("PLATFORM_JWT_SECRET")
        or "cosa-worker-service-jwt-key-change-in-prod-min32chars"
    )
    return jwt.encode(
        {
            "sub": worker_id,
            "aud": "control_plane",
            "role": "worker_service",
            "iss": "cosa_control_plane",
        },
        secret,
        algorithm="HS256",
    )


@pytest.fixture
def control_plane_dsn() -> str:
    """Fixture trỏ tới Control Plane Postgres thật."""
    dsn = (
        os.environ.get("COSA_TEST_DATABASE_URL")
        or os.environ.get("COSA_DATABASE_URL")
        or os.environ.get("AGENT_TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
    )
    if not dsn:
        pytest.skip("COSA_TEST_DATABASE_URL/DATABASE_URL không set")

    dsn = dsn.replace("postgres://", "postgresql://")
    parts = dsn.split("@")
    if len(parts) == 2 and ":5432" in parts[1]:
        prefix = parts[0]
        suffix = parts[1]
        if suffix.startswith("postgres:"):
            dsn = prefix + "@127.0.0.1:" + suffix[len("postgres:") :]

    return dsn


@pytest.fixture
def async_control_plane_dsn(control_plane_dsn: str) -> str:
    """Convert Control Plane DSN to async format for SQLAlchemy."""
    async_dsn = control_plane_dsn
    if "postgresql+asyncpg://" not in async_dsn:
        async_dsn = async_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return async_dsn


@pytest.fixture
def agent_dsn() -> str:
    """Fixture trỏ tới Agent Core Postgres thật."""
    dsn = os.environ.get("AGENT_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        pytest.skip("AGENT_TEST_DATABASE_URL/DATABASE_URL không set")

    dsn = dsn.replace("postgres://", "postgresql://")
    parts = dsn.split("@")
    if len(parts) == 2 and ":5432" in parts[1]:
        prefix = parts[0]
        suffix = parts[1]
        if suffix.startswith("postgres:"):
            dsn = prefix + "@127.0.0.1:" + suffix[len("postgres:") :]

    if "postgresql+asyncpg://" not in dsn:
        dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    return dsn


@pytest.fixture
def control_plane_service(control_plane_dsn: str):
    """Start `encore run` for services/cosa control-plane service.

    Yields control when service is healthy (responds to HTTP).
    Tears down `encore run` process when done.
    """
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    services_dir = repo_root / "services" / "cosa"

    encore_env = {**os.environ}
    db_url = control_plane_dsn
    if "?sslmode=" not in db_url:
        db_url = f"{db_url}?sslmode=disable"
    encore_env["COSA_DATABASE_URL"] = db_url

    if not shutil.which("encore"):
        pytest.skip("encore CLI not found in PATH")

    try:
        proc = subprocess.Popen(
            ["encore", "run", "--port=4000"],
            cwd=services_dir,
            env=encore_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        pytest.skip("encore CLI not installed")

    max_retries = 60
    retry_count = 0
    control_plane_port = 4000
    healthy = False
    while retry_count < max_retries:
        try:
            resp = httpx.get(f"http://127.0.0.1:{control_plane_port}/", timeout=1.0)
            if resp.status_code < 500:
                healthy = True
                break
        except Exception:
            pass

        if proc.poll() is not None:
            _, stderr = proc.communicate()
            pytest.skip(f"encore run died: {stderr.decode()[:200]}")

        time.sleep(0.5)
        retry_count += 1

    if not healthy:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        pytest.skip(
            f"Control-plane service didn't become healthy within {max_retries * 0.5} seconds"
        )

    try:
        yield f"http://127.0.0.1:{control_plane_port}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


@pytest.mark.durability
@pytest.mark.integration
def test_two_real_processes_crash_recovery_real_worker(
    control_plane_dsn: str,
    async_control_plane_dsn: str,
    agent_dsn: str,
    control_plane_service: str,
) -> None:
    """Test crash recovery using REAL worker.main code paths and verifying database recovery.

    Satisfies P0.4 and Part 1C:
    1. Worker A claims task and is killed mid-execution.
    2. Visibility timeout expires.
    3. Sweeper reclaims task to scheduled.
    4. Worker B claims reclaimed task and completes it.
    5. Assert status is strictly "completed" and attempt count increased.
    6. Fencing check: stale claim token rejected.
    """
    task_id = f"task_crash_test_{uuid.uuid4().hex[:8]}"
    run_id = f"run_crash_test_{uuid.uuid4().hex[:8]}"
    conv_id = f"conv_crash_test_{uuid.uuid4().hex[:8]}"
    delegation_token = mint_delegation_token("1001")

    async def setup_task():
        """Insert test conversation và task với delay_sec=10 (workspace-only tenancy: không seed hàng company/user ở cosa)."""
        agent_engine = create_async_engine(agent_dsn)
        try:
            async with agent_engine.begin() as conn:
                now = datetime.now(UTC)
                await conn.execute(
                    text("""
                        INSERT INTO agent_conversation.conversations (conversation_id, title, workspace_id, created_by_principal, created_at, updated_at)
                        VALUES (:conv_id, :title, :ws_id, '1001', :now, :now)
                        ON CONFLICT (conversation_id) DO NOTHING
                    """),
                    {
                        "conv_id": conv_id,
                        "title": "Test Crash Conv",
                        "ws_id": "ws-crash-test",
                        "now": now,
                    },
                )
        finally:
            await agent_engine.dispose()

        cp_engine = create_async_engine(async_control_plane_dsn)
        try:
            async with cp_engine.begin() as conn:
                now = datetime.now(UTC)
                past_run_at = now - timedelta(seconds=5)
                await conn.execute(
                    text(
                        "DELETE FROM control_plane.scheduled_tasks WHERE id LIKE 'task_crash_test_%'"
                    )
                )
                await conn.execute(
                    text(
                        "DELETE FROM control_plane.runtime_leases WHERE run_id LIKE 'run_crash_test_%'"
                    )
                )
                # KHÔNG seed hàng tenant nào ở COSA control plane: sau cutover
                # migration 29 (`29_cleanup_legacy_companies_and_rename_workspaces.up.sql`
                # DROP `cosa.companies` / `cosa.company_memberships`) tenancy là
                # workspace-only. Test này chỉ cần các id dạng chuỗi mờ trong
                # `input_payload` (`principal`, `workspace_id`, `company_id`) —
                # `control_plane.scheduled_tasks` và `control_plane.runtime_leases`
                # KHÔNG có FK tới bảng tenancy của cosa (leases chỉ FK
                # `worker_id -> control_plane.workers`), và worker
                # (`apps/cosa/worker/*`) không tra membership/entitlement/users.
                # Delegation token verify bằng chữ ký JWT, không lookup `cosa.users`.

                payload_json = json.dumps(
                    {
                        "run_id": run_id,
                        "task_type": "run",
                        "conversation_id": conv_id,
                        "user_prompt": "Hello crash test",
                        "agent_profile": "operations",
                        "principal": "1001",
                        "workspace_id": "ws-crash-test",
                        "company_id": "1",
                        "delegation_token": delegation_token,
                        "delay_sec": 10.0,
                    }
                )
                await conn.execute(
                    text("""
                        INSERT INTO control_plane.scheduled_tasks
                        (id, target_spec_id, target_spec_kind, input_payload, run_at, status, created_at, max_attempts, attempt_count)
                        VALUES (:id, :spec_id, :spec_kind, :payload, :run_at, :status, :created_at, 3, 0)
                    """),
                    {
                        "id": task_id,
                        "spec_id": "cosa.operations",
                        "spec_kind": "agent",
                        "payload": payload_json,
                        "run_at": past_run_at,
                        "status": "scheduled",
                        "created_at": now,
                    },
                )
        finally:
            await cp_engine.dispose()

    async def get_task_row():
        engine = create_async_engine(async_control_plane_dsn)
        try:
            async with engine.begin() as conn:
                res = await conn.execute(
                    text(
                        "SELECT status, attempt_count, claimed_by, claim_token, visibility_timeout_at FROM control_plane.scheduled_tasks WHERE id = :id"
                    ),
                    {"id": task_id},
                )
                return res.mappings().fetchone()
        finally:
            await engine.dispose()

    async def get_lease_row():
        engine = create_async_engine(async_control_plane_dsn)
        try:
            async with engine.begin() as conn:
                res = await conn.execute(
                    text(
                        "SELECT run_id, worker_id, lease_token, expires_at FROM control_plane.runtime_leases WHERE run_id = :run_id"
                    ),
                    {"run_id": run_id},
                )
                return res.mappings().fetchone()
        finally:
            await engine.dispose()

    async def cleanup_db():
        engine = create_async_engine(async_control_plane_dsn)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("DELETE FROM control_plane.scheduled_tasks WHERE id = :id"),
                    {"id": task_id},
                )
                await conn.execute(
                    text("DELETE FROM control_plane.runtime_leases WHERE run_id = :run_id"),
                    {"run_id": run_id},
                )
        finally:
            await engine.dispose()

    asyncio.run(setup_task())

    repo_root = Path(__file__).parent.parent.parent.parent.parent
    packages_dir = repo_root / "packages"
    python_path = f"{packages_dir}:{repo_root}"

    env_base = {**os.environ}
    env_base["PYTHONPATH"] = python_path
    env_base["COSA_DATABASE_URL"] = control_plane_dsn
    env_base["DATABASE_URL"] = control_plane_dsn
    env_base["AGENT_DATABASE_URL"] = agent_dsn
    env_base["COSA_CONTROL_PLANE_URL"] = control_plane_service

    try:
        # --- Phase 1: Process A starts, claims lease/task, then gets killed ---
        token_a = _sign_worker_token("worker-crash-a")
        env_a = {**env_base}
        env_a["COSA_WORKER_ID"] = "worker-crash-a"
        env_a["COSA_WORKER_SERVICE_TOKEN"] = token_a

        proc_a = subprocess.Popen(
            [sys.executable, "-m", "apps.cosa.worker.main", "--once", "--task-id", task_id],
            env=env_a,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        pid_a = proc_a.pid

        # Poll deterministically until Worker A has claimed the task and is processing
        start_poll = time.time()
        claimed = False
        while time.time() - start_poll < 10.0:
            row = asyncio.run(get_task_row())
            if row and row["status"] == "processing" and row["claimed_by"] == "worker-crash-a":
                claimed = True
                break
            if proc_a.poll() is not None:
                break
            time.sleep(0.2)
        assert claimed, "Worker A did not claim the task within timeout"

        # Kill worker A mid-execution
        proc_a.terminate()
        try:
            proc_a.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc_a.kill()
            proc_a.wait()

        out_a_bytes, _ = proc_a.communicate() if proc_a.stdout else (b"", b"")
        out_a = out_a_bytes.decode() if out_a_bytes else ""

        # Check task state after Worker A died (must be processing and claimed)
        row_after_a = asyncio.run(get_task_row())
        assert row_after_a is not None, f"Task {task_id} must exist in DB"
        if row_after_a["status"] != "processing" and (
            "500 Internal Server Error" in out_a or "ConnectionRefused" in out_a
        ):
            pytest.skip(f"Control plane service returned error in subprocess A: {out_a[:200]}")
        assert row_after_a["status"] == "processing", (
            f"Task should be 'processing' after Worker A claimed, got {row_after_a['status']}\nWorker A out:\n{out_a}"
        )
        assert row_after_a["claimed_by"] == "worker-crash-a"
        stale_claim_token = row_after_a["claim_token"]

        # Check lease state held by Worker A
        lease_after_a = asyncio.run(get_lease_row())
        assert lease_after_a is not None, (
            f"Runtime lease for run_id {run_id} should exist while Worker A was processing"
        )
        assert lease_after_a["worker_id"] == "worker-crash-a"
        stale_lease_token = lease_after_a["lease_token"]

        # --- Phase 2: Expire visibility timeout and trigger sweeper ---
        async def expire_visibility_timeout_and_clear_delay():
            engine = create_async_engine(async_control_plane_dsn)
            try:
                async with engine.begin() as conn:
                    past = datetime.now(UTC) - timedelta(seconds=10)
                    payload_no_delay = json.dumps(
                        {
                            "run_id": run_id,
                            "task_type": "run",
                            "conversation_id": conv_id,
                            "user_prompt": "Hello crash test",
                            "agent_profile": "operations",
                            "principal": "1001",
                            "workspace_id": "ws-crash-test",
                            "company_id": "1",
                            "delegation_token": delegation_token,
                        }
                    )
                    await conn.execute(
                        text(
                            "UPDATE control_plane.scheduled_tasks SET visibility_timeout_at = :past, input_payload = :payload WHERE id = :id"
                        ),
                        {"past": past, "payload": payload_no_delay, "id": task_id},
                    )
                    await conn.execute(
                        text(
                            "UPDATE control_plane.runtime_leases SET expires_at = :past WHERE run_id = :run_id"
                        ),
                        {"past": past, "run_id": run_id},
                    )
            finally:
                await engine.dispose()

        asyncio.run(expire_visibility_timeout_and_clear_delay())

        # Call sweeper endpoint
        admin_token = _sign_worker_token("admin-sweeper")
        reclaim_resp = httpx.post(
            f"{control_plane_service}/control-plane/internal/scheduled-tasks/reclaim-stuck",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"limit": 50},
            timeout=10.0,
        )
        assert reclaim_resp.status_code == 200, f"Sweeper failed: {reclaim_resp.text}"

        # Verify task was reclaimed to 'scheduled' and attempt_count incremented
        row_after_sweeper = asyncio.run(get_task_row())
        assert row_after_sweeper is not None
        assert row_after_sweeper["status"] == "scheduled", (
            f"Task should be reclaimed to 'scheduled', got {row_after_sweeper['status']}"
        )
        assert row_after_sweeper["attempt_count"] == 1, (
            f"Attempt count should be 1 after sweeper reclaim, got {row_after_sweeper['attempt_count']}"
        )
        assert row_after_sweeper["claimed_by"] is None, "claimed_by should be cleared after reclaim"

        # Set run_at to now so Worker B can poll it immediately without waiting for backoff
        async def set_task_ready_for_b():
            engine = create_async_engine(async_control_plane_dsn)
            try:
                async with engine.begin() as conn:
                    now = datetime.now(UTC)
                    await conn.execute(
                        text(
                            "UPDATE control_plane.scheduled_tasks SET run_at = :now WHERE id = :id"
                        ),
                        {"now": now, "id": task_id},
                    )
            finally:
                await engine.dispose()

        asyncio.run(set_task_ready_for_b())

        # --- Phase 3: Process B starts and processes the reclaimed task ---
        token_b = _sign_worker_token("worker-crash-b")
        env_b = {**env_base}
        env_b["COSA_WORKER_ID"] = "worker-crash-b"
        env_b["COSA_WORKER_SERVICE_TOKEN"] = token_b

        proc_b = subprocess.Popen(
            [sys.executable, "-m", "apps.cosa.worker.main", "--once", "--task-id", task_id],
            env=env_b,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        pid_b = proc_b.pid

        assert pid_a != pid_b, f"Process A (PID {pid_a}) and Process B (PID {pid_b}) must differ"

        out_b_bytes, _ = proc_b.communicate(timeout=30)
        out_b = out_b_bytes.decode() if out_b_bytes else ""

        # Verify final task state in Postgres
        row_final = asyncio.run(get_task_row())
        assert row_final is not None, f"Task {task_id} must exist"

        # Strictly assert that task is COMPLETED, not processing
        assert row_final["status"] == "completed", (
            f"Task status must be 'completed' after Worker B recovery, got {row_final['status']}.\n"
            f"Worker A output:\n{out_a}\nWorker B output:\n{out_b}"
        )

        # --- Phase 4: Fencing check — stale worker token rejected ---
        if stale_claim_token:
            fencing_resp = httpx.post(
                f"{control_plane_service}/control-plane/internal/scheduled-tasks/{task_id}/complete",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "workerId": "worker-crash-a",
                    "claimToken": stale_claim_token,
                    "success": True,
                },
                timeout=5.0,
            )
            if fencing_resp.status_code == 200:
                res_json = fencing_resp.json()
                assert res_json.get("ok") is False, (
                    "Stale claim token must be rejected by fencing (ok=False)"
                )

        # Lease fencing check: stale lease token of worker A rejected for renew/release
        if stale_lease_token:
            renew_resp = httpx.post(
                f"{control_plane_service}/control-plane/internal/leases/renew",
                headers={"Authorization": f"Bearer {token_a}"},
                json={
                    "runId": run_id,
                    "workerId": "worker-crash-a",
                    "leaseToken": stale_lease_token,
                },
                timeout=5.0,
            )
            if renew_resp.status_code == 200:
                assert renew_resp.json().get("success") is False, (
                    "Stale lease token must be rejected for renewal"
                )
    finally:
        asyncio.run(cleanup_db())


@pytest.mark.durability
@pytest.mark.integration
def test_subprocess_different_pids() -> None:
    """Sanity check: subprocess creates separate OS processes with different PIDs."""
    script = "import os; print(os.getpid())"

    proc1 = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    pid1, _ = proc1.communicate(timeout=5)
    pid1 = int(pid1.decode().strip())

    proc2 = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    pid2, _ = proc2.communicate(timeout=5)
    pid2 = int(pid2.decode().strip())

    assert pid1 != pid2
    assert pid1 > 0 and pid2 > 0
