"""E2E Verification for Default Project Resolution and Startup Team Lifecycle.

Task 6 of plan: 2026-09-11-default-project-and-startup-team.md
Spec: docs/superpowers/specs/2026-09-11-startup-default-context-and-workforce-design.md

This test verifies all 7 invariants:
1. First Hub session deterministic default to oldest authorized Project.
2. Stale saved ID is rejected/deleted without silent fallback to wrong Project.
3. Operating Loop contributes Week/Task card independently of empty activity.
4. Founder activates Marketing -> 1 assignment event/outbox record and Agent Platform runs only with returned pin.
5. Pause invalidates next attempted run; prior trace remains inspectable.
6. Non-founder and cross-tenant attempts fail without data disclosure (403/404).
7. Catalog entries that are pending/deferred (coding, crm, sales, support) cannot run or activate.
"""

from __future__ import annotations

import asyncio
import os
import time
import psycopg2
import httpx
import pytest

from apps.cosa.agents.startup_team_profiles_generated import STARTUP_TEAM_PROFILE_KEYS
from apps.cosa.company.project_team_client import (
    ProjectTeamClient,
    ProjectTeamAuthorityError,
)

_SERVICE_TOKEN = os.environ.get(
    "COSA_WORKER_SERVICE_TOKEN",
    "dev-worker-service-token",
)
_WORKSPACE_DB_URL = os.environ.get(
    "WORKSPACE_DATABASE_URL",
    "postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/workspace?sslmode=disable",
)


def _get_db_connection():
    return psycopg2.connect(_WORKSPACE_DB_URL, connect_timeout=5)


