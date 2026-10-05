"""E2E HTTP proof cho luồng Goals/OKR hợp nhất (project A0) trên process Company thật.

Goal -> Objective cấp công ty (bắt buộc goalId) -> Objective cấp dự án (con của
objective công ty) -> Key Result + check-in -> cây Goal tổng hợp -> triage dự án.
"""

from __future__ import annotations

import time

import httpx

from tests.e2e.conftest import CompanyServiceHandle


def test_unified_okr_goal_to_project_flow(real_company_service: CompanyServiceHandle) -> None:
    client = httpx.Client(base_url=real_company_service.base_url, timeout=20.0)
    registration = client.post(
        "/identity/_e2e/session",
        json={
            "email": f"okr-unification-{time.time_ns()}@example.com",
            "displayName": "OKR Unification Founder",
        },
    )
    assert registration.status_code == 200, registration.text
    session = registration.json()
    ws = str(session["workspaceId"])
    headers = {"Authorization": f"Bearer {session['accessToken']}", "X-Workspace-Id": ws}

    project = client.post(
        "/operations/projects", json={"title": "OKR Unification Project"}, headers=headers
    )
    assert project.status_code == 200, project.text
    project_id = str(project.json()["id"])

    # 1. Goal chiến lược
    goal = client.post(
        "/operations/goals",
        json={"workspaceId": ws, "title": "Mục tiêu chiến lược", "goalType": "strategic"},
        headers=headers,
    )
    assert goal.status_code == 200, goal.text
    goal_id = str(goal.json()["id"] if "id" in goal.json() else goal.json()["goalId"])

    # 2. Objective cấp công ty: bắt buộc goalId
    company = client.post(
        "/operations/objectives",
        json={"workspaceId": ws, "scope": "company", "goalId": goal_id, "title": "Company O"},
        headers=headers,
    )
    assert company.status_code == 200, company.text
    company_obj = company.json()
    assert company_obj["scope"] == "company"
    assert company_obj["goalId"] == goal_id
    assert company_obj["projectId"] is None
    company_id = str(company_obj["id"])

    no_goal = client.post(
        "/operations/objectives",
        json={"workspaceId": ws, "scope": "company", "title": "Company O không goal"},
        headers=headers,
    )
    assert no_goal.status_code == 400, no_goal.text
    assert no_goal.json()["code"] == "invalid_argument"

    # 3. Objective cấp dự án, con của objective công ty
    proj = client.post(
        "/operations/objectives",
        json={
            "workspaceId": ws,
            "projectId": project_id,
            "parentObjectiveId": company_id,
            "title": "Project O",
        },
        headers=headers,
    )
    assert proj.status_code == 200, proj.text
    proj_obj = proj.json()
    assert proj_obj["scope"] == "project"
    assert proj_obj["parentObjectiveId"] == company_id
    proj_id = str(proj_obj["id"])

    # 4. Key Result + check-in đạt mục tiêu
    kr = client.post(
        f"/operations/objectives/{proj_id}/key-results",
        json={"title": "KR 1", "targetValue": 10, "baselineValue": 0},
        headers=headers,
    )
    assert kr.status_code == 200, kr.text
    kr_id = str(kr.json()["id"])
    checkin = client.post(
        f"/operations/key-results/{kr_id}/checkin", json={"value": 10}, headers=headers
    )
    assert checkin.status_code == 200, checkin.text

    # 5. Cây Goal tổng hợp objective + KR
    tree = client.get("/operations/goals/tree", params={"workspaceId": ws}, headers=headers)
    assert tree.status_code == 200, tree.text
    node = next(n for n in tree.json()["tree"] if str(n["id"]) == goal_id)
    assert node["objectiveCount"] == 2
    assert node["krTotal"] == 1
    assert node["krAchieved"] == 1

    # 6. Triage 'link' chỉ chấp nhận objective cấp công ty
    bad_link = client.post(
        "/operations/projects/triage",
        json={
            "workspaceId": ws,
            "projectId": project_id,
            "action": "link",
            "targetObjectiveId": proj_id,
        },
        headers=headers,
    )
    assert bad_link.status_code == 400, bad_link.text
    good_link = client.post(
        "/operations/projects/triage",
        json={
            "workspaceId": ws,
            "projectId": project_id,
            "action": "link",
            "targetObjectiveId": company_id,
        },
        headers=headers,
    )
    assert good_link.status_code == 200, good_link.text

    # 7. Danh sách objective có cả hai, kèm scope
    listing = client.get("/operations/objectives", headers=headers)
    assert listing.status_code == 200, listing.text
    by_id = {str(o["id"]): o for o in listing.json()["data"]}
    assert by_id[company_id]["scope"] == "company"
    assert by_id[proj_id]["scope"] == "project"
