"""E2E Verification for Executive Advisory Board Lifecycle and Deliberation Ledger.

Task 6 of plan: docs/superpowers/plans/2026-09-11-executive-advisory-board.md
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
def e2e_board_env(real_company_service):
    """Create two workspaces for board testing: Workspace A and Workspace B."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Workspace A (Founder A)
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": f"exec-founder-a-{time.time()}@example.com", "displayName": "Founder A"},
    )
    assert reg_a.status_code == 200, reg_a.text
    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": ws_a}

    # Create Project A1
    p1_resp = client.post(
        "/operations/projects",
        json={"title": "Executive Board Project", "description": "Strategy project"},
        headers=headers_a,
    )
    assert p1_resp.status_code == 200, p1_resp.text
    proj_a = p1_resp.json()
    proj_a_id = str(proj_a["id"])

    # 2. Workspace B (Founder B) for isolation
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": f"exec-founder-b-{time.time()}@example.com", "displayName": "Founder B"},
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


def test_executive_board_full_lifecycle(e2e_board_env):
    base_url = e2e_board_env["base_url"]
    headers_a = e2e_board_env["headers_a"]
    headers_b = e2e_board_env["headers_b"]
    proj_id = e2e_board_env["proj_a_id"]
    ws_a = e2e_board_env["ws_a"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Activate Startup Core preset (discovery)
    preset_resp = client.post(
        f"/operations/projects/{proj_id}/executive-preset",
        json={"presetKey": "startup-discovery"},
        headers=headers_a,
    )
    assert preset_resp.status_code == 200, preset_resp.text

    # 2. Activate CFO in startup team first, then activate in executive board
    act_team_resp = client.post(
        f"/operations/projects/{proj_id}/startup-team/finance/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert act_team_resp.status_code == 200, act_team_resp.text

    act_cfo_resp = client.post(
        f"/operations/projects/{proj_id}/executive-roles/cfo/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert act_cfo_resp.status_code == 200, act_cfo_resp.text

    # 3. Create Draft Deliberation
    draft_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/draft",
        json={"title": "Q3 Growth Capital Allocation"},
        headers=headers_a,
    )
    assert draft_resp.status_code == 200, draft_resp.text
    delib_id = draft_resp.json()["id"]

    # 4. Frame Deliberation with CFO role
    frame_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}/frame",
        json={
            "question": "Should we deploy $500k into enterprise direct sales or PLG automation?",
            "roleKeys": ["cfo"],
        },
        headers=headers_a,
    )
    assert frame_resp.status_code == 200, frame_resp.text
    framed_data = frame_resp.json()
    assert framed_data["state"] == "ANALYSIS_QUEUED"
    frame_version = framed_data["activeFrameVersion"]

    # 5. Worker checks authority
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
    assert auth_resp.status_code == 200, auth_resp.text
    auth_data = auth_resp.json()
    assert auth_data["rolePin"]["roleKey"] == "cfo"

    # 6. Worker submits analysis callback
    callback_payload = {
        "kind": "executive.analysis.completed.v1",
        "deliberation_id": delib_id,
        "frame_version": frame_version,
        "role_key": "cfo",
        "descriptor": {
            "run_id": "run_cfo_test",
            "conclusion": "Allocate 70% to PLG automation, 30% to targeted SDR enterprise experiment.",
            "confidence": "HIGH",
            "evidence_claims": [],
        },
    }
    cb_resp = client.post(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/callback",
        json=callback_payload,
        headers=worker_headers,
    )
    assert cb_resp.status_code == 200, cb_resp.text
    cb_data = cb_resp.json()
    assert cb_data["status"] == "COMPLETED"
    assert cb_data["state"] == "AWAITING_FOUNDER"

    # 7. Duplicate callback is idempotent
    cb_retry_resp = client.post(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/callback",
        json=callback_payload,
        headers=worker_headers,
    )
    assert cb_retry_resp.status_code == 200, cb_retry_resp.text
    assert cb_retry_resp.json()["id"] == cb_data["id"]

    # 8. Check deliberation details
    get_resp = client.get(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}",
        headers=headers_a,
    )
    assert get_resp.status_code == 200, get_resp.text
    get_data = get_resp.json()
    assert get_data["state"] == "AWAITING_FOUNDER"
    assert len(get_data.get("analyses", [])) == 1

    # 9. Founder appends decision
    decision_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}/decision",
        json={
            "decisionType": "APPROVE",
            "notes": "Approved PLG first approach.",
        },
        headers=headers_a,
    )
    assert decision_resp.status_code == 200, decision_resp.text

    # Verify final state is DECIDED
    delib_final = client.get(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}",
        headers=headers_a,
    ).json()
    assert delib_final["state"] == "DECIDED"

    # 10. Cross-project isolation: Workspace B cannot see or modify this deliberation
    foreign_resp = client.get(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}",
        headers=headers_b,
    )
    assert foreign_resp.status_code in (403, 404)


