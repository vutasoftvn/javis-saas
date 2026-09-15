"""Public-HTTP proof for the Project Operating Loop authority boundary.

This test deliberately creates two projects in one workspace.  It never
imports a Company service or writes the database directly: all setup and
assertions use the same public HTTP surface as a Founder client.

The V2 WorkspaceAgent provisioning command is intentionally *not* faked here.
At the time this test was added, the public contract exposes a Project deploy
command which requires an exact ``workspaceAgentId``, but no public command or
query which can create/list such an agent.  The positive V2 deployment case
therefore remains a release blocker rather than being papered over with an
internal fixture or a guessed identifier.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest


def _create_project(client: httpx.Client, headers: dict[str, str], title: str) -> str:
    response = client.post(
        "/operations/projects",
        json={"title": title, "description": f"E2E scope fixture for {title}"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return str(response.json()["id"])


def _seed_project_loop(
    client: httpx.Client, headers: dict[str, str], project_id: str, label: str
) -> dict[str, str]:
    """Create one complete Objective -> KR -> Initiative -> Cycle -> Week -> Commitment -> Task chain."""
    prefix = f"scope-e2e-{label}"

    objective = client.post(
        f"/operations/projects/{project_id}/operating-loop/objectives",
        json={"title": f"{prefix} objective", "why": "prove project isolation"},
        headers=headers,
    )
    assert objective.status_code == 200, objective.text

    key_result = client.post(
        f"/operations/projects/{project_id}/operating-loop/key-results",
        json={
            "objectiveId": objective.json()["id"],
            "title": f"{prefix} key result",
            "targetValue": 1,
            "unit": "proof",
        },
        headers=headers,
    )
    assert key_result.status_code == 200, key_result.text

    initiative = client.post(
        f"/operations/projects/{project_id}/operating-loop/initiatives",
        json={"keyResultId": key_result.json()["id"], "title": f"{prefix} initiative"},
        headers=headers,
    )
    assert initiative.status_code == 200, initiative.text

    cycle = client.post(
        f"/operations/projects/{project_id}/operating-loop/cycles",
        json={"theme": f"{prefix} cycle", "durationWeeks": 2, "timezone": "Asia/Ho_Chi_Minh"},
        headers=headers,
    )
    assert cycle.status_code == 200, cycle.text

    # Creating a cycle atomically materializes its weeks.  This endpoint adds
    # the visible week content and verifies that the public week route remains
    # scoped to the same Project.
    week = client.post(
        f"/operations/projects/{project_id}/operating-loop/weeks",
        json={
            "cycleId": cycle.json()["id"],
            "weekNo": 1,
            "focus": f"{prefix} weekly focus",
            "mission": "prove scope",
        },
        headers=headers,
    )
    assert week.status_code == 200, week.text

    commitment = client.post(
        f"/operations/projects/{project_id}/operating-loop/commitments",
        json={
            "weeklyPlanId": week.json()["id"],
            "initiativeId": initiative.json()["id"],
            "title": f"{prefix} commitment",
            "purposeType": "KR",
            "purposeRef": key_result.json()["id"],
        },
        headers=headers,
    )
    assert commitment.status_code == 200, commitment.text

    task = client.post(
        f"/operations/projects/{project_id}/operating-loop/tasks",
        json={
            "title": f"{prefix} task",
            "weeklyCommitmentId": commitment.json()["id"],
            "initiativeId": initiative.json()["id"],
            "priority": "high",
            "status": "todo",
        },
        headers=headers,
    )
    assert task.status_code == 200, task.text

    return {
        "objective_id": str(objective.json()["id"]),
        "key_result_id": str(key_result.json()["id"]),
        "initiative_id": str(initiative.json()["id"]),
        "cycle_id": str(cycle.json()["id"]),
        "week_id": str(week.json()["id"]),
        "commitment_id": str(commitment.json()["id"]),
        "task_id": str(task.json()["id"]),
        "task_title": str(task.json()["title"]),
    }


@pytest.fixture
def operating_loop_scope_env(real_company_service: Any) -> dict[str, Any]:
    client = httpx.Client(base_url=real_company_service.base_url, timeout=20.0)
    registration = client.post(
        "/identity/_e2e/session",
        json={
            "email": f"operating-loop-scope-{time.time_ns()}@example.com",
            "displayName": "Operating Loop Founder",
        },
    )
    assert registration.status_code == 200, registration.text
    session = registration.json()
    workspace_id = str(session["workspaceId"])
    headers = {
        "Authorization": f"Bearer {session['accessToken']}",
        "X-Workspace-Id": workspace_id,
    }

    project_a = _create_project(client, headers, "Operating Loop Scope A")
    project_b = _create_project(client, headers, "Operating Loop Scope B")

    return {
        "client": client,
        "headers": headers,
        "workspace_id": workspace_id,
        "project_a": project_a,
        "project_b": project_b,
        "a": _seed_project_loop(client, headers, project_a, "a"),
        "b": _seed_project_loop(client, headers, project_b, "b"),
    }


def test_operating_loop_is_project_scoped_and_weekly_cas_has_one_visible_advance(
    operating_loop_scope_env: dict[str, Any],
) -> None:
    env = operating_loop_scope_env
    client: httpx.Client = env["client"]
    headers: dict[str, str] = env["headers"]
    project_a = env["project_a"]
    project_b = env["project_b"]
    a = env["a"]
    b = env["b"]

    loop_a = client.get(f"/operations/projects/{project_a}/operating-loop", headers=headers)
    assert loop_a.status_code == 200, loop_a.text
    loop_a_body = loop_a.json()
    assert str(loop_a_body["project"]["id"]) == project_a
    assert [str(task["id"]) for task in loop_a_body["tasks"]] == [a["task_id"]]
    assert b["task_id"] not in str(loop_a_body)
    assert b["task_title"] not in str(loop_a_body)

    # A URL containing B's task/cycle must not turn that B record into a
    # mutation.  Re-read B below to prove the current state was preserved.
    foreign_task = client.patch(
        f"/operations/projects/{project_a}/operating-loop/tasks/{b['task_id']}/status",
        json={"status": "done"},
        headers=headers,
    )
    assert foreign_task.status_code in (403, 404), foreign_task.text

    foreign_cycle = client.patch(
        f"/operations/projects/{project_a}/operating-loop/cycles/{b['cycle_id']}/week",
        json={"expectedCurrentWeek": 1, "reflection": "must never be written"},
        headers=headers,
    )
    assert foreign_cycle.status_code in (403, 404), foreign_cycle.text

    loop_b = client.get(f"/operations/projects/{project_b}/operating-loop", headers=headers)
    assert loop_b.status_code == 200, loop_b.text
    loop_b_body = loop_b.json()
    assert str(loop_b_body["activeCycle"]["id"]) == b["cycle_id"]
    assert loop_b_body["activeCycle"]["currentWeek"] == 1
    assert next(task for task in loop_b_body["tasks"] if str(task["id"]) == b["task_id"])["status"] == "todo"

    # First CAS advance succeeds and returns the unique public advance-event
    # identity. Retrying the exact stale expected week must leave public state
    # at week 2.  The current HTTP API has no cycle-event-list endpoint, so it
    # cannot honestly assert the hidden table row count without using DB access.
    advanced = client.patch(
        f"/operations/projects/{project_a}/operating-loop/cycles/{a['cycle_id']}/week",
        json={"expectedCurrentWeek": 1, "reflection": "week one complete"},
        headers=headers,
    )
    assert advanced.status_code == 200, advanced.text
    assert advanced.json()["event"]["id"]
    assert advanced.json()["event"]["expectedCurrentWeek"] == 1

    stale_advance = client.patch(
        f"/operations/projects/{project_a}/operating-loop/cycles/{a['cycle_id']}/week",
        json={"expectedCurrentWeek": 1, "reflection": "must not duplicate"},
        headers=headers,
    )
    assert stale_advance.status_code in (400, 409, 412), stale_advance.text

    loop_a_after = client.get(f"/operations/projects/{project_a}/operating-loop", headers=headers)
    assert loop_a_after.status_code == 200, loop_a_after.text
    assert loop_a_after.json()["activeCycle"]["currentWeek"] == 2


def test_workspace_cfo_without_project_deployment_cannot_frame_deliberation(
    operating_loop_scope_env: dict[str, Any],
) -> None:
    env = operating_loop_scope_env
    client: httpx.Client = env["client"]
    headers: dict[str, str] = env["headers"]
    workspace_id = env["workspace_id"]
    project_a = env["project_a"]

    # The legacy profile is only an availability prerequisite for the Office.
    # It is not a V2 project-agent deployment, so the later frame must fail.
    finance_profile = client.post(
        f"/operations/projects/{project_a}/startup-team/finance/activate",
        json={"expectedVersion": 1},
        headers=headers,
    )
    assert finance_profile.status_code == 200, finance_profile.text

    activate_cfo = client.post(
        f"/operations/workspaces/{workspace_id}/executive-roles/cfo/activate",
        json={"expectedVersion": 1},
        headers=headers,
    )
    assert activate_cfo.status_code == 200, activate_cfo.text
    assert activate_cfo.json()["state"] == "ACTIVE"

    draft = client.post(
        f"/operations/projects/{project_a}/deliberations/draft",
        json={"title": "CFO without a Project deployment must not advise"},
        headers=headers,
    )
    assert draft.status_code == 200, draft.text

    frame = client.post(
        f"/operations/projects/{project_a}/deliberations/{draft.json()['id']}/frame",
        json={
            "question": "Can the office bypass the Project deployment gate?",
            "roleKeys": ["cfo"],
            "expectedVersion": 1,
        },
        headers=headers,
    )
    assert frame.status_code in (400, 409, 412), frame.text
    assert "EXECUTIVE_ROLE_PROJECT_DEPLOYMENT_INACTIVE" in frame.text
