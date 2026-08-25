"""HttpControlPlaneSchedulerClient (ADR-CONTROLPLANE-001 H.3) — test dùng
httpx.MockTransport để verify request/response mapping đúng shape với
services/cosa/handlers/control-plane.handler.ts, KHÔNG cần services/cosa thật
đang chạy (không có Encore CLI/Postgres trong môi trường phát triển này)."""
from __future__ import annotations

import json

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