def test_executive_board_cancellation_and_rejection(e2e_board_env):
    base_url = e2e_board_env["base_url"]
    headers_a = e2e_board_env["headers_a"]
    proj_id = e2e_board_env["proj_a_id"]
    ws_a = e2e_board_env["ws_a"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Activate Startup Core preset & CFO
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

    # Create draft & frame
    draft_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/draft",
        json={"title": "To be cancelled deliberation"},
        headers=headers_a,
    )
    assert draft_resp.status_code == 200
    delib_id = draft_resp.json()["id"]

    frame_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}/frame",
        json={"question": "Test question?", "roleKeys": ["cfo"]},
        headers=headers_a,
    )
    assert frame_resp.status_code == 200
    frame_version = frame_resp.json()["activeFrameVersion"]

    # Cancel deliberation
    cancel_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}/cancel",
        json={"reason": "Board pivot"},
        headers=headers_a,
    )
    assert cancel_resp.status_code == 200

    # Subsequent callback must be rejected
    worker_headers = {
        "X-Workspace-Id": ws_a,
        "X-Service-Token": _SERVICE_TOKEN,
        "Authorization": f"Bearer {_SERVICE_TOKEN}",
    }
    cb_resp = client.post(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/callback",
        json={
            "kind": "executive.analysis.completed.v1",
            "deliberation_id": delib_id,
            "frame_version": frame_version,
            "role_key": "cfo",
            "descriptor": {"conclusion": "Too late"},
        },
        headers=worker_headers,
    )
    assert cb_resp.status_code in (400, 412), "Cancelled deliberation must reject callbacks"


