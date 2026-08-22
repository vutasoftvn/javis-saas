import pytest
from fastapi.testclient import TestClient
from main import app


def test_agent_gateway_meta_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/agents/_meta")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert "sub_surfaces" in data
    names = [s["name"] for s in data["sub_surfaces"]]
    assert "agents_runtime" in names
    assert "agents_execution" in names
    assert "agents_approvals" in names
    assert "agent_proposals" in names
    assert "orchestrator" in names
    assert "mission_control" in names


def test_agent_gateway_sub_surface_routes_exist():
    client = TestClient(app)
    # Check that mounted paths exist (even if 401 unauthenticated, they exist as route)
    res_approvals = client.get("/api/v1/agents/approvals")
    assert res_approvals.status_code in (200, 401)

    res_proposals = client.get("/api/v1/agents/proposals")
    assert res_proposals.status_code in (200, 401)

    res_mc = client.get("/api/v1/agents/mission-control/stream/12345")
    assert res_mc.status_code in (200, 401)

    # The removed agentic control plane had no production callers.  Its old
    # `/api/v1/agent/goals` route must stay absent rather than accidentally
    # reintroducing a second command authority.
    res_control = client.get("/api/v1/agent/goals")
    assert res_control.status_code == 404
