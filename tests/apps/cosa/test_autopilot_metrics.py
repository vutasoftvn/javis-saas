from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from apps.cosa.api.app import create_cosa_app


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


@pytest.fixture
def metrics_client():
    app = create_cosa_app()
    app.state.plane = type(
        "DummyPlane",
        (),
        {
            "correlation_db": MockCorrelationDb(),
        },
    )()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_autopilot_metrics_calculation(metrics_client: AsyncClient):
    res = await metrics_client.get("/agent/autopilot/metrics?workspaceId=ws_metric_1")
    assert res.status_code == 200
    data = res.json()

    assert data["runsDispatched"] == 4
    assert data["runsCompleted"] == 3
    assert data["runsHandedOff"] == 1
    # Completed without human handoff = 2 out of 4 = 0.5 (50%)
    assert data["containmentRate"] == 0.5
    assert "takeoverAfterAutopilotRate" in data
    assert "unsafeProposalRate" in data