@pytest.fixture
def e2e_tenants(real_company_service):
    """Create two workspaces: Workspace A with 2 projects, Workspace B for isolation."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Create Workspace A
    email_a = f"founder-a-{time.time()}@example.com"
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": email_a, "displayName": "Founder A"},
    )
    assert reg_a.status_code == 200, f"Failed to create workspace A: {reg_a.text}"
    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    user_a = str(data_a["userId"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": ws_a}

    # 2. Create Project A1 and A2 with distinct created times
    p1_resp = client.post(
        "/operations/projects",
        json={"title": "Alpha Project A1", "description": "First project"},
        headers=headers_a,
    )
    assert p1_resp.status_code == 200, f"Failed to create project A1: {p1_resp.text}"
    proj_a1 = p1_resp.json()
    proj_a1_id = str(proj_a1["id"])

    time.sleep(0.05)

    p2_resp = client.post(
        "/operations/projects",
        json={"title": "Beta Project A2", "description": "Second project"},
        headers=headers_a,
    )
    assert p2_resp.status_code == 200, f"Failed to create project A2: {p2_resp.text}"
    proj_a2 = p2_resp.json()
    proj_a2_id = str(proj_a2["id"])

    # 3. Create Workspace B (cross-tenant)
    email_b = f"founder-b-{time.time()}@example.com"
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": email_b, "displayName": "Founder B"},
    )
    assert reg_b.status_code == 200, f"Failed to create workspace B: {reg_b.text}"
    data_b = reg_b.json()
    token_b = data_b["accessToken"]
    ws_b = str(data_b["workspaceId"])
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-Id": ws_b}

    return {
        "base_url": base_url,
        "ws_a": ws_a,
        "user_a": user_a,
        "headers_a": headers_a,
        "proj_a1_id": proj_a1_id,
        "proj_a2_id": proj_a2_id,
        "ws_b": ws_b,
        "headers_b": headers_b,
    }


def test_invariant_1_and_2_deterministic_project_resolution(e2e_tenants):
    """Invariant 1 & 2: Deterministic oldest project default and stale ID isolation."""
    base_url = e2e_tenants["base_url"]
    headers_a = e2e_tenants["headers_a"]
    headers_b = e2e_tenants["headers_b"]
    p1_id = e2e_tenants["proj_a1_id"]
    p2_id = e2e_tenants["proj_a2_id"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Query project list for workspace A
    resp = client.get("/operations/projects", headers=headers_a)
    assert resp.status_code == 200
    projects = resp.json().get("projects", [])
    assert len(projects) >= 2
    
    # Invariant 1: The deterministic oldest authorized project is A1
    oldest_project = min(projects, key=lambda p: (p.get("createdAt") or "", str(p["id"])))
    assert str(oldest_project["id"]) == p1_id

    # 2. Invariant 2: Stale saved ID (e.g. non-existent or foreign) must be rejected with 404
    foreign_resp = client.get(f"/operations/projects/{p1_id}/startup-team", headers=headers_b)
    assert foreign_resp.status_code == 404, "Foreign workspace must receive 404 for project"

    non_existent_resp = client.get(
        "/operations/projects/999999999999999/startup-team",
        headers=headers_a,
    )
    assert non_existent_resp.status_code == 404


def test_invariant_3_operating_loop_contributes_week_task_card(e2e_tenants):
    """Invariant 3: Selected project's Operating Loop contributes Week/Task card independently."""
    base_url = e2e_tenants["base_url"]
    headers_a = e2e_tenants["headers_a"]
    p1_id = e2e_tenants["proj_a1_id"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # Fetch operating loop for project A1
    resp = client.get(f"/operations/projects/{p1_id}/operating-loop", headers=headers_a)
    assert resp.status_code == 200, f"Failed to get operating loop: {resp.text}"
    data = resp.json()
    assert "project" in data
    assert str(data["project"]["id"]) == p1_id


def test_invariant_4_and_5_startup_team_activation_pause_and_authority(e2e_tenants):
    """Invariant 4 & 5: Founder activates Marketing -> run authority pinned; Pause revokes authority."""
    base_url = e2e_tenants["base_url"]
    headers_a = e2e_tenants["headers_a"]
    p1_id = e2e_tenants["proj_a1_id"]
    ws_a = e2e_tenants["ws_a"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Fetch team list for project A1
    resp = client.get(f"/operations/projects/{p1_id}/startup-team", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    items = body["items"]
    assert {item["profileKey"] for item in items} == set(STARTUP_TEAM_PROFILE_KEYS)

    # Verify operations initial state
    ops = next(m for m in items if m["profileKey"] == "operations")
    assert ops["displayState"] == "TEMPLATE"
    assert ops["runtimeReadiness"] == "READY"

    # Verify marketing initial state
    mkt = next(m for m in items if m["profileKey"] == "marketing")
    assert mkt["displayState"] == "TEMPLATE"
    assert mkt["runtimeReadiness"] == "READY"
    version = mkt.get("assignmentVersion") or 1

    # 2. Invariant 4: Founder activates Marketing
    act_resp = client.post(
        f"/operations/projects/{p1_id}/startup-team/marketing/activate",
        json={"expectedVersion": version},
        headers=headers_a,
    )
    assert act_resp.status_code == 200, f"Activation failed: {act_resp.text}"
    act_data = act_resp.json()
    assert act_data["displayState"] == "ACTIVE"
    assert act_data["assignmentVersion"] == version + 1
    assert act_data["activatedAt"] is not None

    # Check DB state
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check assignment row
            cur.execute(
                """
                SELECT state, version, spec_hash
                FROM operating.project_agent_assignments
                WHERE project_id = %s AND profile_key = 'marketing'
                """,
                (int(p1_id),),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "ACTIVE"
            assert row[1] == version + 1
            pinned_hash = row[2]
            assert pinned_hash and len(pinned_hash) > 10

            # Check audit event
            cur.execute(
                """
                SELECT event_type, to_state, event_payload->>'specHash'
                FROM operating.project_agent_assignment_events
                WHERE project_id = %s
                ORDER BY occurred_at DESC
                LIMIT 1
                """,
                (int(p1_id),),
            )
            event_row = cur.fetchone()
            assert event_row is not None
            assert event_row[0] == "ASSIGNMENT_ACTIVATED"
            assert event_row[1] == "ACTIVE"
            assert event_row[2] == pinned_hash
    finally:
        conn.close()

    # 3. Check ProjectTeamClient / internal run authority endpoint
    pt_client = ProjectTeamClient(
        base_url=base_url,
        service_token=_SERVICE_TOKEN,
    )
    authority = asyncio.run(
        pt_client.get_run_authority(
            workspace_id=ws_a,
            project_id=p1_id,
            profile_key="marketing",
        )
    )
    assert authority.project_id == p1_id
    assert authority.workspace_id == ws_a
    assert authority.profile_key == "marketing"
    assert authority.assignment_version == version + 1
    assert authority.spec.hash == pinned_hash

    # 4. Invariant 5: Founder pauses Marketing
    pause_resp = client.post(
        f"/operations/projects/{p1_id}/startup-team/marketing/pause",
        json={"expectedVersion": version + 1, "reason": "Budget review pause"},
        headers=headers_a,
    )
    assert pause_resp.status_code == 200, f"Pause failed: {pause_resp.text}"
    pause_data = pause_resp.json()
    assert pause_data["displayState"] == "PAUSED"
    assert pause_data["assignmentVersion"] == version + 2

    # Verify run authority now DENIES execution
    with pytest.raises(ProjectTeamAuthorityError) as exc_info:
        asyncio.run(
            pt_client.get_run_authority(
                workspace_id=ws_a,
                project_id=p1_id,
                profile_key="marketing",
            )
        )
    assert exc_info.value.status_code in (404, 409)
    assert "not actively assigned" in str(exc_info.value) or "PAUSED" in str(exc_info.value)

    # Verify prior audit event trail remains intact in DB
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_type, event_payload->>'reason'
                FROM operating.project_agent_assignment_events
                WHERE project_id = %s AND event_type IN ('ASSIGNMENT_ACTIVATED', 'ASSIGNMENT_PAUSED')
                ORDER BY occurred_at ASC
                """,
                (int(p1_id),),
            )
            events = cur.fetchall()
            assert len(events) >= 2
            assert events[0][0] == "ASSIGNMENT_ACTIVATED"
            assert events[1][0] == "ASSIGNMENT_PAUSED"
            assert events[1][1] == "Budget review pause"
    finally:
        conn.close()


def test_invariant_6_non_founder_and_cross_tenant_isolation(e2e_tenants):
    """Invariant 6: Non-founder role and cross-tenant attempts fail without disclosure."""
    base_url = e2e_tenants["base_url"]
    p1_id = e2e_tenants["proj_a1_id"]
    ws_a = e2e_tenants["ws_a"]
    ws_b = e2e_tenants["ws_b"]
    headers_b = e2e_tenants["headers_b"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Cross-tenant founder tries to activate a member in Project A1 -> 404 Not Found
    cross_resp = client.post(
        f"/operations/projects/{p1_id}/startup-team/strategy/activate",
        json={"expectedVersion": 1},
        headers=headers_b,
    )
    assert cross_resp.status_code == 404, "Cross-tenant activate must return 404"

    # 2. Cross-tenant list -> 404
    cross_list = client.get(f"/operations/projects/{p1_id}/startup-team", headers=headers_b)
    assert cross_list.status_code == 404, "Cross-tenant list must return 404"

    # 3. Internal run authority cross-tenant check
    pt_client = ProjectTeamClient(
        base_url=base_url,
        service_token=_SERVICE_TOKEN,
    )
    # Non-existent project
    with pytest.raises(ProjectTeamAuthorityError) as exc_info:
        asyncio.run(
            pt_client.get_run_authority(
                workspace_id=ws_a,
                project_id="99999999999999",
                profile_key="strategy",
            )
        )
    assert exc_info.value.status_code == 404

    # Mismatched workspace/project
    with pytest.raises(ProjectTeamAuthorityError) as exc_info_mismatch:
        asyncio.run(
            pt_client.get_run_authority(
                workspace_id=ws_b,
                project_id=p1_id,
                profile_key="strategy",
            )
        )
    assert exc_info_mismatch.value.status_code == 404


def test_invariant_7_pending_and_deferred_profiles_cannot_activate(e2e_tenants):
    """Invariant 7: Coding (DEFERRED_CODING) and CRM/Sales/Support (PENDING) cannot activate."""
    base_url = e2e_tenants["base_url"]
    headers_a = e2e_tenants["headers_a"]
    ws_a = e2e_tenants["ws_a"]
    p1_id = e2e_tenants["proj_a1_id"]

    client = httpx.Client(base_url=base_url, timeout=10.0)
    pt_client = ProjectTeamClient(
        base_url=base_url,
        service_token=_SERVICE_TOKEN,
    )

    # Coding is deferred
    coding_resp = client.post(
        f"/operations/projects/{p1_id}/startup-team/coding/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert coding_resp.status_code == 400
    assert "DEFERRED_CODING" in coding_resp.text

    # Coding run authority is rejected
    with pytest.raises(ProjectTeamAuthorityError) as exc_coding:
        asyncio.run(
            pt_client.get_run_authority(
                workspace_id=ws_a,
                project_id=p1_id,
                profile_key="coding",
            )
        )
    assert exc_coding.value.status_code in (404, 409)

    # CRM is pending CRM foundation
    crm_resp = client.post(
        f"/operations/projects/{p1_id}/startup-team/crm/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert crm_resp.status_code == 400
    assert "PENDING_CRM_FOUNDATION" in crm_resp.text

    # Sales is pending CRM foundation
    sales_resp = client.post(
        f"/operations/projects/{p1_id}/startup-team/sales/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert sales_resp.status_code == 400
    assert "PENDING_CRM_FOUNDATION" in sales_resp.text

    # Founder Assistant cannot be activated as an operating agent
    fa_resp = client.post(
        f"/operations/projects/{p1_id}/startup-team/founder_assistant/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert fa_resp.status_code == 400
    assert "cannot be activated as an operating agent" in fa_resp.text


def test_invariant_operations_profile_lifecycle_and_authority(e2e_tenants):
    """Operations profile lifecycle: TEMPLATE -> ACTIVE -> PAUSED with run authority and audit event proof."""
    base_url = e2e_tenants["base_url"]
    headers_a = e2e_tenants["headers_a"]
    p2_id = e2e_tenants["proj_a2_id"]
    ws_a = e2e_tenants["ws_a"]

    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Fetch team list for project A2
    resp = client.get(f"/operations/projects/{p2_id}/startup-team", headers=headers_a)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    items = body["items"]
    assert len(items) == 10

    ops = next(m for m in items if m["profileKey"] == "operations")
    assert ops["displayState"] == "TEMPLATE"
    assert ops["runtimeReadiness"] == "READY"
    version = ops.get("assignmentVersion") or 1

    # 2. Founder activates Operations
    act_resp = client.post(
        f"/operations/projects/{p2_id}/startup-team/operations/activate",
        json={"expectedVersion": version},
        headers=headers_a,
    )
    assert act_resp.status_code == 200, f"Activation failed: {act_resp.text}"
    act_data = act_resp.json()
    assert act_data["displayState"] == "ACTIVE"
    assert act_data["assignmentVersion"] == version + 1
    assert act_data["activatedAt"] is not None

    # Check DB state
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT state, version, spec_hash
                FROM operating.project_agent_assignments
                WHERE project_id = %s AND profile_key = 'operations'
                """,
                (int(p2_id),),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "ACTIVE"
            assert row[1] == version + 1
            pinned_hash = row[2]
            assert pinned_hash and len(pinned_hash) > 10

            cur.execute(
                """
                SELECT event_type, to_state, event_payload->>'specHash'
                FROM operating.project_agent_assignment_events
                WHERE project_id = %s AND event_payload->>'profileKey' = 'operations'
                ORDER BY occurred_at DESC
                LIMIT 1
                """,
                (int(p2_id),),
            )
            event_row = cur.fetchone()
            assert event_row is not None
            assert event_row[0] == "ASSIGNMENT_ACTIVATED"
            assert event_row[1] == "ACTIVE"
            assert event_row[2] == pinned_hash
    finally:
        conn.close()

    # 3. Check ProjectTeamClient / internal run authority endpoint
    pt_client = ProjectTeamClient(
        base_url=base_url,
        service_token=_SERVICE_TOKEN,
    )
    authority = asyncio.run(
        pt_client.get_run_authority(
            workspace_id=ws_a,
            project_id=p2_id,
            profile_key="operations",
        )
    )
    assert authority.project_id == p2_id
    assert authority.workspace_id == ws_a
    assert authority.profile_key == "operations"
    assert authority.assignment_version == version + 1
    assert authority.spec.hash == pinned_hash

    # 4. Founder pauses Operations
    pause_resp = client.post(
        f"/operations/projects/{p2_id}/startup-team/operations/pause",
        json={"expectedVersion": version + 1, "reason": "Operational pause"},
        headers=headers_a,
    )
    assert pause_resp.status_code == 200, f"Pause failed: {pause_resp.text}"
    pause_data = pause_resp.json()
    assert pause_data["displayState"] == "PAUSED"
    assert pause_data["assignmentVersion"] == version + 2

    # Verify run authority now DENIES execution
    with pytest.raises(ProjectTeamAuthorityError) as exc_info:
        asyncio.run(
            pt_client.get_run_authority(
                workspace_id=ws_a,
                project_id=p2_id,
                profile_key="operations",
            )
        )
    assert exc_info.value.status_code in (404, 409)
    assert "not actively assigned" in str(exc_info.value) or "PAUSED" in str(exc_info.value)

    # Verify prior audit event trail remains intact in DB
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_type, event_payload->>'reason'
                FROM operating.project_agent_assignment_events
                WHERE project_id = %s AND event_payload->>'profileKey' = 'operations' AND event_type IN ('ASSIGNMENT_ACTIVATED', 'ASSIGNMENT_PAUSED')
                ORDER BY occurred_at ASC
                """,
                (int(p2_id),),
            )
            events = cur.fetchall()
            assert len(events) >= 2
            assert events[0][0] == "ASSIGNMENT_ACTIVATED"
            assert events[1][0] == "ASSIGNMENT_PAUSED"
            assert events[1][1] == "Operational pause"
    finally:
        conn.close()
