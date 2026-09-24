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


@pytest.mark.cross_plane
def test_cpo_activation_boundary_and_deliberation(advisor_stack, advisor_cluster):
    """Đường đầy đủ của role CPO trên stack thật: profile nền -> office Workspace ->
    Project deployment -> stage gate -> frame với pin overlay; cross-tenant bị từ chối."""
    from tests.e2e.advisor_board import run_role_lifecycle

    run_role_lifecycle(advisor_stack, advisor_cluster, "cpo", "Should we prioritise onboarding over the reporting feature?")



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
