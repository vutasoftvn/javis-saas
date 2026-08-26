"""Wave 7 — HttpControlPlaneLeaseClient (ADR-CONTROLPLANE-001 H.3). Test dùng
httpx.MockTransport để verify request/response mapping đúng shape với
services/cosa/handlers/control-plane.handler.ts, KHÔNG cần services/cosa thật
đang chạy (không có Encore CLI/Postgres trong môi trường phát triển này)."""
from __future__ import annotations

import json

import httpx
import pytest

from agent_core.runs.control_plane_client import HttpControlPlaneLeaseClient


def _client_with_transport(handler) -> HttpControlPlaneLeaseClient:
    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(transport=transport)
    return HttpControlPlaneLeaseClient(base_url="http://control-plane.internal", client=inner)


@pytest.mark.asyncio
async def test_acquire_lease_success_maps_response_correctly():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "success": True,
                "leaseToken": "lease_abc123",
                "expiresAt": "2026-08-24T10:00:00.000Z",
                "reason": "Lease successfully acquired",
            },
        )

    client = _client_with_transport(handler)
    result = await client.acquire_lease("run_1", "worker_1", ttl_sec=90)

    assert captured["url"] == "http://control-plane.internal/control-plane/internal/leases/acquire"
    assert captured["body"] == {"runId": "run_1", "workerId": "worker_1", "ttlSec": 90}
    assert result.success is True
    assert result.lease is not None
    assert result.lease.lease_token == "lease_abc123"
    assert result.lease.run_id == "run_1"


@pytest.mark.asyncio
async def test_acquire_lease_failure_maps_reason():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"success": False, "reason": "Run 'run_1' is currently leased by worker 'worker_2' until ..."},
        )

    client = _client_with_transport(handler)
    result = await client.acquire_lease("run_1", "worker_1")

    assert result.success is False
    assert result.lease is None
    assert "leased by worker" in result.reason


@pytest.mark.asyncio
async def test_renew_and_release_lease_map_success_flag():
    def make_handler(path: str):
        def handler(request: httpx.Request) -> httpx.Response:
            assert path in str(request.url)
            return httpx.Response(200, json={"success": True})

        return handler

    renew_client = _client_with_transport(make_handler("/leases/renew"))
    assert await renew_client.renew_lease("run_1", "worker_1", "lease_abc123") is True

    release_client = _client_with_transport(make_handler("/leases/release"))
    assert await release_client.release_lease("run_1", "worker_1", "lease_abc123") is True


@pytest.mark.asyncio
async def test_lease_client_sends_authorization_header():
    captured_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(request.headers)
        return httpx.Response(200, json={"success": True})

    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(transport=transport)
    client = HttpControlPlaneLeaseClient(
        base_url="http://control-plane.internal",
        service_token="test-worker-token-456",
        client=inner,
    )
    await client.renew_lease("run_1", "worker_1", "token_1")

    assert captured_headers.get("authorization") == "Bearer test-worker-token-456"

