"""Postgres SELECT FOR UPDATE Lease Mutual Exclusion Test — THẬT qua OS process.

Kiểm chứng tính loại trừ tương hỗ (mutual exclusion) và chống split-brain
của control-plane lease (`services/cosa/services/control-plane-lease.service.ts`
và `HttpControlPlaneLeaseClient`) trên PostgreSQL thật qua nhiều OS process thật
(Part 1C §1C.2, CLAUDE.md #6).

Các kịch bản kiểm chứng:
1. Concurrency Race giữa 2 OS subprocess: 2 process thật cùng cố acquire lease
   cho cùng 1 `run_id` đồng thời -> đúng 1 process thành công, 1 process nhận
   từ chối do `SELECT ... FOR UPDATE` row lock trong transaction PostgreSQL.
2. Lifecycle Fencing & Expiry Handover:
   - Worker A giữ lease hợp lệ -> Worker B bị từ chối.
   - Worker B cố renew/release lease của A bằng token sai / ID khác -> bị từ chối.
   - Worker A dừng heartbeat/chết -> sau TTL hết hạn, Worker B acquire thành công
     với lease token mới.
   - Worker A (stale) cố renew bằng lease token cũ -> bị từ chối bởi fencing.
3. Parallel Independent Leases:
   - 2 OS process acquire lease cho 2 `run_id` khác nhau cùng lúc -> cả 2 đều thành
     công song song mà không bị chặn lẫn nhau.
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
from pathlib import Path

import httpx
import jwt
import pytest
from agent_core.runs.control_plane_client import HttpControlPlaneLeaseClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

__all__ = [
    "test_independent_run_ids_parallel_acquisition",
    "test_lease_lifecycle_fencing_and_expiry_handover",
    "test_real_concurrent_subprocess_lease_race",
]


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
        os.environ.get("CONTROL_PLANE_TEST_DATABASE_URL")
        or os.environ.get("CONTROL_PLANE_DATABASE_URL")
        or os.environ.get("AGENT_CORE_TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
    )
    if not dsn:
        pytest.skip("CONTROL_PLANE_TEST_DATABASE_URL/DATABASE_URL không set")

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
def control_plane_service(control_plane_dsn: str):
    """Start `encore run` for services/cosa control-plane service."""
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
def test_real_concurrent_subprocess_lease_race(
    control_plane_service: str,
    async_control_plane_dsn: str,
) -> None:
    """Spawn 2 real OS subprocesses trying to acquire lease on the SAME run_id concurrently.

    Proves that PostgreSQL SELECT ... FOR UPDATE ensures strict mutual exclusion:
    - Exactly 1 process acquires the lease (success=True).
    - Exactly 1 process fails to acquire the lease (success=False).
    - In DB, exactly 1 lease row exists corresponding to the winner.
    """
    run_id = f"run_race_{uuid.uuid4().hex[:8]}"
    worker_1 = f"worker_race_1_{uuid.uuid4().hex[:6]}"
    worker_2 = f"worker_race_2_{uuid.uuid4().hex[:6]}"
    token_1 = _sign_worker_token(worker_1)
    token_2 = _sign_worker_token(worker_2)

    script = """
import asyncio, sys, json
from agent_core.runs.control_plane_client import HttpControlPlaneLeaseClient

