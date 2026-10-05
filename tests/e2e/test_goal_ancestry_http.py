"""E2E HTTP proof cho goal ancestry + done criteria (project A) trên process Company thật.

Goal -> Objective công ty -> link project -> execution plan có `doneCriteria`
(400 khi tiêu chí sai) -> GET round trip -> accept.

Phần claim (`GET /operations/tasks/agent-claimable`) KHÔNG nằm ở đây: endpoint đòi
cosa company-delegation JWT (COSA_COMPANY_DELEGATION_SECRET) + task giao cho agent
AI; không có đường e2e hợp lệ mà không thêm backdoor. Phần đó được phủ bởi
services/company/operations/tests/agent-claimable.test.ts.
"""

from __future__ import annotations

import time

import httpx

from tests.e2e.conftest import CompanyServiceHandle


def _item(title: str, **extra: object) -> dict[str, object]:
    return {
        "title": title,
        "decisionReason": "Cần cho mục tiêu tuần",
        "evidenceRefs": [],
        "suggestedDomain": None,
        "expectedCapability": None,
        "capabilityRisk": "LOW",
        "tenantPolicyDecision": None,
        "dependsOnTitles": [],
        **extra,
    }


def test_execution_plan_done_criteria_round_trip(
    real_company_service: CompanyServiceHandle,
) -> None:
    client = httpx.Client(base_url=real_company_service.base_url, timeout=20.0)
    registration = client.post(
        "/identity/_e2e/session",
        json={
            "email": f"goal-ancestry-{time.time_ns()}@example.com",
            "displayName": "Goal Ancestry Founder",
        },
    )
    assert registration.status_code == 200, registration.text
    session = registration.json()
    ws = str(session["workspaceId"])
    headers = {"Authorization": f"Bearer {session['accessToken']}", "X-Workspace-Id": ws}

    project = client.post(
        "/operations/projects", json={"title": "Goal Ancestry Project"}, headers=headers
    )
    assert project.status_code == 200, project.text
    project_id = str(project.json()["id"])

    goal = client.post(
        "/operations/goals",
        json={"workspaceId": ws, "title": "Mục tiêu chiến lược", "goalType": "strategic"},
        headers=headers,
    )
    assert goal.status_code == 200, goal.text
    goal_id = str(goal.json().get("id") or goal.json()["goalId"])

    company = client.post(
        "/operations/objectives",
        json={"workspaceId": ws, "scope": "company", "goalId": goal_id, "title": "Company O"},
        headers=headers,
    )
    assert company.status_code == 200, company.text
    link = client.post(
        "/operations/projects/triage",
        json={
            "workspaceId": ws,
            "projectId": project_id,
            "action": "link",
            "targetObjectiveId": str(company.json()["id"]),
        },
        headers=headers,
    )
    assert link.status_code == 200, link.text

    criteria = {
        "version": 1,
        "criteria": [
            {
                "id": "report-ready",
                "description": "Báo cáo đã được đính kèm",
                "required": True,
                "check": "deterministic",
                "predicate": {"kind": "artifact_exists", "args": {"kind": "report"}},
            }
        ],
    }
    cycle = client.post(
        "/operations/cycles",
        json={
            "workspaceId": ws,
            "projectId": project_id,
            "displayName": "Goal Ancestry Cycle",
            "startLocalDate": "2026-10-05",
        },
        headers=headers,
    )
    assert cycle.status_code == 200, cycle.text
    weekly = client.post(
        "/operations/weekly-plans",
        json={
            "workspaceId": ws,
            "cycleId": str(cycle.json()["id"]),
            "weekNo": 1,
            "focus": "Ra mắt báo cáo",
        },
        headers=headers,
    )
    assert weekly.status_code == 200, weekly.text

    created = client.post(
        "/operations/execution-plans",
        json={
            "projectId": project_id,
            "weeklyPlanId": str(weekly.json()["id"]),
            "goalText": "Ra mắt báo cáo tuần",
            "items": [_item("Viết báo cáo", doneCriteria=criteria)],
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    plan = created.json()
    assert plan["items"][0]["doneCriteria"]["criteria"][0]["id"] == "report-ready"

    bad = client.post(
        "/operations/execution-plans",
        json={
            "projectId": project_id,
            "weeklyPlanId": str(weekly.json()["id"]),
            "goalText": "Kế hoạch tiêu chí sai",
            "items": [_item("Việc sai", doneCriteria={"version": 1, "criteria": [{"id": "BAD ID"}]})],
        },
        headers=headers,
    )
    assert bad.status_code == 400, bad.text
    assert bad.json()["code"] == "invalid_argument"
    assert "invalid criterion id" in bad.json()["message"]

    fetched = client.get(f"/operations/execution-plans/{plan['id']}", headers=headers)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["items"][0]["doneCriteria"] == plan["items"][0]["doneCriteria"]

    accepted = client.post(f"/operations/execution-plans/{plan['id']}/accept", json={}, headers=headers)
    assert accepted.status_code == 200, accepted.text
