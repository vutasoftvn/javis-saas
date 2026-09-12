"""E2E Verification for CHRO People Profile and Executive Role Activation.

Plan: .superpowers/sdd/2026-09-12-chro-people-profile-and-executive-activation/task-3-brief.md
Mirrors: tests/e2e/test_cpo_product_profile.py (freshest sibling).
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
def chro_test_env(real_company_service):
    """Setup Workspace A with Project A1, and Workspace B for isolation."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Workspace A (Founder A)
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": f"chro-founder-a-{time.time()}@example.com", "displayName": "Founder A"},
    )
    assert reg_a.status_code == 200, reg_a.text
    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": ws_a}

    # Project A1
    p_a_resp = client.post(
        "/operations/projects",
        json={"title": "CHRO Alpha Project", "description": "People project for CHRO"},
        headers=headers_a,
    )
    assert p_a_resp.status_code == 200, p_a_resp.text
    proj_a_id = str(p_a_resp.json()["id"])

    # 2. Workspace B (Founder B) for cross-tenant isolation
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": f"chro-founder-b-{time.time()}@example.com", "displayName": "Founder B"},
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


def test_chro_activation_boundary_and_deliberation(chro_test_env):
    """Test negative gates (inactive people profile, cross-tenant) and positive CHRO activation."""
    base_url = chro_test_env["base_url"]
    headers_a = chro_test_env["headers_a"]
    headers_b = chro_test_env["headers_b"]
    proj_a_id = chro_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Verify CHRO is initially UNAVAILABLE when People profile is only TEMPLATE
    board_resp = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp.status_code == 200, board_resp.text
    roles = board_resp.json()["roles"]
    chro_role = next((r for r in roles if r["roleKey"] == "chro"), None)
    assert chro_role is not None
    assert chro_role["displayState"] == "UNAVAILABLE"
    assert chro_role["runtimeReadiness"] == "READY"
    assert chro_role["requiredProfileKey"] == "people"

    # 2. Attempt to activate CHRO directly before People profile is ACTIVE -> must FAIL
    early_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/chro/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert early_act.status_code in (400, 412), early_act.text

    # 3. Cross-Tenant Attempt: Workspace B cannot activate or access CHRO on Project A1
    denied_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/chro/activate",
        json={"expectedVersion": 1},
        headers=headers_b,
    )
    assert denied_act.status_code in (403, 404), denied_act.text

    # 4. Founder A activates People profile in Startup Team
    people_act = client.post(
        f"/operations/projects/{proj_a_id}/startup-team/people/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert people_act.status_code == 200, people_act.text
    people_data = people_act.json()
    assert people_data["displayState"] == "ACTIVE"

    # 5. Check Executive Board: CHRO now transitions to AVAILABLE_NOT_ACTIVATED
    board_resp2 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp2.status_code == 200, board_resp2.text
    chro_role2 = next(r for r in board_resp2.json()["roles"] if r["roleKey"] == "chro")
    assert chro_role2["displayState"] == "AVAILABLE_NOT_ACTIVATED"

    # 6. Founder A explicitly activates CHRO role
    act_chro = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/chro/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert act_chro.status_code == 200, act_chro.text
    chro_act_data = act_chro.json()
    assert chro_act_data["state"] == "ACTIVE"
    assert chro_act_data["roleKey"] == "chro"

    # 7. Board now reports CHRO as ACTIVE
    board_resp3 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp3.status_code == 200, board_resp3.text
    chro_role3 = next(r for r in board_resp3.json()["roles"] if r["roleKey"] == "chro")
    assert chro_role3["displayState"] == "ACTIVE"

    # 8. Create Draft Deliberation and Frame with CHRO selected
    draft_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/draft",
        json={"title": "Should we restructure the support team reporting line?"},
        headers=headers_a,
    )
    assert draft_resp.status_code == 200, draft_resp.text
    delib_id = draft_resp.json()["id"]

    frame_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/{delib_id}/frame",
        json={
            "question": "Do we have enough aggregate capacity/risk evidence to justify a reorg?",
            "roleKeys": ["chro"],
        },
        headers=headers_a,
    )
    assert frame_resp.status_code == 200, frame_resp.text
    framed_data = frame_resp.json()
    assert framed_data["state"] == "ANALYSIS_QUEUED"
    assert framed_data["activeFrameVersion"] >= 1


def test_people_risk_dossier_is_project_and_workspace_isolated(chro_test_env):
    """Founder A creates a people risk dossier on Project A1; Workspace B cannot read it."""
    base_url = chro_test_env["base_url"]
    headers_a = chro_test_env["headers_a"]
    headers_b = chro_test_env["headers_b"]
    proj_a_id = chro_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # Founder A creates a people risk dossier on Project A1
    create_resp = client.post(
        "/operations/people-risk-dossiers",
        json={
            "projectId": proj_a_id,
            "capacityBands": [{"roleCategory": "engineering", "headcount": 4}],
            "riskSignals": [
                {
                    "category": "single_point_of_failure",
                    "severity": "MEDIUM",
                    "sourceRef": "org-review://q3-2026",
                }
            ],
            "sourceRefs": [
                {
                    "sourceRef": "org-review://q3-2026",
                    "classification": "org_review",
                }
            ],
            "reasonCode": "INITIAL_ASSESSMENT",
        },
        headers=headers_a,
    )
    assert create_resp.status_code == 200, create_resp.text
    dossier = create_resp.json()
    assert dossier["revision"] == 1
    assert dossier["status"] == "DRAFT"

    # Founder A can read it back on Project A1
    read_a_resp = client.get(
        f"/operations/projects/{proj_a_id}/people-risk-dossier",
        headers=headers_a,
    )
    assert read_a_resp.status_code == 200, read_a_resp.text
    assert read_a_resp.json()["dossierId"] == dossier["dossierId"]

    # Workspace B (a different tenant) cannot read the dossier on Project A1
    read_b_resp = client.get(
        f"/operations/projects/{proj_a_id}/people-risk-dossier",
        headers=headers_b,
    )
    assert read_b_resp.status_code in (403, 404), read_b_resp.text


def test_people_risk_dossier_rejects_pii_shaped_field(chro_test_env):
    """People Risk Dossier's headline privacy property: PII-shaped strings are rejected with 400."""
    base_url = chro_test_env["base_url"]
    headers_a = chro_test_env["headers_a"]
    proj_a_id = chro_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # An email-shaped string tucked into an otherwise-valid sourceRef must be rejected.
    create_resp = client.post(
        "/operations/people-risk-dossiers",
        json={
            "projectId": proj_a_id,
            "sourceRefs": [
                {
                    "sourceRef": "candidate.jane.doe@example.com",
                    "classification": "org_review",
                }
            ],
            "reasonCode": "INITIAL_ASSESSMENT",
        },
        headers=headers_a,
    )
    assert create_resp.status_code == 400, create_resp.text
