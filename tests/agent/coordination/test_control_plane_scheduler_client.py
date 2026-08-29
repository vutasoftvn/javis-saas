"""HttpControlPlaneSchedulerClient (ADR-CONTROLPLANE-001 H.3, Phase 3 Durable
Queue Recovery) — test dùng httpx.MockTransport để verify request/response
mapping đúng shape với services/cosa/handlers/control-plane.handler.ts,
KHÔNG cần services/cosa thật đang chạy (không có Encore CLI/Postgres trong
môi trường phát triển này). Sweeper (reclaim_stuck_tasks) giờ chạy hoàn toàn
phía services/cosa (cron + service function) — verify bằng vitest ở
services/cosa/tests/control-plane-scheduler.test.ts, không còn Python
sweep_stuck_tasks() (đã xoá, coupling sai qua input_payload->>'run_id')."""
from __future__ import annotations

import json

import httpx
import pytest

from agent.coordination.control_plane_scheduler_client import HttpControlPlaneSchedulerClient


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
                "attemptCount": 0,
                "maxAttempts": 5,
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
async def test_poll_due_tasks_claims_with_worker_id_and_maps_claim_token():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
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
                        "claimToken": "claim_abc123",
                        "attemptCount": 0,
                        "maxAttempts": 5,
                    }
                ]
            },
        )

    client = _client_with_transport(handler)
    tasks = await client.poll_due_tasks(worker_id="worker_1", limit=5)

    assert captured["url"] == "http://control-plane.internal/control-plane/internal/scheduled-tasks/poll"
    assert captured["body"] == {"workerId": "worker_1", "limit": 5}
    assert len(tasks) == 1
    assert tasks[0].task_id == "task_1"
    assert tasks[0].status == "processing"
    assert tasks[0].claim_token == "claim_abc123"


@pytest.mark.asyncio
async def test_poll_due_tasks_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"tasks": []})

    client = _client_with_transport(handler)
    assert await client.poll_due_tasks(worker_id="worker_1") == []


@pytest.mark.asyncio
async def test_heartbeat_task_hits_correct_path_with_fencing():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    client = _client_with_transport(handler)
    ok = await client.heartbeat_task("task_abc123", worker_id="worker_1", claim_token="claim_xyz")

    assert captured["url"] == "http://control-plane.internal/control-plane/internal/scheduled-tasks/task_abc123/heartbeat"
    assert captured["body"] == {"taskId": "task_abc123", "workerId": "worker_1", "claimToken": "claim_xyz"}
    assert ok is True


@pytest.mark.asyncio
async def test_complete_task_hits_correct_path_with_fencing():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True, "finalStatus": "failed"})

    client = _client_with_transport(handler)
    ok = await client.complete_task(
        "task_abc123", worker_id="worker_1", claim_token="claim_xyz", success=False, error="boom"
    )

    assert captured["url"] == "http://control-plane.internal/control-plane/internal/scheduled-tasks/task_abc123/complete"
    assert captured["body"] == {
        "taskId": "task_abc123",
        "workerId": "worker_1",
        "claimToken": "claim_xyz",
        "success": False,
        "error": "boom",
    }
    assert ok is True


@pytest.mark.asyncio
async def test_complete_task_rejected_by_fencing_returns_false():
    """Worker cũ đã bị sweeper reclaim (claim_token đổi) cố gọi complete_task
    — server trả `ok: false`, client KHÔNG được raise (đây là kết quả hợp lệ
    cần caller tự xử lý, không phải lỗi HTTP)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "finalStatus": "scheduled"})

    client = _client_with_transport(handler)
    ok = await client.complete_task("task_abc123", worker_id="stale_worker", claim_token="stale_claim", success=True)

    assert ok is False


@pytest.mark.asyncio
async def test_scheduler_client_sends_authorization_header():
    captured_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(request.headers)
        return httpx.Response(200, json={"tasks": []})

    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(transport=transport)
    client = HttpControlPlaneSchedulerClient(
        base_url="http://control-plane.internal",
        service_token="test-worker-token-xyz",
        client=inner,
    )
    await client.poll_due_tasks(worker_id="worker_1")

    assert captured_headers.get("authorization") == "Bearer test-worker-token-xyz"