async def main():
    base_url = sys.argv[1]
    run_id = sys.argv[2]
    worker_id = sys.argv[3]
    token = sys.argv[4]

    client = HttpControlPlaneLeaseClient(base_url=base_url, token=token)
    try:
        res = await client.acquire_lease(run_id, worker_id, ttl_sec=30)
        output = {
            "worker_id": worker_id,
            "success": res.success,
            "lease_token": res.lease.lease_token if res.lease else None,
            "reason": res.reason,
        }
        print(json.dumps(output))
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
"""

    repo_root = Path(__file__).parent.parent.parent.parent.parent
    packages_dir = repo_root / "packages"
    python_path = f"{packages_dir}:{repo_root}"
    env_base = {**os.environ, "PYTHONPATH": python_path}

    async def cleanup():
        engine = create_async_engine(async_control_plane_dsn)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("DELETE FROM control_plane.runtime_leases WHERE run_id = :run_id"),
                    {"run_id": run_id},
                )
        finally:
            await engine.dispose()

    try:
        # Launch 2 separate OS subprocesses concurrently
        proc1 = subprocess.Popen(
            [sys.executable, "-c", script, control_plane_service, run_id, worker_1, token_1],
            env=env_base,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        proc2 = subprocess.Popen(
            [sys.executable, "-c", script, control_plane_service, run_id, worker_2, token_2],
            env=env_base,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        out1_b, err1_b = proc1.communicate(timeout=15)
        out2_b, err2_b = proc2.communicate(timeout=15)

        assert proc1.returncode == 0, f"Process 1 failed with stderr:\n{err1_b.decode()}"
        assert proc2.returncode == 0, f"Process 2 failed with stderr:\n{err2_b.decode()}"

        res1 = json.loads(out1_b.decode().strip())
        res2 = json.loads(out2_b.decode().strip())

        # Assert exactly one winner and one loser
        results = [res1, res2]
        winners = [r for r in results if r["success"] is True]
        losers = [r for r in results if r["success"] is False]

        assert len(winners) == 1, f"Expected exactly 1 winner, got {len(winners)}: {results}"
        assert len(losers) == 1, f"Expected exactly 1 loser, got {len(losers)}: {results}"

        winner = winners[0]
        loser = losers[0]

        assert winner["lease_token"] is not None, "Winner must have a valid lease token"
        assert loser["lease_token"] is None, "Loser must not have a lease token"
        assert winner["worker_id"] in loser["reason"], (
            f"Loser's reason should indicate that run is currently leased by winner ({winner['worker_id']}), "
            f"got reason: {loser['reason']}"
        )

        # Verify state in PostgreSQL
        async def verify_db():
            engine = create_async_engine(async_control_plane_dsn)
            try:
                async with engine.begin() as conn:
                    rows = (
                        (
                            await conn.execute(
                                text(
                                    "SELECT worker_id, lease_token FROM control_plane.runtime_leases WHERE run_id = :run_id"
                                ),
                                {"run_id": run_id},
                            )
                        )
                        .mappings()
                        .fetchall()
                    )
                    return rows
            finally:
                await engine.dispose()

        db_rows = asyncio.run(verify_db())
        assert len(db_rows) == 1, f"Expected exactly 1 lease row in DB, got {len(db_rows)}"
        assert db_rows[0]["worker_id"] == winner["worker_id"]
        assert db_rows[0]["lease_token"] == winner["lease_token"]

    finally:
        asyncio.run(cleanup())


@pytest.mark.durability
@pytest.mark.integration
def test_lease_lifecycle_fencing_and_expiry_handover(
    control_plane_service: str,
    async_control_plane_dsn: str,
) -> None:
    """Test full lease lifecycle across 2 distinct worker identities:

    1. Worker A acquires lease with short TTL (3s).
    2. Worker B attempts acquire -> rejected.
    3. Worker B attempts renew/release Worker A's lease -> rejected.
    4. Worker A successfully renews with valid token.
    5. Worker A stops heartbeating and TTL expires.
    6. Worker B acquires expired lease -> succeeds with new lease token.
    7. Stale Worker A attempts renew/release -> rejected by fencing.
    8. Worker B releases lease -> successfully removed.
    """
    run_id = f"run_lifecycle_{uuid.uuid4().hex[:8]}"
    worker_a = f"worker_life_a_{uuid.uuid4().hex[:6]}"
    worker_b = f"worker_life_b_{uuid.uuid4().hex[:6]}"
    token_a = _sign_worker_token(worker_a)
    token_b = _sign_worker_token(worker_b)

    async def cleanup():
        engine = create_async_engine(async_control_plane_dsn)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("DELETE FROM control_plane.runtime_leases WHERE run_id = :run_id"),
                    {"run_id": run_id},
                )
        finally:
            await engine.dispose()

    async def run_test():
        client_a = HttpControlPlaneLeaseClient(base_url=control_plane_service, token=token_a)
        client_b = HttpControlPlaneLeaseClient(base_url=control_plane_service, token=token_b)
        try:
            # Step 1: Worker A acquires lease (TTL = 3s)
            acq_a = await client_a.acquire_lease(run_id, worker_a, ttl_sec=3)
            assert acq_a.success is True, f"Worker A should acquire lease: {acq_a.reason}"
            assert acq_a.lease is not None
            lease_token_a = acq_a.lease.lease_token

            # Step 2: Worker B attempts to acquire same run_id -> rejected
            acq_b1 = await client_b.acquire_lease(run_id, worker_b, ttl_sec=10)
            assert acq_b1.success is False, "Worker B must not acquire active lease of Worker A"
            assert worker_a in acq_b1.reason

            # Step 3: Fencing check — Worker B tries to renew/release with fake token or Worker B's token
            renew_fake = await client_b.renew_lease(run_id, worker_b, lease_token="fake_token_1234")
            assert renew_fake is False, "Renew with fake token must fail"

            renew_b_cross = await client_b.renew_lease(run_id, worker_b, lease_token=lease_token_a)
            assert renew_b_cross is False, "Worker B cannot renew Worker A's lease"

            release_b_cross = await client_b.release_lease(
                run_id, worker_b, lease_token=lease_token_a
            )
            assert release_b_cross is False, "Worker B cannot release Worker A's lease"

            # Step 4: Worker A renews own lease with valid token -> success
            renew_a = await client_a.renew_lease(
                run_id, worker_a, lease_token=lease_token_a, additional_ttl_sec=3
            )
            assert renew_a is True, "Worker A must successfully renew own lease"

            # Step 5: Worker A stops heartbeating. Wait for TTL to expire (3.5s)
            await asyncio.sleep(3.5)

            # Step 6: Worker B acquires expired lease -> succeeds with NEW lease token
            acq_b2 = await client_b.acquire_lease(run_id, worker_b, ttl_sec=10)
            assert acq_b2.success is True, f"Worker B must acquire expired lease: {acq_b2.reason}"
            assert acq_b2.lease is not None
            lease_token_b = acq_b2.lease.lease_token
            assert lease_token_b != lease_token_a, (
                "New lease token must differ from old expired token"
            )

            # Step 7: Stale Worker A tries to renew or release with old lease token -> rejected
            stale_renew = await client_a.renew_lease(run_id, worker_a, lease_token=lease_token_a)
            assert stale_renew is False, "Stale Worker A renewal must be rejected"

            stale_release = await client_a.release_lease(
                run_id, worker_a, lease_token=lease_token_a
            )
            assert stale_release is False, "Stale Worker A release must be rejected"

            # Step 8: Worker B releases valid lease
            released = await client_b.release_lease(run_id, worker_b, lease_token=lease_token_b)
            assert released is True, "Worker B must successfully release lease"

            # Verify DB is clean
            engine = create_async_engine(async_control_plane_dsn)
            try:
                async with engine.begin() as conn:
                    rows = (
                        await conn.execute(
                            text(
                                "SELECT * FROM control_plane.runtime_leases WHERE run_id = :run_id"
                            ),
                            {"run_id": run_id},
                        )
                    ).fetchall()
                    assert len(rows) == 0, (
                        f"Lease row should be deleted after release, found: {rows}"
                    )
            finally:
                await engine.dispose()
        finally:
            await client_a.aclose()
            await client_b.aclose()

    try:
        asyncio.run(run_test())
    finally:
        asyncio.run(cleanup())


@pytest.mark.durability
@pytest.mark.integration
def test_independent_run_ids_parallel_acquisition(
    control_plane_service: str,
    async_control_plane_dsn: str,
) -> None:
    """Two separate OS subprocesses acquire leases on distinct run_ids concurrently.

    Verifies that FOR UPDATE locking on specific rows does not cause global deadlock
    or block non-conflicting run_ids.
    """
    run_id_1 = f"run_indep_1_{uuid.uuid4().hex[:8]}"
    run_id_2 = f"run_indep_2_{uuid.uuid4().hex[:8]}"
    worker_1 = f"worker_indep_1_{uuid.uuid4().hex[:6]}"
    worker_2 = f"worker_indep_2_{uuid.uuid4().hex[:6]}"
    token_1 = _sign_worker_token(worker_1)
    token_2 = _sign_worker_token(worker_2)

    script = """
