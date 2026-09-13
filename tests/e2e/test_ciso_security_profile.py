"""E2E Verification for CISO Security Profile and Executive Role Activation.

Plan: .superpowers/sdd/2026-09-12-ciso-security-profile-and-executive-activation/task-3-brief.md
Mirrors: tests/e2e/test_chro_people_profile.py (freshest sibling, hardened body-content assertions).
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
def ciso_test_env(real_company_service):
    """Setup Workspace A with Project A1, and Workspace B for isolation."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Workspace A (Founder A)
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": f"ciso-founder-a-{time.time()}@example.com", "displayName": "Founder A"},
    )
    assert reg_a.status_code == 200, reg_a.text
    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": ws_a}

    # Project A1
    p_a_resp = client.post(
        "/operations/projects",
        json={"title": "CISO Alpha Project", "description": "Security project for CISO"},
        headers=headers_a,
    )
    assert p_a_resp.status_code == 200, p_a_resp.text
    proj_a_id = str(p_a_resp.json()["id"])

    # 2. Workspace B (Founder B) for cross-tenant isolation
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": f"ciso-founder-b-{time.time()}@example.com", "displayName": "Founder B"},
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


def test_ciso_activation_boundary_and_deliberation(ciso_test_env):
    """Test negative gates (inactive security profile, cross-tenant) and positive CISO activation."""
    base_url = ciso_test_env["base_url"]
    headers_a = ciso_test_env["headers_a"]
    headers_b = ciso_test_env["headers_b"]
    proj_a_id = ciso_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Verify CISO is initially UNAVAILABLE when Security profile is only TEMPLATE
    board_resp = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp.status_code == 200, board_resp.text
    roles = board_resp.json()["roles"]
    ciso_role = next((r for r in roles if r["roleKey"] == "ciso"), None)
    assert ciso_role is not None
    assert ciso_role["displayState"] == "UNAVAILABLE"
    assert ciso_role["runtimeReadiness"] == "READY"
    assert ciso_role["requiredProfileKey"] == "security"

    # 2. Attempt to activate CISO directly before Security profile is ACTIVE -> must FAIL
    early_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/ciso/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert early_act.status_code in (400, 412), early_act.text

    # 3. Cross-Tenant Attempt: Workspace B cannot activate or access CISO on Project A1
    denied_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/ciso/activate",
        json={"expectedVersion": 1},
        headers=headers_b,
    )
    assert denied_act.status_code in (403, 404), denied_act.text

    # 4. Founder A activates Security profile in Startup Team
    security_act = client.post(
        f"/operations/projects/{proj_a_id}/startup-team/security/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert security_act.status_code == 200, security_act.text
    security_data = security_act.json()
    assert security_data["displayState"] == "ACTIVE"

    # 5. Check Executive Board: CISO now transitions to AVAILABLE_NOT_ACTIVATED
    board_resp2 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp2.status_code == 200, board_resp2.text
    ciso_role2 = next(r for r in board_resp2.json()["roles"] if r["roleKey"] == "ciso")
    assert ciso_role2["displayState"] == "AVAILABLE_NOT_ACTIVATED"

    # 6. Founder A explicitly activates CISO role
    act_ciso = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/ciso/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert act_ciso.status_code == 200, act_ciso.text
    ciso_act_data = act_ciso.json()
    assert ciso_act_data["state"] == "ACTIVE"
    assert ciso_act_data["roleKey"] == "ciso"

    # 7. Board now reports CISO as ACTIVE
    board_resp3 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp3.status_code == 200, board_resp3.text
    ciso_role3 = next(r for r in board_resp3.json()["roles"] if r["roleKey"] == "ciso")
    assert ciso_role3["displayState"] == "ACTIVE"

    # 8. Create Draft Deliberation and Frame with CISO selected
    draft_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/draft",
        json={"title": "Should we prioritize a SOC 2 readiness push this quarter?"},
        headers=headers_a,
    )
    assert draft_resp.status_code == 200, draft_resp.text
    delib_id = draft_resp.json()["id"]

    frame_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/{delib_id}/frame",
        json={
            "question": "Do we have enough classified control/finding evidence to justify the push?",
            "roleKeys": ["ciso"],
        },
        headers=headers_a,
    )
    assert frame_resp.status_code == 200, frame_resp.text
    framed_data = frame_resp.json()
    assert framed_data["state"] == "ANALYSIS_QUEUED"
    assert framed_data["activeFrameVersion"] >= 1


