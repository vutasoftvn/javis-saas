"""E2E Verification for GC Legal Profile and Executive Role Activation.

Plan: .superpowers/sdd/2026-09-12-gc-legal-profile-and-executive-activation/task-3-brief.md
Mirrors: tests/e2e/test_ciso_security_profile.py (freshest sibling, hardened body-content assertions).
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
def gc_test_env(real_company_service):
    """Setup Workspace A with Project A1, and Workspace B for isolation."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Workspace A (Founder A)
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": f"gc-founder-a-{time.time()}@example.com", "displayName": "Founder A"},
    )
    assert reg_a.status_code == 200, reg_a.text
    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": ws_a}

    # Project A1
    p_a_resp = client.post(
        "/operations/projects",
        json={"title": "GC Alpha Project", "description": "Legal project for GC"},
        headers=headers_a,
    )
    assert p_a_resp.status_code == 200, p_a_resp.text
    proj_a_id = str(p_a_resp.json()["id"])

    # 2. Workspace B (Founder B) for cross-tenant isolation
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": f"gc-founder-b-{time.time()}@example.com", "displayName": "Founder B"},
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
        "token_a": token_a,
        "proj_a_id": proj_a_id,
        "ws_b": ws_b,
        "headers_b": headers_b,
    }


def test_gc_activation_boundary_and_deliberation(gc_test_env):
    """Test negative gates (inactive legal profile, cross-tenant) and positive GC activation."""
    base_url = gc_test_env["base_url"]
    headers_a = gc_test_env["headers_a"]
    headers_b = gc_test_env["headers_b"]
    proj_a_id = gc_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Verify GC is initially UNAVAILABLE when Legal profile is only TEMPLATE
    board_resp = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp.status_code == 200, board_resp.text
    roles = board_resp.json()["roles"]
    gc_role = next((r for r in roles if r["roleKey"] == "gc"), None)
    assert gc_role is not None
    assert gc_role["displayState"] == "UNAVAILABLE"
    assert gc_role["runtimeReadiness"] == "READY"
    assert gc_role["requiredProfileKey"] == "legal"

    # 2. Attempt to activate GC directly before Legal profile is ACTIVE -> must FAIL
    early_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/gc/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert early_act.status_code in (400, 412), early_act.text

    # 3. Cross-Tenant Attempt: Workspace B cannot activate or access GC on Project A1
    denied_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/gc/activate",
        json={"expectedVersion": 1},
        headers=headers_b,
    )
    assert denied_act.status_code in (403, 404), denied_act.text

    # 4. Founder A activates Legal profile in Startup Team
    legal_act = client.post(
        f"/operations/projects/{proj_a_id}/startup-team/legal/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert legal_act.status_code == 200, legal_act.text
    legal_data = legal_act.json()
    assert legal_data["displayState"] == "ACTIVE"

    # 5. Check Executive Board: GC now transitions to AVAILABLE_NOT_ACTIVATED
    board_resp2 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp2.status_code == 200, board_resp2.text
    gc_role2 = next(r for r in board_resp2.json()["roles"] if r["roleKey"] == "gc")
    assert gc_role2["displayState"] == "AVAILABLE_NOT_ACTIVATED"

    # 6. Founder A explicitly activates GC role
    act_gc = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/gc/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert act_gc.status_code == 200, act_gc.text
    gc_act_data = act_gc.json()
    assert gc_act_data["state"] == "ACTIVE"
    assert gc_act_data["roleKey"] == "gc"

    # 7. Board now reports GC as ACTIVE
    board_resp3 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp3.status_code == 200, board_resp3.text
    gc_role3 = next(r for r in board_resp3.json()["roles"] if r["roleKey"] == "gc")
    assert gc_role3["displayState"] == "ACTIVE"

    # 8. Create Draft Deliberation and Frame with GC selected
    draft_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/draft",
        json={"title": "Should we sign the new vendor MSA this quarter?"},
        headers=headers_a,
    )
    assert draft_resp.status_code == 200, draft_resp.text
    delib_id = draft_resp.json()["id"]

    frame_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/{delib_id}/frame",
        json={
            "question": "Do we have enough classified legal issue evidence to justify signing now?",
            "roleKeys": ["gc"],
        },
        headers=headers_a,
    )
    assert frame_resp.status_code == 200, frame_resp.text
    framed_data = frame_resp.json()
    assert framed_data["state"] == "ANALYSIS_QUEUED"
    assert framed_data["activeFrameVersion"] >= 1


