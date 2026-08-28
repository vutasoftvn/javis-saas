"""Unit & Integration tests for COSA Worker Health and Readiness endpoints (Part 1E §1E.1)."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from agent_core.coordination.scheduler import RunScheduler
from agent_core.runs.leases import RunLeaseManager
from fastapi.testclient import TestClient

from apps.cosa.worker.health import (
    WorkerHealthState,
    check_lease_store_health,
    check_scheduler_health,
    create_worker_health_app,
)


class MockPlane:
    """Mock plane with configurable scheduler and lease_client."""

    def __init__(self, scheduler=None, lease_client=None):
        self.scheduler = scheduler if scheduler is not None else RunScheduler()
        self.lease_client = lease_client if lease_client is not None else RunLeaseManager()


@pytest.fixture
def health_state() -> WorkerHealthState:
    return WorkerHealthState(poll_interval_sec=1.0)


@pytest.fixture
def mock_plane() -> MockPlane:
    return MockPlane()


def test_worker_live_endpoint(mock_plane, health_state):
    """GET /live returns 200 when process is running."""
    app = create_worker_health_app(mock_plane, health_state, worker_id="test_worker_1")
    client = TestClient(app)

    response = client.get("/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "cosa-worker"
    assert data["worker_id"] == "test_worker_1"
    assert data["live"] is True


def test_worker_ready_fails_before_first_poll(mock_plane, health_state):
    """GET /ready returns 503 when worker has not polled yet (last_poll_ts is None)."""
    health_state.last_poll_ts = None
    app = create_worker_health_app(mock_plane, health_state, worker_id="test_worker_1")
    client = TestClient(app)

    response = client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["checks"]["polling"] is False
    assert data["checks"]["scheduler"] is True
    assert data["checks"]["lease_store"] is True


def test_worker_ready_passes_after_first_poll(mock_plane, health_state):
    """GET /ready returns 200 after first polling cycle succeeds."""
    health_state.last_poll_ts = time.monotonic()
    app = create_worker_health_app(mock_plane, health_state, worker_id="test_worker_1")
    client = TestClient(app)

    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["polling"] is True
    assert data["checks"]["scheduler"] is True
    assert data["checks"]["lease_store"] is True


def test_worker_ready_fails_when_scheduler_down(health_state):
    """GET /ready returns 503 when scheduler is down or unreachable."""
    health_state.last_poll_ts = time.monotonic()

    bad_scheduler = MagicMock()
    bad_scheduler.is_healthy = AsyncMock(return_value=False)
    plane = MockPlane(scheduler=bad_scheduler)

    app = create_worker_health_app(plane, health_state, worker_id="test_worker_1")
    client = TestClient(app)

    response = client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["checks"]["scheduler"] is False
    assert data["checks"]["polling"] is True
    assert data["checks"]["lease_store"] is True


def test_worker_ready_fails_when_lease_store_down(health_state):
    """GET /ready returns 503 when lease store is down or unreachable."""
    health_state.last_poll_ts = time.monotonic()

    bad_lease = MagicMock()
    bad_lease.is_healthy = AsyncMock(return_value=False)
    plane = MockPlane(lease_client=bad_lease)

    app = create_worker_health_app(plane, health_state, worker_id="test_worker_1")
    client = TestClient(app)

    response = client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["checks"]["lease_store"] is False
    assert data["checks"]["scheduler"] is True
    assert data["checks"]["polling"] is True


def test_worker_ready_fails_when_polling_stale(mock_plane, health_state):
    """GET /ready returns 503 when polling is stale (> 5x poll_interval)."""
    # 1.0s poll interval * 5 = 5s max elapsed
    health_state.poll_interval_sec = 1.0
    health_state.last_poll_ts = time.monotonic() - 10.0  # 10s ago

    app = create_worker_health_app(mock_plane, health_state, worker_id="test_worker_1")
    client = TestClient(app)

    response = client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["checks"]["polling"] is False


def test_worker_health_does_not_leak_secrets(mock_plane, health_state):
    """Health endpoints must not leak DSN, database passwords, or JWT secrets."""
    health_state.last_poll_ts = time.monotonic()
    app = create_worker_health_app(mock_plane, health_state, worker_id="worker_secure")
    client = TestClient(app)

    live_res = client.get("/live")
    ready_res = client.get("/ready")

    for resp in (live_res, ready_res):
        text = resp.text.lower()
        assert "password" not in text
        assert "secret" not in text
        assert "postgres://" not in text
        assert "postgresql://" not in text
        assert "bearer" not in text


@pytest.mark.asyncio
async def test_http_scheduler_and_lease_probing():
    """Verify HTTP client probe handles reachable / unreachable endpoints without crashing."""
    # Test HTTP probing against dummy base url
    scheduler_mock = MagicMock(spec=["_base_url", "_client"])
    scheduler_mock._base_url = "http://127.0.0.1:59999"  # Non-existent port
    scheduler_mock._client = httpx.AsyncClient(timeout=0.1)

    lease_mock = MagicMock(spec=["_base_url", "_client"])
    lease_mock._base_url = "http://127.0.0.1:59999"
    lease_mock._client = httpx.AsyncClient(timeout=0.1)

    try:
        ok = await check_scheduler_health(scheduler_mock)
        assert ok is False

        ok_lease = await check_lease_store_health(lease_mock)
        assert ok_lease is False
    finally:
        await scheduler_mock._client.aclose()
        await lease_mock._client.aclose()
