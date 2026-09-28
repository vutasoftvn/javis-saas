"""Internal tests for /internal/ai-initiatives/snapshots endpoint (Task 6).

Verifies service token authentication, foreign project and hash drift denial (403),
and idempotent consumption of valid snapshots.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from types import SimpleNamespace

from apps.cosa.api.ai_initiative_internal_routes import compute_decision_hash
from apps.cosa.api.app import create_cosa_app
from apps.cosa.models.ai_initiative_snapshot import InMemoryAiInitiativePromotionSnapshotStore

SERVICE_HEADERS = {"X-Cosa-Service-Token": "local-dev-service-token"}


@pytest.fixture
def client():
    # This route only reads `plane.ai_initiative_snapshot_store` — inject a
    # minimal fake plane instead of building a full CosaAgentPlane (which
    # needs AGENT_DATABASE_URL/model credentials and would make this a slow
    # integration test rather than a route-level unit test). Without an
    # injected plane, `create_cosa_app()` never populates `app.state.plane`
    # here: real plane construction happens in ASGI `lifespan`, which the
    # bare `TestClient(app)` used below does not trigger.
    fake_plane = SimpleNamespace(
        ai_initiative_snapshot_store=InMemoryAiInitiativePromotionSnapshotStore()
    )
    app = create_cosa_app(plane=fake_plane)
    return TestClient(app)


def test_internal_promotion_snapshot_requires_service_token(client):
    valid_payload = {
        "initiative_id": "init-1",
        "initiative_revision": 2,
        "workspace_id": "ws-1",
        "project_id": "proj-1",
        "lifecycle_state": "PILOT",
        "risk_tier": "LOW",
        "autonomy_tier": "A0",
        "decision_id": "dec-100",
        "decision_hash": "a1b2c3d4e5f67890",
    }
    resp = client.post("/internal/ai-initiatives/snapshots", json=valid_payload)
    assert resp.status_code == 401


def test_internal_promotion_snapshot_rejects_foreign_project_or_hash_drift(client):
    # decision_hash is computed for project "proj-1" — resubmitting the same
    # decision_id/revision/lifecycle_state under a different project_id must
    # fail the hash comparison, since project_id is part of the signed input
    # (see compute_decision_hash docstring). This is the real defense against
    # a decision being "replayed" under a foreign project, not a substring
    # check on the literal text "foreign".
    foreign_snapshot = {
        "initiative_id": "init-1",
        "initiative_revision": 2,
        "workspace_id": "ws-1",
        "project_id": "foreign_project_99",
        "lifecycle_state": "PILOT",
        "risk_tier": "LOW",
        "autonomy_tier": "A0",
        "decision_id": "dec-100",
        "decision_hash": compute_decision_hash("dec-100", 2, "PILOT", "ws-1", "proj-1"),
    }
    resp = client.post(
        "/internal/ai-initiatives/snapshots",
        headers=SERVICE_HEADERS,
        json=foreign_snapshot,
    )
    assert resp.status_code == 403

    drift_snapshot = {
        "initiative_id": "init-1",
        "initiative_revision": 2,
        "workspace_id": "ws-1",
        "project_id": "proj-1",
        "lifecycle_state": "PILOT",
        "risk_tier": "LOW",
        "autonomy_tier": "A0",
        "decision_id": "dec-101",
        "decision_hash": "drifted_hash_value",
    }
    resp_drift = client.post(
        "/internal/ai-initiatives/snapshots",
        headers=SERVICE_HEADERS,
        json=drift_snapshot,
    )
    assert resp_drift.status_code == 403


def test_internal_promotion_snapshot_accepts_valid_and_is_idempotent(client):
    payload = {
        "initiative_id": "init-2",
        "initiative_revision": 3,
        "workspace_id": "ws-1",
        "project_id": "proj-1",
        "lifecycle_state": "VALIDATE",
        "risk_tier": "MEDIUM",
        "autonomy_tier": "A1",
        "decision_id": "dec-200",
        "decision_hash": compute_decision_hash("dec-200", 3, "VALIDATE", "ws-1", "proj-1"),
        "value_contract_revision": 1,
        "data_readiness_revision": 1,
    }

    # First call: accepted
    r1 = client.post(
        "/internal/ai-initiatives/snapshots",
        headers=SERVICE_HEADERS,
        json=payload,
    )
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["status"] == "accepted"
    assert data1["accepted"] is True
    assert data1["decision_id"] == "dec-200"

    # Second call with identical payload: already_consumed (idempotent)
    r2 = client.post(
        "/internal/ai-initiatives/snapshots",
        headers=SERVICE_HEADERS,
        json=payload,
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["status"] == "already_consumed"
    assert data2["accepted"] is True