def test_legal_issue_dossier_is_project_and_workspace_isolated(gc_test_env):
    """Founder A creates a legal issue dossier on Project A1 referencing a real
    Finance-Legal obligation; Workspace B cannot read it."""
    base_url = gc_test_env["base_url"]
    headers_a = gc_test_env["headers_a"]
    headers_b = gc_test_env["headers_b"]
    proj_a_id = gc_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # Seed a real legal obligation via Finance-Legal so legalRecordRefs can
    # reference a real record (not SQL cross-schema access — mirror Task 1's
    # own vitest setup, which calls `createObligationService`).
    obligation_resp = client.post(
        "/finance-legal/obligations",
        json={"workspaceId": gc_test_env["ws_a"], "title": "Annual data protection filing"},
        headers=headers_a,
    )
    assert obligation_resp.status_code == 200, obligation_resp.text
    obligation_id = str(obligation_resp.json()["id"])

    # Founder A creates a legal issue dossier on Project A1
    create_resp = client.post(
        "/operations/legal-issue-dossiers",
        json={
            "projectId": proj_a_id,
            "issueCategory": "CONTRACT_QUESTION",
            "legalRecordRefs": [{"recordType": "OBLIGATION", "recordId": obligation_id}],
            "applicabilityStatus": "UNKNOWN",
            "jurisdiction": "US-DE",
            "redactedQuestion": "Does the vendor MSA renewal clause require 30 or 60 days notice?",
            "reasonCode": "ISSUE_RAISED",
        },
        headers=headers_a,
    )
    assert create_resp.status_code == 200, create_resp.text
    dossier = create_resp.json()
    assert dossier["revision"] == 1
    assert dossier["status"] == "DRAFT"
    assert dossier["applicabilityStatus"] == "UNKNOWN"

    # Founder A can read it back on Project A1
    read_a_resp = client.get(
        f"/operations/projects/{proj_a_id}/legal-issue-dossier",
        headers=headers_a,
    )
    assert read_a_resp.status_code == 200, read_a_resp.text
    assert read_a_resp.json()["dossierId"] == dossier["dossierId"]

    # Workspace B (a different tenant) cannot read the dossier on Project A1
    read_b_resp = client.get(
        f"/operations/projects/{proj_a_id}/legal-issue-dossier",
        headers=headers_b,
    )
    assert read_b_resp.status_code in (403, 404), read_b_resp.text
    # Không chỉ kiểm tra status code chung chung — xác nhận đúng loại từ chối
    # là "project không thuộc workspace" (permission_denied), không phải một
    # lỗi 4xx bất kỳ khác vô tình khớp status code.
    read_b_body = read_b_resp.json()
    assert read_b_body.get("code") == "permission_denied", read_b_resp.text
    assert "PROJECT_ACCESS_DENIED" in read_b_body.get("message", ""), read_b_resp.text


def test_legal_issue_dossier_rejects_contract_body_shaped_field(gc_test_env):
    """Legal Issue Dossier's headline property: full contract bodies/PII/privileged
    advice are never allowed — a contract-body-shaped field is rejected with 400."""
    base_url = gc_test_env["base_url"]
    headers_a = gc_test_env["headers_a"]
    proj_a_id = gc_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # A WHEREAS/NOW-THEREFORE contract-boilerplate string tucked into
    # redactedQuestion must be rejected.
    create_resp = client.post(
        "/operations/legal-issue-dossiers",
        json={
            "projectId": proj_a_id,
            "issueCategory": "CONTRACT_QUESTION",
            "redactedQuestion": (
                "WHEREAS the parties wish to enter into this Agreement, NOW THEREFORE in "
                "consideration of the mutual covenants contained herein, the parties agree "
                "as follows..."
            ),
            "reasonCode": "ISSUE_RAISED",
        },
        headers=headers_a,
    )
    assert create_resp.status_code == 400, create_resp.text
    # Không chỉ kiểm tra status 400 chung chung — xác nhận body thật sự mang
    # marker contract-body-rejection cụ thể, phân biệt với một invalid_argument
    # khác (vd. thiếu field) vô tình cũng trả 400.
    create_body = create_resp.json()
    assert create_body.get("code") == "invalid_argument", create_resp.text
    assert "LEGAL_DOSSIER_CONTRACT_BODY_REJECTED" in create_body.get("message", ""), create_resp.text

    # A PII-shaped email address must also be rejected.
    create_resp_pii = client.post(
        "/operations/legal-issue-dossiers",
        json={
            "projectId": proj_a_id,
            "issueCategory": "CONTRACT_QUESTION",
            "redactedQuestion": "Please contact jane.doe@example.com about the renewal terms",
            "reasonCode": "ISSUE_RAISED",
        },
        headers=headers_a,
    )
    assert create_resp_pii.status_code == 400, create_resp_pii.text
    create_body_pii = create_resp_pii.json()
    assert create_body_pii.get("code") == "invalid_argument", create_resp_pii.text
    assert "LEGAL_DOSSIER_PII_REJECTED" in create_body_pii.get("message", ""), create_resp_pii.text
