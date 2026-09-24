"""E2E HTTP cho Strategy interviews (bề mặt Startup Core hiện hành): vòng đời, evidence và cô lập
workspace, không mock transport. Canvas/workspace-runtime đã bị gỡ ở clean-slate 2026-09-10."""

from __future__ import annotations

import time

import httpx


def _session(client: httpx.Client, label: str) -> dict:
    reg = client.post(
        "/identity/_e2e/session",
        json={"email": f"{label}-{time.time_ns()}@example.com", "displayName": label},
    )
    assert reg.status_code == 200, f"Identity test session creation failed: {reg.text}"
    data = reg.json()
    return {
        "Authorization": f"Bearer {data['accessToken']}",
        "X-Workspace-Id": str(data["workspaceId"]),
    }


def test_strategy_interview_lifecycle_and_isolation(real_company_service):
    client = httpx.Client(base_url=real_company_service.base_url, timeout=15.0)
    headers_a = _session(client, "strategy-a")
    project = client.post("/operations/projects", json={"title": "Strategy Project"}, headers=headers_a)
    assert project.status_code == 200, project.text
    project_id = str(project.json()["id"])

    assert client.get("/operations/strategy/interviews", headers=headers_a).json()["items"] == []

    created = client.post(
        "/operations/strategy/interviews",
        json={"projectId": project_id, "notes": "Khách hàng đau ở bước đối soát"},
        headers=headers_a,
    )
    assert created.status_code == 200, created.text
    interview = created.json()
    assert interview["projectId"] == project_id
    interview_id = interview["id"]

    updated = client.patch(
        f"/operations/strategy/interviews/{interview_id}",
        json={"notes": "Khách hàng đau ở bước đối soát và xuất hoá đơn"},
        headers=headers_a,
    )
    assert updated.status_code == 200, updated.text
    assert "xuất hoá đơn" in updated.json()["notes"]

    evidence = client.post(
        f"/operations/strategy/interviews/{interview_id}/submit-evidence",
        json={"claim": "Đối soát thủ công tốn 3 giờ/tuần", "supportsOrRefutes": "supports", "factOrInference": "fact"},
        headers=headers_a,
    )
    assert evidence.status_code == 200, evidence.text

    fetched = client.get(f"/operations/strategy/interviews/{interview_id}", headers=headers_a)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == interview_id

    # Workspace B không đọc/sửa/xoá được interview của workspace A.
    headers_b = _session(client, "strategy-b")
    assert client.get(
        f"/operations/strategy/interviews/{interview_id}", headers=headers_b
    ).status_code in {403, 404}
    assert client.patch(
        f"/operations/strategy/interviews/{interview_id}", json={"notes": "hijack"}, headers=headers_b
    ).status_code in {403, 404}
    assert client.delete(
        f"/operations/strategy/interviews/{interview_id}", headers=headers_b
    ).status_code in {403, 404}
    assert client.get(f"/operations/strategy/interviews/{interview_id}", headers=headers_a).status_code == 200

    deleted = client.delete(f"/operations/strategy/interviews/{interview_id}", headers=headers_a)
    assert deleted.status_code == 200, deleted.text
    assert client.get(f"/operations/strategy/interviews/{interview_id}", headers=headers_a).status_code == 404
