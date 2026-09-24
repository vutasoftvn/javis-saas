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


@pytest.mark.cross_plane
def test_gc_activation_boundary_and_deliberation(advisor_stack, advisor_cluster):
    """Đường đầy đủ của role GC trên stack thật: profile nền -> office Workspace ->
    Project deployment -> stage gate -> frame với pin overlay; cross-tenant bị từ chối."""
    from tests.e2e.advisor_board import run_role_lifecycle

    run_role_lifecycle(advisor_stack, advisor_cluster, "gc", "Do we have enough legal evidence to sign this partnership?")



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
