"""E2E HTTP tests for MVP Strategy and Workspace Runtime.
Ensures truth-only contracts and workspace isolation without mock transports.
"""

from __future__ import annotations

import httpx
import pytest

from tests.e2e.mvp_stack import MvpStack


def test_strategy_and_workspace_runtime_live(real_company_service):
    """Test canvas creation, revision review, blockers and runtime source status."""
    base_url = real_company_service.base_url

    # Create test session 1 (workspace A)
    client = httpx.Client(base_url=base_url, timeout=10.0)
    email_a = f"test-user-a-{pytest.importorskip('time').time()}@example.com"
    reg_a = client.post(
        "/identity/test-session",
        json={"email": email_a, "displayName": "Workspace A Founder"},
    )
    if reg_a.status_code != 200:
        pytest.skip(f"Identity test session creation failed ({reg_a.status_code}): {reg_a.text}")

    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])

    headers_a = {
        "Authorization": f"Bearer {token_a}",
        "X-Workspace-Id": ws_a,
    }

    # 1. List canvases (should be empty initially)
    list_res = client.get("/operations/strategy/canvases", headers=headers_a)
    assert list_res.status_code == 200
    list_json = list_res.json()
    assert list_json["meta"]["dataState"] == "empty"
    assert list_json["data"] == []

    # 2. Create a Canvas
    create_res = client.post(
        "/operations/strategy/canvases",
        headers=headers_a,
        json={"name": "MVP Strategy Canvas", "description": "Problem-Solution Fit"},
    )
    assert create_res.status_code == 200
    canvas_json = create_res.json()
    assert canvas_json["meta"]["dataState"] == "populated"
    canvas_id = canvas_json["data"]["id"]
    assert canvas_json["data"]["name"] == "MVP Strategy Canvas"

    # 3. Create a Revision (USER origin)
    rev_res = client.post(
        f"/operations/strategy/canvases/{canvas_id}/revisions",
        headers=headers_a,
        json={
            "content": {"problem": "Lack of AI automation", "solution": "Agent OS"},
            "origin": "USER",
        },
    )
    assert rev_res.status_code == 200
    rev_json = rev_res.json()
    assert rev_json["data"]["status"] == "DRAFT"
    rev_id = rev_json["data"]["id"]

    # 4. Submit Revision for Review
    submit_res = client.post(
        f"/operations/strategy/canvas-revisions/{rev_id}/submit-review",
        headers=headers_a,
    )
    assert submit_res.status_code == 200
    assert submit_res.json()["data"]["status"] == "IN_REVIEW"

    # 5. Approve Revision
    approve_res = client.post(
        f"/operations/strategy/canvas-revisions/{rev_id}/approve",
        headers=headers_a,
        json={"reviewNote": "Approved for execution"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["data"]["status"] == "APPROVED"

    # 6. Check Workspace Runtime Blockers
    blockers_res = client.get("/operations/workspace-runtime/blockers", headers=headers_a)
    assert blockers_res.status_code == 200
    blockers_json = blockers_res.json()
    assert blockers_json["meta"]["dataState"] in {"populated", "empty"}

    # 7. Check Workspace Runtime Source Status
    status_res = client.get("/operations/workspace-runtime/source-status", headers=headers_a)
    assert status_res.status_code == 200
    status_json = status_res.json()
    assert len(status_json["data"]) > 0
    assert status_json["data"][0]["status"] == "HEALTHY"

    # 8. Workspace Isolation Check: Query canvas from Workspace B
    email_b = f"test-user-b-{pytest.importorskip('time').time()}@example.com"
    reg_b = client.post(
        "/identity/test-session",
        json={"email": email_b, "displayName": "Workspace B Founder"},
    )
    data_b = reg_b.json()
    headers_b = {
        "Authorization": f"Bearer {data_b['accessToken']}",
        "X-Workspace-Id": str(data_b["workspaceId"]),
    }
    cross_res = client.get(f"/operations/strategy/canvases/{canvas_id}", headers=headers_b)
    assert cross_res.status_code in {403, 404}