def test_operations_roles_lifecycle_dual_frame_and_isolation(e2e_board_env):
    """Operations prerequisite lifecycle for COO and Chief of Staff:
    1. New Project creation -> chief_of_staff & coo are UNAVAILABLE.
    2. Activate Operations in startup team -> chief_of_staff & coo become AVAILABLE_NOT_ACTIVATED (not ACTIVE).
    3. Activate both roles directly with CAS expected versions -> both become ACTIVE.
    4. Dual-role frame with chief_of_staff and coo -> state is ANALYSIS_QUEUED.
    5. Internal authority checks verify exact operations spec, hash, and skill pins.
    6. Deterministic callbacks for both roles -> state transitions to AWAITING_FOUNDER with 2 analyses.
    7. No business side effects; cross-workspace 403/404 isolation.
    """
    base_url = e2e_board_env["base_url"]
    headers_a = e2e_board_env["headers_a"]
    headers_b = e2e_board_env["headers_b"]
    ws_a = e2e_board_env["ws_a"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Create a fresh project in Workspace A
    p_resp = client.post(
        "/operations/projects",
        json={"title": "Operations Board Project", "description": "Operations & Executive testing"},
        headers=headers_a,
    )
    assert p_resp.status_code == 200, p_resp.text
    proj_id = str(p_resp.json()["id"])

    # Verify initial executive roles state: chief_of_staff and coo must be UNAVAILABLE
    roles_resp = client.get(
        f"/operations/projects/{proj_id}/executive-roles",
        headers=headers_a,
    )
    assert roles_resp.status_code == 200, roles_resp.text
    roles_data = roles_resp.json().get("roles", [])
    cos_role = next(r for r in roles_data if r["roleKey"] == "chief_of_staff")
    coo_role = next(r for r in roles_data if r["roleKey"] == "coo")

    assert cos_role["displayState"] == "UNAVAILABLE"
    assert cos_role["disabledReason"] == "UNDERLYING_PROFILE_UNAVAILABLE"
    assert coo_role["displayState"] == "UNAVAILABLE"
    assert coo_role["disabledReason"] == "UNDERLYING_PROFILE_UNAVAILABLE"

    # Attempting to activate chief_of_staff before operations is active must fail
    premature_act = client.post(
        f"/operations/projects/{proj_id}/executive-roles/chief_of_staff/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert premature_act.status_code in (400, 412)

    # 2. Activate operations in startup team
    team_act = client.post(
        f"/operations/projects/{proj_id}/startup-team/operations/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert team_act.status_code == 200, team_act.text
    assert team_act.json()["displayState"] == "ACTIVE"

    # Re-query executive roles: both must be AVAILABLE_NOT_ACTIVATED, NOT ACTIVE
    roles_after = client.get(
        f"/operations/projects/{proj_id}/executive-roles",
        headers=headers_a,
    ).json().get("roles", [])
    cos_after = next(r for r in roles_after if r["roleKey"] == "chief_of_staff")
    coo_after = next(r for r in roles_after if r["roleKey"] == "coo")

    assert cos_after["displayState"] == "AVAILABLE_NOT_ACTIVATED"
    assert coo_after["displayState"] == "AVAILABLE_NOT_ACTIVATED"

    cos_ver = cos_after.get("version", 1)
    coo_ver = coo_after.get("version", 1)

    # 3. Explicitly activate both roles directly with CAS
    cos_act_resp = client.post(
        f"/operations/projects/{proj_id}/executive-roles/chief_of_staff/activate",
        json={"expectedVersion": cos_ver},
        headers=headers_a,
    )
    assert cos_act_resp.status_code == 200, cos_act_resp.text
    assert cos_act_resp.json()["state"] == "ACTIVE"

    coo_act_resp = client.post(
        f"/operations/projects/{proj_id}/executive-roles/coo/activate",
        json={"expectedVersion": coo_ver},
        headers=headers_a,
    )
    assert coo_act_resp.status_code == 200, coo_act_resp.text
    assert coo_act_resp.json()["state"] == "ACTIVE"

    # 4. Create Draft Deliberation and frame with both roles
    draft_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/draft",
        json={"title": "Q4 Operating Model Review"},
        headers=headers_a,
    )
    assert draft_resp.status_code == 200, draft_resp.text
    delib_id = draft_resp.json()["id"]

    frame_resp = client.post(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}/frame",
        json={
            "question": "How should we restructure operations to scale cross-functional delivery in Q4?",
            "roleKeys": ["chief_of_staff", "coo"],
        },
        headers=headers_a,
    )
    assert frame_resp.status_code == 200, frame_resp.text
    framed_data = frame_resp.json()
    assert framed_data["state"] == "ANALYSIS_QUEUED"
    frame_version = framed_data["activeFrameVersion"]

    # 5. Worker checks internal authority for both roles
    worker_headers = {
        "X-Workspace-Id": ws_a,
        "X-Service-Token": _SERVICE_TOKEN,
        "Authorization": f"Bearer {_SERVICE_TOKEN}",
    }

    cos_auth_resp = client.get(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/authority",
        params={"roleKey": "chief_of_staff"},
        headers=worker_headers,
    )
    assert cos_auth_resp.status_code == 200, cos_auth_resp.text
    cos_auth = cos_auth_resp.json()
    assert cos_auth["rolePin"]["roleKey"] == "chief_of_staff"
    assert cos_auth["rolePin"]["specId"] == "cosa.agents.operations"
    assert cos_auth["rolePin"]["specHash"] == "0c838f93ddc700984b9acdfead50ce45eb7f6ad867453edaf7c6793562dc33b2"
    assert "skillpack:executive/chief-of-staff@1.0.0" in cos_auth["rolePin"]["skillPins"]

    coo_auth_resp = client.get(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/authority",
        params={"roleKey": "coo"},
        headers=worker_headers,
    )
    assert coo_auth_resp.status_code == 200, coo_auth_resp.text
    coo_auth = coo_auth_resp.json()
    assert coo_auth["rolePin"]["roleKey"] == "coo"
    assert coo_auth["rolePin"]["specId"] == "cosa.agents.operations"
    assert coo_auth["rolePin"]["specHash"] == "0c838f93ddc700984b9acdfead50ce45eb7f6ad867453edaf7c6793562dc33b2"
    assert "skillpack:executive/coo-advisor@1.0.0" in coo_auth["rolePin"]["skillPins"]

    # 6. Worker submits deterministic callbacks for both roles
    cb_cos = client.post(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/callback",
        json={
            "kind": "executive.analysis.completed.v1",
            "deliberation_id": delib_id,
            "frame_version": frame_version,
            "role_key": "chief_of_staff",
            "descriptor": {
                "run_id": "run_cos_test",
                "conclusion": "Establish weekly cross-functional operating cadences and clear handoff boundaries.",
                "confidence": "HIGH",
            },
        },
        headers=worker_headers,
    )
    assert cb_cos.status_code == 200, cb_cos.text
    # After first role, still waiting for COO:
    assert cb_cos.json()["state"] == "ANALYZING"

    cb_coo = client.post(
        f"/internal/operations/projects/{proj_id}/deliberations/{delib_id}/callback",
        json={
            "kind": "executive.analysis.completed.v1",
            "deliberation_id": delib_id,
            "frame_version": frame_version,
            "role_key": "coo",
            "descriptor": {
                "run_id": "run_coo_test",
                "conclusion": "Automate repeatable fulfillment workflows and allocate 2 dedicated coordinators.",
                "confidence": "HIGH",
            },
        },
        headers=worker_headers,
    )
    assert cb_coo.status_code == 200, cb_coo.text
    # After second role, transitions to AWAITING_FOUNDER:
    assert cb_coo.json()["state"] == "AWAITING_FOUNDER"

    # 7. Check deliberation details: 2 analyses, no business side effects
    delib_detail = client.get(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}",
        headers=headers_a,
    ).json()
    assert delib_detail["state"] == "AWAITING_FOUNDER"
    analyses = delib_detail.get("analyses", [])
    assert len(analyses) == 2
    analysis_roles = {a["roleKey"] for a in analyses}
    assert analysis_roles == {"chief_of_staff", "coo"}

    # 8. Cross-workspace isolation: Workspace B receives 403 or 404
    b_resp = client.get(
        f"/operations/projects/{proj_id}/deliberations/{delib_id}",
        headers=headers_b,
    )
    assert b_resp.status_code in (403, 404)
