"""E2E verification of Migration 007: Operations startup profile backfill and guarded down.

Tests real migration execution against PostgreSQL:
1. Simulates pre-007 state on a fresh Project.
2. Applies 007_operations_startup_profile.up.sql.
3. Verifies TEMPLATE assignment + ASSIGNMENT_TEMPLATE_CREATED event.
4. Verifies idempotency (second run does not duplicate row or event).
5. Activates Operations as Founder.
6. Verifies 007_operations_startup_profile.down.sql fails-closed with named refusal.
"""

from __future__ import annotations

from pathlib import Path
import time
import httpx
import psycopg2
import pytest

from tests.e2e.conftest import _workspace_migrator_database_url


UP_MIGRATION_PATH = (
    Path(__file__).parent.parent.parent
    / "services"
    / "company"
    / "operations"
    / "migrations"
    / "007_operations_startup_profile.up.sql"
)

DOWN_MIGRATION_PATH = (
    Path(__file__).parent.parent.parent
    / "services"
    / "company"
    / "operations"
    / "migrations"
    / "007_operations_startup_profile.down.sql"
)


def _get_migrator_conn():
    return psycopg2.connect(_workspace_migrator_database_url(), connect_timeout=5)


def test_operations_profile_migration_lifecycle(real_company_service):
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Create isolated Workspace and Project
    email = f"mig-founder-{time.time()}@example.com"
    reg = client.post(
        "/identity/_e2e/session",
        json={"email": email, "displayName": "Migration Founder"},
    )
    assert reg.status_code == 200, f"Register failed: {reg.text}"
    auth_data = reg.json()
    token = auth_data["accessToken"]
    ws_id = str(auth_data["workspaceId"])
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws_id}

    p_resp = client.post(
        "/operations/projects",
        json={"title": "Migration Test Project", "description": "Testing 007 backfill"},
        headers=headers,
    )
    assert p_resp.status_code == 200, f"Create project failed: {p_resp.text}"
    proj_id = str(p_resp.json()["id"])

    # Ensure migration files exist
    assert UP_MIGRATION_PATH.exists(), f"Missing up migration: {UP_MIGRATION_PATH}"
    assert DOWN_MIGRATION_PATH.exists(), f"Missing down migration: {DOWN_MIGRATION_PATH}"

    up_sql = UP_MIGRATION_PATH.read_text(encoding="utf-8")
    down_sql = DOWN_MIGRATION_PATH.read_text(encoding="utf-8")

    # 2. Simulate pre-007 state: remove only this project's Operations row & event
    with _get_migrator_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM operating.project_agent_assignment_events
                WHERE workspace_id = %s AND project_id = %s
                  AND assignment_id IN (
                    SELECT id FROM operating.project_agent_assignments
                    WHERE workspace_id = %s AND project_id = %s AND profile_key = 'operations'
                  )
                """,
                (ws_id, proj_id, ws_id, proj_id),
            )
            cur.execute(
                """
                DELETE FROM operating.project_agent_assignments
                WHERE workspace_id = %s AND project_id = %s AND profile_key = 'operations'
                """,
                (ws_id, proj_id),
            )
        conn.commit()

    # 3. Apply 007 UP migration
    with _get_migrator_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(up_sql)
        conn.commit()

    # Verify: exactly one TEMPLATE row with version=1 and no workforce/spec/hash/disabled_reason
    with _get_migrator_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, state, version, agent_workforce_member_id, spec_id, spec_version, spec_hash, disabled_reason, created_by
                FROM operating.project_agent_assignments
                WHERE workspace_id = %s AND project_id = %s AND profile_key = 'operations'
                """,
                (ws_id, proj_id),
            )
            rows = cur.fetchall()
            assert len(rows) == 1, f"Expected 1 operations row, got {len(rows)}"
            (
                asg_id,
                state,
                version,
                workforce_id,
                spec_id,
                spec_ver,
                spec_hash,
                disabled_reason,
                created_by,
            ) = rows[0]
            assert state == "TEMPLATE"
            assert version == 1
            assert workforce_id is None
            assert spec_id is None
            assert spec_ver is None
            assert spec_hash is None
            assert disabled_reason is None
            assert created_by is None

            # Verify: exactly one ASSIGNMENT_TEMPLATE_CREATED event
            cur.execute(
                """
                SELECT event_type, from_state, to_state, assignment_version, actor_id, event_payload
                FROM operating.project_agent_assignment_events
                WHERE workspace_id = %s AND project_id = %s AND assignment_id = %s
                """,
                (ws_id, proj_id, asg_id),
            )
            events = cur.fetchall()
            assert len(events) == 1, f"Expected 1 event, got {len(events)}"
            ev_type, from_st, to_st, ev_ver, actor_id, payload = events[0]
            assert ev_type == "ASSIGNMENT_TEMPLATE_CREATED"
            assert from_st is None
            assert to_st == "TEMPLATE"
            assert ev_ver == 1
            assert actor_id == 0
            assert payload.get("profileKey") == "operations"
            assert payload.get("source") == "operations_profile_catalog_backfill_v1"
            assert payload.get("actorKind") == "SYSTEM_MIGRATION"

    # 4. Idempotency test: re-run 007 UP SQL, assert no duplicates created
    with _get_migrator_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(up_sql)
        conn.commit()

    with _get_migrator_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM operating.project_agent_assignments
                WHERE workspace_id = %s AND project_id = %s AND profile_key = 'operations'
                """,
                (ws_id, proj_id),
            )
            assert cur.fetchone()[0] == 1

            cur.execute(
                """
                SELECT count(*) FROM operating.project_agent_assignment_events
                WHERE workspace_id = %s AND project_id = %s AND assignment_id = %s
                """,
                (ws_id, proj_id, asg_id),
            )
            assert cur.fetchone()[0] == 1

    # 5. Founder activates Operations via API
    act_resp = client.post(
        f"/operations/projects/{proj_id}/startup-team/operations/activate",
        json={"expectedVersion": 1},
        headers=headers,
    )
    assert act_resp.status_code == 200, f"Activation failed: {act_resp.text}"
    act_data = act_resp.json()
    assert act_data["displayState"] == "ACTIVE"
    assert act_data["assignmentVersion"] == 2

    # 6. Execute DOWN migration: must refuse because Operations has usage evidence
    with _get_migrator_conn() as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg2.Error) as exc_info:
                cur.execute(down_sql)
            assert "migration 007 down refused: operations profile has usage evidence" in str(
                exc_info.value
            )
        conn.rollback()

    # 7. Verify all evidence preserved
    with _get_migrator_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT state, version, spec_id FROM operating.project_agent_assignments
                WHERE workspace_id = %s AND project_id = %s AND profile_key = 'operations'
                """,
                (ws_id, proj_id),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "ACTIVE"
            assert row[1] == 2
            assert row[2] == "cosa.agents.operations"