def test_security_posture_dossier_is_project_and_workspace_isolated(ciso_test_env):
    """Founder A creates a security posture dossier on Project A1; Workspace B cannot read it."""
    base_url = ciso_test_env["base_url"]
    headers_a = ciso_test_env["headers_a"]
    headers_b = ciso_test_env["headers_b"]
    proj_a_id = ciso_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # Founder A creates a security posture dossier on Project A1
    create_resp = client.post(
        "/operations/security-posture-dossiers",
        json={
            "projectId": proj_a_id,
            "controls": [
                {
                    "controlId": "control-mfa-enforced",
                    "category": "access_control",
                    "state": "IMPLEMENTED",
                }
            ],
            "findings": [
                {
                    "category": "missing_control",
                    "severity": "MEDIUM",
                    "sourceRef": "security-review://q3-2026",
                }
            ],
            "evidenceRefs": [
                {
                    "sourceRef": "security-review://q3-2026",
                    "classification": "security_review",
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
        f"/operations/projects/{proj_a_id}/security-posture-dossier",
        headers=headers_a,
    )
    assert read_a_resp.status_code == 200, read_a_resp.text
    assert read_a_resp.json()["dossierId"] == dossier["dossierId"]

    # Workspace B (a different tenant) cannot read the dossier on Project A1
    read_b_resp = client.get(
        f"/operations/projects/{proj_a_id}/security-posture-dossier",
        headers=headers_b,
    )
    assert read_b_resp.status_code in (403, 404), read_b_resp.text
    # Không chỉ kiểm tra status code chung chung — xác nhận đúng loại từ chối
    # là "project không thuộc workspace" (permission_denied), không phải một
    # lỗi 4xx bất kỳ khác vô tình khớp status code.
    read_b_body = read_b_resp.json()
    assert read_b_body.get("code") == "permission_denied", read_b_resp.text
    assert "PROJECT_ACCESS_DENIED" in read_b_body.get("message", ""), read_b_resp.text


def test_security_posture_dossier_rejects_secret_shaped_field(ciso_test_env):
    """Security Posture Dossier's headline secret-free property: secret-shaped strings are rejected with 400."""
    base_url = ciso_test_env["base_url"]
    headers_a = ciso_test_env["headers_a"]
    proj_a_id = ciso_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # An sk-prefixed API-key-shaped string tucked into an otherwise-valid
    # sourceRef must be rejected.
    create_resp = client.post(
        "/operations/security-posture-dossiers",
        json={
            "projectId": proj_a_id,
            "findings": [
                {
                    "category": "exposed_secret",
                    "severity": "HIGH",
                    "sourceRef": "sk-liveApiKeyLeakedInLogsExample1234567890",
                }
            ],
            "reasonCode": "INITIAL_ASSESSMENT",
        },
        headers=headers_a,
    )
    assert create_resp.status_code == 400, create_resp.text
    # Không chỉ kiểm tra status 400 chung chung — xác nhận body thật sự mang
    # marker secret-rejection cụ thể, phân biệt với một invalid_argument khác
    # (vd. thiếu field) vô tình cũng trả 400.
    create_body = create_resp.json()
    assert create_body.get("code") == "invalid_argument", create_resp.text
    assert "SECURITY_DOSSIER_SECRET_REJECTED" in create_body.get("message", ""), create_resp.text

    # A PEM private key header must also be rejected.
    create_resp_pem = client.post(
        "/operations/security-posture-dossiers",
        json={
            "projectId": proj_a_id,
            "evidenceRefs": [
                {
                    "sourceRef": "security-review://q3-2026",
                    "classification": "security_review",
                    "redactedExcerpt": "-----BEGIN RSA PRIVATE KEY-----",
                }
            ],
            "reasonCode": "INITIAL_ASSESSMENT",
        },
        headers=headers_a,
    )
    assert create_resp_pem.status_code == 400, create_resp_pem.text
    create_body_pem = create_resp_pem.json()
    assert create_body_pem.get("code") == "invalid_argument", create_resp_pem.text
    assert "SECURITY_DOSSIER_SECRET_REJECTED" in create_body_pem.get("message", ""), create_resp_pem.text
