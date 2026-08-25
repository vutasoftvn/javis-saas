"""HttpControlPlaneSchedulerClient (ADR-CONTROLPLANE-001 H.3) — test dùng
httpx.MockTransport để verify request/response mapping đúng shape với
services/cosa/handlers/control-plane.handler.ts, KHÔNG cần services/cosa thật
đang chạy (không có Encore CLI/Postgres trong môi trường phát triển này)."""
from __future__ import annotations

import json
import uuid

import httpx
import pytest

from agent_core.coordination.control_plane_scheduler_client import HttpControlPlaneSchedulerClient


def _client_with_transport(handler) -> HttpControlPlaneSchedulerClient:
    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(transport=transport)
    return HttpControlPlaneSchedulerClient(base_url="http://control-plane.internal", client=inner)


@pytest.mark.asyncio
async def test_schedule_maps_request_and_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "task_abc123",
                "coalescingKey": "conv_1:run",
                "targetSpecId": "cosa.operations",
                "targetSpecKind": "agent",
                "inputPayload": {"prompt": "hi"},
                "runAt": "2026-08-25T10:00:00.000Z",
                "status": "scheduled",
                "createdAt": "2026-08-25T10:00:00.000Z",
            },
        )

    client = _client_with_transport(handler)
    record = await client.schedule(
        target_spec_id="cosa.operations", input_payload={"prompt": "hi"}, coalescing_key="conv_1:run"
    )

    assert captured["url"] == "http://control-plane.internal/control-plane/internal/scheduled-tasks"
    assert captured["body"]["targetSpecId"] == "cosa.operations"
    assert captured["body"]["coalescingKey"] == "conv_1:run"
    assert record.task_id == "task_abc123"
    assert record.status == "scheduled"


@pytest.mark.asyncio
async def test_poll_due_tasks_maps_list():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["limit"] == "5"
        return httpx.Response(
            200,
            json={
                "tasks": [
                    {
                        "id": "task_1",
                        "coalescingKey": None,
                        "targetSpecId": "cosa.finance",
                        "targetSpecKind": "agent",
                        "inputPayload": {},
                        "runAt": "2026-08-25T10:00:00.000Z",
                        "status": "processing",
                        "createdAt": "2026-08-25T09:59:00.000Z",
                    }
                ]
            },
        )

    client = _client_with_transport(handler)
    tasks = await client.poll_due_tasks(limit=5)
    assert len(tasks) == 1
    assert tasks[0].task_id == "task_1"
    assert tasks[0].status == "processing"


@pytest.mark.asyncio
async def test_poll_due_tasks_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"tasks": []})

    client = _client_with_transport(handler)
    assert await client.poll_due_tasks() == []


@pytest.mark.asyncio
async def test_complete_task_hits_correct_path():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    client = _client_with_transport(handler)
    await client.complete_task("task_abc123", success=False)

    assert captured["url"] == "http://control-plane.internal/control-plane/internal/scheduled-tasks/task_abc123/complete"
    assert captured["body"] == {"success": False}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sweep_stuck_tasks_resets_expired_leases():
    """Test sweeper function — TDD RED phase.

    Verify rằng sweep_stuck_tasks():
    1. Finds tasks với status='processing' và lease đã hết hạn
    2. Resets task về 'scheduled' để worker khác có thể claim
    3. Returns số task đã reset

    Yêu cầu: CONTROL_PLANE_DATABASE_URL phải trỏ Postgres thật.
    """
    import os
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from agent_core.coordination.control_plane_scheduler_client import sweep_stuck_tasks

    dsn = os.environ.get("CONTROL_PLANE_DATABASE_URL")
    if not dsn:
        pytest.skip("CONTROL_PLANE_DATABASE_URL not set — need real Postgres")

    # Normalize DSN: replace 'postgres' hostname with '127.0.0.1' for host access
    dsn = dsn.replace("postgres://", "postgresql://")
    # Handle 'postgres:' in connection string (convert postgres:5432 to 127.0.0.1:5432)
    parts = dsn.split("@")
    if len(parts) == 2 and ":5432" in parts[1]:
        prefix = parts[0]
        suffix = parts[1]
        if suffix.startswith("postgres:"):
            dsn = prefix + "@127.0.0.1:" + suffix[len("postgres:"):]

    # Use async driver for SQLAlchemy
    async_dsn = dsn
    if "postgresql+asyncpg://" not in async_dsn:
        async_dsn = async_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(async_dsn)

    # Create a stuck task: processing status + expired lease
    async with engine.begin() as conn:
        # Insert a worker
        worker_id = "test-sweep-worker"
        await conn.execute(
            text("""
                INSERT INTO control_plane.workers (id, runtime_kind, status)
                VALUES (:id, :kind, :status)
                ON CONFLICT (id) DO UPDATE SET runtime_kind = :kind
            """),
            {"id": worker_id, "kind": "test", "status": "online"},
        )

        # Insert an expired lease
        run_id = f"run_stuck_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        expired_at = now - timedelta(seconds=30)  # expired 30 seconds ago
        await conn.execute(
            text("""
                INSERT INTO control_plane.runtime_leases (run_id, worker_id, lease_token, acquired_at, expires_at, heartbeat_interval_sec)
                VALUES (:run_id, :worker_id, :token, :acquired_at, :expires_at, :interval)
                ON CONFLICT (run_id) DO UPDATE SET expires_at = :expires_at
            """),
            {
                "run_id": run_id,
                "worker_id": worker_id,
                "token": f"token_{uuid.uuid4().hex[:12]}",
                "acquired_at": expired_at - timedelta(seconds=60),
                "expires_at": expired_at,
                "interval": 20,
            },
        )

        # Insert a processing task with matching run_id in payload
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        await conn.execute(
            text("""
                INSERT INTO control_plane.scheduled_tasks (id, target_spec_id, target_spec_kind, input_payload, run_at, status, created_at)
                VALUES (:id, :spec_id, :spec_kind, :payload, :run_at, :status, :created_at)
                ON CONFLICT (id) DO UPDATE SET status = :status
            """),
            {
                "id": task_id,
                "spec_id": "test.spec",
                "spec_kind": "agent",
                "payload": json.dumps({"run_id": run_id, "task_type": "run"}),
                "run_at": now - timedelta(minutes=1),
                "status": "processing",
                "created_at": now - timedelta(minutes=1),
            },
        )

    try:
        # Call sweeper
        count = await sweep_stuck_tasks(dsn, stale_after_seconds=10)
        assert count >= 1, f"Sweeper should reset at least 1 task, got {count}"

        # Verify task was reset to 'scheduled'
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT status FROM control_plane.scheduled_tasks WHERE id = :id"),
                {"id": task_id},
            )
            row = result.fetchone()
            assert row is not None, f"Task {task_id} should exist"
            assert row[0] == "scheduled", f"Task status should be reset to 'scheduled', got {row[0]}"

    finally:
        await engine.dispose()
