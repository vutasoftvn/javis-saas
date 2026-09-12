"""E2E Verification for CPO Product Profile and Executive Role Activation.

Plan: .superpowers/sdd/2026-09-12-cpo-product-profile-and-executive-activation/task-3-brief.md
Mirrors: tests/e2e/test_cro_sales_profile.py, tests/e2e/test_vpe_coding_profile.py
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
def cpo_test_env(real_company_service):
    """Setup Workspace A with Project A1, and Workspace B for isolation."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Workspace A (Founder A)
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": f"cpo-founder-a-{time.time()}@example.com", "displayName": "Founder A"},
    )
    assert reg_a.status_code == 200, reg_a.text
    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": ws_a}

    # Project A1
    p_a_resp = client.post(
        "/operations/projects",
        json={"title": "CPO Alpha Project", "description": "Product project for CPO"},
        headers=headers_a,
    )
    assert p_a_resp.status_code == 200, p_a_resp.text
    proj_a_id = str(p_a_resp.json()["id"])

    # 2. Workspace B (Founder B) for cross-tenant isolation
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": f"cpo-founder-b-{time.time()}@example.com", "displayName": "Founder B"},
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


def test_cpo_activation_boundary_and_deliberation(cpo_test_env):
    """Test negative gates (inactive product profile, cross-tenant) and positive CPO activation."""
    base_url = cpo_test_env["base_url"]
    headers_a = cpo_test_env["headers_a"]
    headers_b = cpo_test_env["headers_b"]
    proj_a_id = cpo_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Verify CPO is initially UNAVAILABLE when Product profile is only TEMPLATE
    board_resp = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp.status_code == 200, board_resp.text
    roles = board_resp.json()["roles"]
    cpo_role = next((r for r in roles if r["roleKey"] == "cpo"), None)
    assert cpo_role is not None
    assert cpo_role["displayState"] == "UNAVAILABLE"
    assert cpo_role["runtimeReadiness"] == "READY"
    assert cpo_role["requiredProfileKey"] == "product"

    # 2. Attempt to activate CPO directly before Product profile is ACTIVE -> must FAIL
    early_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/cpo/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert early_act.status_code in (400, 412), early_act.text

    # 3. Cross-Tenant Attempt: Workspace B cannot activate or access CPO on Project A1
    denied_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/cpo/activate",
        json={"expectedVersion": 1},
        headers=headers_b,
    )
    assert denied_act.status_code in (403, 404), denied_act.text

    # 4. Founder A activates Product profile in Startup Team
    product_act = client.post(
        f"/operations/projects/{proj_a_id}/startup-team/product/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert product_act.status_code == 200, product_act.text
    product_data = product_act.json()
    assert product_data["displayState"] == "ACTIVE"

    # 5. Check Executive Board: CPO now transitions to AVAILABLE_NOT_ACTIVATED
    board_resp2 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp2.status_code == 200, board_resp2.text
    cpo_role2 = next(r for r in board_resp2.json()["roles"] if r["roleKey"] == "cpo")
    assert cpo_role2["displayState"] == "AVAILABLE_NOT_ACTIVATED"

    # 6. Founder A explicitly activates CPO role
    act_cpo = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/cpo/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert act_cpo.status_code == 200, act_cpo.text
    cpo_act_data = act_cpo.json()
    assert cpo_act_data["state"] == "ACTIVE"
    assert cpo_act_data["roleKey"] == "cpo"

    # 7. Board now reports CPO as ACTIVE
    board_resp3 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp3.status_code == 200, board_resp3.text
    cpo_role3 = next(r for r in board_resp3.json()["roles"] if r["roleKey"] == "cpo")
    assert cpo_role3["displayState"] == "ACTIVE"

    # 8. Create Draft Deliberation and Frame with CPO selected
    draft_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/draft",
        json={"title": "Should we build the self-serve onboarding bet?"},
        headers=headers_a,
    )
    assert draft_resp.status_code == 200, draft_resp.text
    delib_id = draft_resp.json()["id"]

    frame_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/{delib_id}/frame",
        json={
            "question": "Do we have enough validated customer evidence to commit to this product bet?",
            "roleKeys": ["cpo"],
        },
        headers=headers_a,
    )
    assert frame_resp.status_code == 200, frame_resp.text
    framed_data = frame_resp.json()
    assert framed_data["state"] == "ANALYSIS_QUEUED"
    assert framed_data["activeFrameVersion"] >= 1


def test_product_decision_dossier_is_project_and_workspace_isolated(cpo_test_env):
    """Founder A creates a product decision dossier on Project A1; Workspace B cannot read it."""
    base_url = cpo_test_env["base_url"]
    headers_a = cpo_test_env["headers_a"]
    headers_b = cpo_test_env["headers_b"]
    proj_a_id = cpo_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # Founder A creates a product decision dossier on Project A1
    create_resp = client.post(
        "/operations/product-decision-dossiers",
        json={
            "projectId": proj_a_id,
            "title": "Pivot onboarding flow",
            "assumptions": ["users churn due to onboarding friction"],
            "evidenceRefs": [
                {
                    "sourceRef": "interview://cust-42",
                    "classification": "customer_interview",
                    "redactedExcerpt": "onboarding was confusing",
                }
            ],
            "reasonCode": "INITIAL_DRAFT",
        },
        headers=headers_a,
    )
    assert create_resp.status_code == 200, create_resp.text
    dossier = create_resp.json()
    assert dossier["revision"] == 1
    assert dossier["status"] == "DRAFT"

    # Founder A can read it back on Project A1
    read_a_resp = client.get(
        f"/operations/projects/{proj_a_id}/product-decision-dossier",
        headers=headers_a,
    )
    assert read_a_resp.status_code == 200, read_a_resp.text
    assert read_a_resp.json()["dossierId"] == dossier["dossierId"]

    # Workspace B (a different tenant) cannot read the dossier on Project A1
    read_b_resp = client.get(
        f"/operations/projects/{proj_a_id}/product-decision-dossier",
        headers=headers_b,
    )
    assert read_b_resp.status_code in (403, 404), read_b_resp.text
