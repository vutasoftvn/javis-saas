"""E2E HTTP smoke test across MVP sub-domains trên bề mặt Startup Core hiện hành.

Bề mặt canvas/workspace-runtime đã bị gỡ khi clean-slate (2026-09-10); smoke này kiểm các
domain còn lại: identity, strategy (interviews), marketing, finance, cùng cô lập workspace.
"""

from __future__ import annotations

import time

import httpx


def _session(client: httpx.Client, label: str) -> tuple[dict, str]:
    reg = client.post(
        "/identity/_e2e/session",
        json={"email": f"{label}-{time.time_ns()}@example.com", "displayName": label},
    )
    assert reg.status_code == 200, f"Identity test session creation failed: {reg.text}"
    data = reg.json()
    ws_id = str(data["workspaceId"])
    return {"Authorization": f"Bearer {data['accessToken']}", "X-Workspace-Id": ws_id}, ws_id


def test_full_mvp_release_smoke(real_company_service):
    client = httpx.Client(base_url=real_company_service.base_url, timeout=15.0)

    # 1. Identity + Project
    headers, _ = _session(client, "smoke-a")
    project = client.post("/operations/projects", json={"title": "Smoke Project"}, headers=headers)
    assert project.status_code == 200, project.text
    project_id = str(project.json()["id"])

    # 2. Strategy: interview gắn Project, đọc lại qua list
    created = client.post(
        "/operations/strategy/interviews",
        json={"projectId": project_id, "notes": "Khách nói đau ở đối soát"},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    interview_id = created.json()["id"]
    listed = client.get("/operations/strategy/interviews", headers=headers)
    assert listed.status_code == 200
    assert interview_id in {i["id"] for i in listed.json()["items"]}

    # 3. Marketing: nguồn dữ liệu trung thực (company_db) + campaign list theo Project
    objectives = client.get("/commercial/marketing/objectives", headers=headers)
    assert objectives.status_code == 200
    assert objectives.json()["meta"]["sources"][0]["kind"] == "company_db"
    campaigns = client.get(
        "/commercial/marketing/campaigns", params={"projectId": project_id}, headers=headers
    )
    assert campaigns.status_code == 200, campaigns.text

    # 4. Finance: budget summary theo Project
    budget = client.get(
        "/finance/budget-summary", params={"projectId": project_id}, headers=headers
    )
    assert budget.status_code == 200, budget.text

    # 5. Cô lập workspace: workspace khác không đọc được interview của workspace A.
    headers_b, _ = _session(client, "smoke-b")
    cross = client.get(f"/operations/strategy/interviews/{interview_id}", headers=headers_b)
    assert cross.status_code in {403, 404}
    assert interview_id not in {
        i["id"] for i in client.get("/operations/strategy/interviews", headers=headers_b).json()["items"]
    }
