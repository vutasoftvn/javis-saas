"""E2E Verification for CRO Sales Profile and Executive Role Activation.

Plan: docs/superpowers/plans/2026-09-12-cro-sales-profile-and-executive-activation.md
Roadmap: docs/superpowers/plans/2026-09-12-executive-board-remaining-roles-roadmap.md
"""

from __future__ import annotations

import os
import time
import httpx
import pytest

_SERVICE_TOKEN = os.environ.get(
    "COSA_WORKER_SERVICE_TOKEN",
    "dev-worker-service-token",
)


@pytest.fixture
def cro_test_env(real_company_service):
    """Setup Workspace A with Project A1, and Workspace B for isolation."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Workspace A (Founder A)
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": f"cro-founder-a-{time.time()}@example.com", "displayName": "Founder A"},
    )
    assert reg_a.status_code == 200, reg_a.text
    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": ws_a}

    # Project A1
    p_a_resp = client.post(
        "/operations/projects",
        json={"title": "CRO Alpha Project", "description": "Strategy project for CRO"},
        headers=headers_a,
    )
    assert p_a_resp.status_code == 200, p_a_resp.text
    proj_a_id = str(p_a_resp.json()["id"])

    # 2. Workspace B (Founder B) for cross-tenant isolation
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": f"cro-founder-b-{time.time()}@example.com", "displayName": "Founder B"},
    )
    assert reg_b.status_code == 200, reg_b.text
    data_b = reg_b.json()
    token_b = data_b["accessToken"]
    ws_b = str(data_b["workspaceId"])
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-Id": ws_b}

    return {
        "base_url": base_url,
        "ws_a": ws_a,
        "headers_a": headers_a,
        "proj_a_id": proj_a_id,
        "ws_b": ws_b,
        "headers_b": headers_b,
    }


def test_cro_activation_boundary_and_deliberation(cro_test_env):
    """Test negative gates (inactive sales profile, cross-tenant) and positive CRO activation."""
    base_url = cro_test_env["base_url"]
    headers_a = cro_test_env["headers_a"]
    headers_b = cro_test_env["headers_b"]
    proj_a_id = cro_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Verify CRO is initially UNAVAILABLE when Sales profile is only TEMPLATE
    board_resp = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp.status_code == 200, board_resp.text
    roles = board_resp.json()["roles"]
    cro_role = next((r for r in roles if r["roleKey"] == "cro"), None)
    assert cro_role is not None
    assert cro_role["displayState"] == "UNAVAILABLE"
    assert cro_role["runtimeReadiness"] == "READY"
    assert cro_role["requiredProfileKey"] == "sales"

    # 2. Attempt to activate CRO directly before Sales profile is ACTIVE -> must FAIL
    early_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/cro/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert early_act.status_code in (400, 412), early_act.text

    # 3. Cross-Tenant Attempt: Workspace B cannot activate or access CRO on Project A1
    denied_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/cro/activate",
        json={"expectedVersion": 1},
        headers=headers_b,
    )
    assert denied_act.status_code in (403, 404), denied_act.text

    # 4. Founder A activates Sales profile in Startup Team
    sales_act = client.post(
        f"/operations/projects/{proj_a_id}/startup-team/sales/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert sales_act.status_code == 200, sales_act.text
    sales_data = sales_act.json()
    assert sales_data["displayState"] == "ACTIVE"

    # 5. Check Executive Board: CRO now transitions to AVAILABLE_NOT_ACTIVATED
    board_resp2 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp2.status_code == 200, board_resp2.text
    cro_role2 = next(r for r in board_resp2.json()["roles"] if r["roleKey"] == "cro")
    assert cro_role2["displayState"] == "AVAILABLE_NOT_ACTIVATED"

    # 6. Founder A explicitly activates CRO role
    act_cro = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/cro/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert act_cro.status_code == 200, act_cro.text
    cro_act_data = act_cro.json()
    assert cro_act_data["state"] == "ACTIVE"
    assert cro_act_data["roleKey"] == "cro"

    # 7. Board now reports CRO as ACTIVE
    board_resp3 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp3.status_code == 200, board_resp3.text
    cro_role3 = next(r for r in board_resp3.json()["roles"] if r["roleKey"] == "cro")
    assert cro_role3["displayState"] == "ACTIVE"

    # 8. Create Draft Deliberation and Frame with CRO selected
    draft_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/draft",
        json={"title": "Q3 Revenue Expansion & Pricing Review"},
        headers=headers_a,
    )
    assert draft_resp.status_code == 200, draft_resp.text
    delib_id = draft_resp.json()["id"]

    frame_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/{delib_id}/frame",
        json={
            "question": "Should we revise our pipeline qualification criteria and enterprise discount guardrails?",
            "roleKeys": ["cro"],
        },
        headers=headers_a,
    )
    assert frame_resp.status_code == 200, frame_resp.text
    framed_data = frame_resp.json()
    assert framed_data["state"] == "ANALYSIS_QUEUED"
    assert framed_data["activeFrameVersion"] >= 1
