"""E2E Recovery, Revocation, and Tenant Isolation Verification for Executive Advisory Board.

Task 8 of plan: docs/superpowers/plans/2026-09-11-executive-advisory-board.md
Spec: docs/superpowers/specs/2026-09-11-executive-advisory-board-design.md
"""

from __future__ import annotations

import os
import time
import httpx
import pytest

from tests.e2e.advisor_board import Board, worker_headers

_SERVICE_TOKEN = os.environ.get(
    "COSA_WORKER_SERVICE_TOKEN",
    "dev-worker-service-token",
)


@pytest.fixture
def e2e_recovery_env(real_company_service):
    """Create two separate workspaces for recovery and isolation testing."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Workspace A (Founder A)
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": f"exec-recovery-a-{time.time()}@example.com", "displayName": "Founder Recovery A"},
    )
    assert reg_a.status_code == 200, reg_a.text
    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": ws_a}

    # Create Project A
    p_resp = client.post(
        "/operations/projects",
        json={"title": "Recovery Board Project", "description": "Recovery testing"},
        headers=headers_a,
    )
    assert p_resp.status_code == 200, p_resp.text
    proj_a_id = str(p_resp.json()["id"])

    # 2. Workspace B (Founder B) for cross-tenant testing
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": f"exec-recovery-b-{time.time()}@example.com", "displayName": "Founder Recovery B"},
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
def test_revocation_after_frame_never_executes_an_action(advisor_stack, advisor_cluster):
    """Founder vô hiệu hoá office role sau khi frame: authority của worker bị từ chối, callback bị
    từ chối và không có analysis nào được ghi (zero side effect)."""
    board = Board(advisor_stack, advisor_cluster)
    delib_id, framed = board.frame("Should we issue convertible notes or safe notes?")

    disable = board.call(
        "post",
        f"/operations/workspaces/{board.ws}/executive-roles/cfo/disable",
        json={"reason": "Emergency role audit"},
    )
    assert disable.status_code == 200, disable.text

    auth = board.authority(delib_id, "cfo")
    assert auth.status_code in (400, 412), f"Expected 400/412, got {auth.status_code}: {auth.text}"
    assert auth.json().get("code") == "failed_precondition"

    cb = board.completed_callback(delib_id, "cfo", frame_version=framed["activeFrameVersion"])
    assert cb.status_code in (400, 412), f"Expected 400/412, got {cb.status_code}: {cb.text}"
    assert cb.json().get("code") == "failed_precondition"

    assert board.deliberation(delib_id).get("analyses") in (None, []), (
        "No analysis should be recorded after revocation"
    )


@pytest.mark.cross_plane
def test_stale_ticket_and_epoch_mismatch(advisor_stack, advisor_cluster):
    """Worker dùng frame version cũ hoặc role không được pin thì bị từ chối."""
    board = Board(advisor_stack, advisor_cluster)
    delib_id, _ = board.frame("Budget test?")

    stale = httpx.get(
        f"{board.company.base_url}/internal/operations/projects/{board.project_id}"
        f"/deliberations/{delib_id}/authority",
        params={"roleKey": "cfo", "frameVersion": 999},
        headers=worker_headers(board.ws, advisor_cluster.run_id),
        timeout=20.0,
    )
    assert stale.status_code in (400, 412), f"stale frameVersion: {stale.status_code}"
    assert stale.json().get("code") == "failed_precondition"

    unpinned = board.authority(delib_id, "cmo")
    assert unpinned.status_code in (400, 412), f"unpinned role: {unpinned.status_code}"
    assert unpinned.json().get("code") == "failed_precondition"


def test_cross_tenant_evidence_expansion_rejected(e2e_recovery_env):
    """Attempts to frame a deliberation referencing cross-project or cross-workspace

    evidence are strictly rejected by the Company server.
    """
    base_url = e2e_recovery_env["base_url"]
    headers_a = e2e_recovery_env["headers_a"]
    proj_id = e2e_recovery_env["proj_a_id"]
    ws_b = e2e_recovery_env["ws_b"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # Activate preset & CFO
    client.post(
        f"/operations/projects/{proj_id}/executive-preset",
        json={"presetKey": "startup-discovery"},
        headers=headers_a,
    )
    client.post(
        f"/operations/projects/{proj_id}/startup-team/finance/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    client.post(
        f"/operations/projects/{proj_id}/executive-roles/cfo/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )

    draft_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/draft",
        json={"title": "Cross Tenant Test"},
        headers=headers_a,
    )
    delib_id = draft_resp.json()["id"]

    # 1. Foreign project reference in evidenceSources
    foreign_proj_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}/frame",
        json={
            "question": "Assess foreign evidence?",
            "roleKeys": ["cfo"],
            "evidenceSources": [
                {
                    "sourceRef": "project://foreign-project-999/contracts/deal.pdf",
                    "sourceHash": "sha256:abc",
                    "classification": "CONFIDENTIAL",
                }
            ],
        },
        headers=headers_a,
    )
    assert foreign_proj_resp.status_code == 403, f"Expected 403, got {foreign_proj_resp.status_code}: {foreign_proj_resp.text}"

    # 2. Foreign workspace reference in evidenceSources
    foreign_ws_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}/frame",
        json={
            "question": "Assess foreign workspace evidence?",
            "roleKeys": ["cfo"],
            "evidenceSources": [
                {
                    "sourceRef": f"workspace://{ws_b}/reports/audit.pdf",
                    "sourceHash": "sha256:def",
                    "classification": "CONFIDENTIAL",
                }
            ],
        },
        headers=headers_a,
    )
    assert foreign_ws_resp.status_code == 403, f"Expected 403, got {foreign_ws_resp.status_code}: {foreign_ws_resp.text}"


@pytest.mark.cross_plane
def test_consumer_restart_and_idempotent_replay(advisor_stack, advisor_cluster):
    """Outbox redelivery sau khi worker restart: callback trùng trả cùng bản ghi, không tiến state 2 lần."""
    board = Board(advisor_stack, advisor_cluster)
    delib_id, framed = board.frame("Replay test question?")
    version = framed["activeFrameVersion"]

    first = board.completed_callback(
        delib_id, "cfo", frame_version=version, conclusion="Initial and replayed conclusion are identical."
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "COMPLETED"
    assert first.json()["state"] == "AWAITING_FOUNDER"

    replay = board.completed_callback(
        delib_id, "cfo", frame_version=version, conclusion="Initial and replayed conclusion are identical."
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == first.json()["id"]
    assert replay.json()["state"] == "AWAITING_FOUNDER"
    assert len(board.deliberation(delib_id).get("analyses", [])) == 1


def test_tampered_or_missing_worker_service_token(e2e_recovery_env):
    """Unauthorized worker callers without valid service token are rejected with 401."""
    base_url = e2e_recovery_env["base_url"]
    headers_a = e2e_recovery_env["headers_a"]
    proj_id = e2e_recovery_env["proj_a_id"]
    ws_a = e2e_recovery_env["ws_a"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Missing service token
    no_token_resp = client.get(
        f"/internal/operations/projects/{proj_id}/deliberations/1/authority",
        params={"roleKey": "cfo"},
        headers={"X-Workspace-Id": ws_a},
    )
    assert no_token_resp.status_code == 401

    # 2. Tampered service token
    bad_token_resp = client.get(
        f"/internal/operations/projects/{proj_id}/deliberations/1/authority",
        params={"roleKey": "cfo"},
        headers={
            "X-Workspace-Id": ws_a,
            "X-Service-Token": "tampered-token-12345",
        },
    )
    assert bad_token_resp.status_code == 401
