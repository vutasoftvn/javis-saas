from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from apps.cosa.api.app import create_cosa_app
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity


class MockCorrelationDb:
    def __init__(self):
        self.inbox_records = {}
        self.tasks = {}
        self.runs = {
            "run_ap_1": {"run_id": "run_ap_1", "workspace_id": "ws_metric_1", "status": "completed", "handed_off": False},
            "run_ap_2": {"run_id": "run_ap_2", "workspace_id": "ws_metric_1", "status": "completed", "handed_off": True},
            "run_ap_3": {"run_id": "run_ap_3", "workspace_id": "ws_metric_1", "status": "failed", "handed_off": False},
            "run_ap_4": {"run_id": "run_ap_4", "workspace_id": "ws_metric_1", "status": "completed", "handed_off": False},
        }
        self.artifacts = {}


def _metrics_client(*, workspace_id: str | None = None) -> AsyncClient:
    app = create_cosa_app()
    app.state.plane = type(
        "DummyPlane",
        (),
        {
            "correlation_db": MockCorrelationDb(),
        },
    )()
    if workspace_id is not None:
        override_authenticated_identity(app, workspace_id=workspace_id, role_id="member")
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def metrics_client():
    return _metrics_client(workspace_id="ws_metric_1")


@pytest.fixture
def unsecured_client():
    return _metrics_client()


@pytest.fixture
def member_a_client():
    return _metrics_client(workspace_id="ws_metric_1")


@pytest.mark.asyncio
async def test_metrics_require_identity(unsecured_client: AsyncClient):
    assert (await unsecured_client.get("/agent/autopilot/metrics")).status_code == 401


@pytest.mark.asyncio
async def test_metrics_ignore_cross_workspace_query(member_a_client: AsyncClient):
    response = await member_a_client.get("/agent/autopilot/metrics?workspaceId=ws_metric_b")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unknown_aggregates_are_null(metrics_client: AsyncClient):
    data = (await metrics_client.get("/agent/autopilot/metrics")).json()
    assert data["approvalLatencyP95Sec"] is None


@pytest.mark.asyncio
async def test_autopilot_metrics_calculation(metrics_client: AsyncClient):
    res = await metrics_client.get("/agent/autopilot/metrics")
    assert res.status_code == 200
    data = res.json()

    assert data["runsDispatched"] == 4
    assert data["runsCompleted"] == 3
    assert data["runsHandedOff"] == 1
    # Completed without human handoff = 2 out of 4 = 0.5 (50%)
    assert data["containmentRate"] == 0.5
    assert "takeoverAfterAutopilotRate" in data
    assert "unsafeProposalRate" in data
