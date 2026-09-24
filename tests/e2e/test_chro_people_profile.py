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


@pytest.mark.cross_plane
def test_chro_activation_boundary_and_deliberation(advisor_stack, advisor_cluster):
    """Đường đầy đủ của role CHRO trên stack thật: profile nền -> office Workspace ->
    Project deployment -> stage gate -> frame với pin overlay; cross-tenant bị từ chối."""
    from tests.e2e.advisor_board import run_role_lifecycle

    run_role_lifecycle(advisor_stack, advisor_cluster, "chro", "Is the hiring plan supportable given verified people evidence?")



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
    # Không chỉ kiểm tra status code chung chung — xác nhận đúng loại từ chối
    # là "project không thuộc workspace" (permission_denied), không phải một
    # lỗi 4xx bất kỳ khác vô tình khớp status code.
    read_b_body = read_b_resp.json()
    assert read_b_body.get("code") == "permission_denied", read_b_resp.text
    assert "PROJECT_ACCESS_DENIED" in read_b_body.get("message", ""), read_b_resp.text


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
    # Không chỉ kiểm tra status 400 chung chung — xác nhận body thật sự mang
    # marker PII-rejection cụ thể, phân biệt với một invalid_argument khác
    # (vd. thiếu field) vô tình cũng trả 400.
    create_body = create_resp.json()
    assert create_body.get("code") == "invalid_argument", create_resp.text
    assert "PEOPLE_DOSSIER_PII_REJECTED" in create_body.get("message", ""), create_resp.text
