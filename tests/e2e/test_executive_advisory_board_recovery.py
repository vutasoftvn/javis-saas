"""E2E Recovery, Revocation, and Tenant Isolation Verification for Executive Advisory Board.

Task 8 of plan: docs/superpowers/plans/2026-09-11-executive-advisory-board.md
Spec: docs/superpowers/specs/2026-09-11-executive-advisory-board-design.md
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


def test_revocation_after_frame_never_executes_an_action(e2e_recovery_env):
    """If Founder revokes/disables advisor grant after framing, worker authority is denied

    and callback is rejected, resulting in ZERO business side effects.
    """
    base_url = e2e_recovery_env["base_url"]
    headers_a = e2e_recovery_env["headers_a"]
    proj_id = e2e_recovery_env["proj_a_id"]
    ws_a = e2e_recovery_env["ws_a"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Activate preset & CFO
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
    act_cfo_resp = client.post(
        f"/operations/projects/{proj_id}/executive-roles/cfo/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert act_cfo_resp.status_code == 200

    # 2. Create and Frame deliberation
    draft_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/draft",
        json={"title": "Capital Strategy Deliberation"},
        headers=headers_a,
    )
    assert draft_resp.status_code == 200
    delib_id = draft_resp.json()["id"]

    frame_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}/frame",
        json={
            "question": "Should we issue convertible notes or safe notes?",
            "roleKeys": ["cfo"],
        },
        headers=headers_a,
    )
    assert frame_resp.status_code == 200
    frame_version = frame_resp.json()["activeFrameVersion"]

    # 3. Founder revokes / disables the CFO role before execution
    disable_resp = client.post(
        f"/operations/projects/{proj_id}/executive-roles/cfo/disable",
        json={"reason": "Emergency role audit"},
        headers=headers_a,
    )
    assert disable_resp.status_code == 200

    # 4. Worker checks authority -> must be rejected because role is no longer active
    worker_headers = {
        "X-Workspace-Id": ws_a,
        "X-Service-Token": _SERVICE_TOKEN,
        "Authorization": f"Bearer {_SERVICE_TOKEN}",
    }
    auth_resp = client.get(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/authority",
        params={"roleKey": "cfo"},
        headers=worker_headers,
    )
    assert auth_resp.status_code in (400, 412), f"Expected 400/412 FailedPrecondition, got {auth_resp.status_code}: {auth_resp.text}"
    assert auth_resp.json().get("code") == "failed_precondition"

    # 5. Worker tries to force-submit callback -> must also be rejected
    cb_resp = client.post(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/callback",
        json={
            "kind": "executive.analysis.completed.v1",
            "deliberation_id": delib_id,
            "frame_version": frame_version,
            "role_key": "cfo",
            "descriptor": {
                "conclusion": "Convertible notes with 20% discount.",
                "confidence": "HIGH",
            },
        },
        headers=worker_headers,
    )
    assert cb_resp.status_code in (400, 412), f"Expected 400/412, got {cb_resp.status_code}: {cb_resp.text}"
    assert cb_resp.json().get("code") == "failed_precondition"

    # 6. Verify zero side effects: no analyses recorded in ledger
    delib_check = client.get(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}",
        headers=headers_a,
    )
    assert delib_check.status_code == 200
    analyses = delib_check.json().get("analyses", [])
    assert len(analyses) == 0, "No analysis should be recorded after revocation"


def test_stale_ticket_and_epoch_mismatch(e2e_recovery_env):
    """Worker passing outdated frame version or unpinned role key is rejected."""
    base_url = e2e_recovery_env["base_url"]
    headers_a = e2e_recovery_env["headers_a"]
    proj_id = e2e_recovery_env["proj_a_id"]
    ws_a = e2e_recovery_env["ws_a"]

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

    # Create and frame deliberation
    draft_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/draft",
        json={"title": "Stale ticket test"},
        headers=headers_a,
    )
    delib_id = draft_resp.json()["id"]

    frame_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}/frame",
        json={"question": "Budget test?", "roleKeys": ["cfo"]},
        headers=headers_a,
    )
    assert frame_resp.status_code == 200

    worker_headers = {
        "X-Workspace-Id": ws_a,
        "X-Service-Token": _SERVICE_TOKEN,
        "Authorization": f"Bearer {_SERVICE_TOKEN}",
    }

    # Stale frameVersion: 999 vs 1
    stale_auth = client.get(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/authority",
        params={"roleKey": "cfo", "frameVersion": 999},
        headers=worker_headers,
    )
    assert stale_auth.status_code in (400, 412), f"Expected 400/412 for stale frameVersion, got {stale_auth.status_code}"
    assert stale_auth.json().get("code") == "failed_precondition"

    # Unpinned role: cmo
    unpinned_auth = client.get(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/authority",
        params={"roleKey": "cmo"},
        headers=worker_headers,
    )
    assert unpinned_auth.status_code in (400, 412), f"Expected 400/412 for unpinned role, got {unpinned_auth.status_code}"
    assert unpinned_auth.json().get("code") == "failed_precondition"


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


def test_consumer_restart_and_idempotent_replay(e2e_recovery_env):
    """Crash/restart replay: duplicate callbacks return identical record without double-advancing state."""
    base_url = e2e_recovery_env["base_url"]
    headers_a = e2e_recovery_env["headers_a"]
    proj_id = e2e_recovery_env["proj_a_id"]
    ws_a = e2e_recovery_env["ws_a"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # Setup role
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
        json={"title": "Idempotent Replay Test"},
        headers=headers_a,
    )
    delib_id = draft_resp.json()["id"]

    frame_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}/frame",
        json={"question": "Replay test question?", "roleKeys": ["cfo"]},
        headers=headers_a,
    )
    frame_version = frame_resp.json()["activeFrameVersion"]

    worker_headers = {
        "X-Workspace-Id": ws_a,
        "X-Service-Token": _SERVICE_TOKEN,
        "Authorization": f"Bearer {_SERVICE_TOKEN}",
    }

    callback_payload = {
        "kind": "executive.analysis.completed.v1",
        "deliberation_id": delib_id,
        "frame_version": frame_version,
        "role_key": "cfo",
        "descriptor": {
            "run_id": "run_replay_test_001",
            "conclusion": "Initial and replayed conclusion are identical.",
            "confidence": "HIGH",
            "evidence_claims": [],
        },
    }

    # Initial delivery
    first_resp = client.post(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/callback",
        json=callback_payload,
        headers=worker_headers,
    )
    assert first_resp.status_code == 200
    first_data = first_resp.json()
    assert first_data["status"] == "COMPLETED"
    assert first_data["state"] == "AWAITING_FOUNDER"

    # Replayed delivery (e.g. outbox redelivery after worker restart)
    replay_resp = client.post(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/callback",
        json=callback_payload,
        headers=worker_headers,
    )
    assert replay_resp.status_code == 200
    replay_data = replay_resp.json()
    assert replay_data["id"] == first_data["id"]
    assert replay_data["state"] == "AWAITING_FOUNDER"

    # Verify single analysis entry in ledger
    delib_check = client.get(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}",
        headers=headers_a,
    ).json()
    assert len(delib_check.get("analyses", [])) == 1


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