import asyncio, sys, json
from agent_core.runs.control_plane_client import HttpControlPlaneLeaseClient

async def main():
    base_url = sys.argv[1]
    run_id = sys.argv[2]
    worker_id = sys.argv[3]
    token = sys.argv[4]

    client = HttpControlPlaneLeaseClient(base_url=base_url, token=token)
    try:
        res = await client.acquire_lease(run_id, worker_id, ttl_sec=30)
        output = {
            "worker_id": worker_id,
            "run_id": run_id,
            "success": res.success,
            "lease_token": res.lease.lease_token if res.lease else None,
        }
        print(json.dumps(output))
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
"""

    repo_root = Path(__file__).parent.parent.parent.parent.parent
    packages_dir = repo_root / "packages"
    python_path = f"{packages_dir}:{repo_root}"
    env_base = {**os.environ, "PYTHONPATH": python_path}

    async def cleanup():
        engine = create_async_engine(async_control_plane_dsn)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("DELETE FROM control_plane.runtime_leases WHERE run_id IN (:r1, :r2)"),
                    {"r1": run_id_1, "r2": run_id_2},
                )
        finally:
            await engine.dispose()

    try:
        proc1 = subprocess.Popen(
            [sys.executable, "-c", script, control_plane_service, run_id_1, worker_1, token_1],
            env=env_base,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        proc2 = subprocess.Popen(
            [sys.executable, "-c", script, control_plane_service, run_id_2, worker_2, token_2],
            env=env_base,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        out1_b, err1_b = proc1.communicate(timeout=15)
        out2_b, err2_b = proc2.communicate(timeout=15)

        assert proc1.returncode == 0, f"Process 1 failed: {err1_b.decode()}"
        assert proc2.returncode == 0, f"Process 2 failed: {err2_b.decode()}"

        res1 = json.loads(out1_b.decode().strip())
        res2 = json.loads(out2_b.decode().strip())

        assert res1["success"] is True, f"Process 1 should succeed: {res1}"
        assert res2["success"] is True, f"Process 2 should succeed: {res2}"
        assert res1["lease_token"] is not None
        assert res2["lease_token"] is not None
    finally:
        asyncio.run(cleanup())
