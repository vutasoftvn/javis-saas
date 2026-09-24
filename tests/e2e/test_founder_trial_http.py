"""E2E HTTP cho Strategy assumptions (kế thừa bề mặt Founder Trial đã gỡ ở clean-slate 2026-09-10):
tạo, xếp hạng theo Project và cô lập workspace, không mock transport."""

from __future__ import annotations

import time

import httpx


def _session(client: httpx.Client, label: str) -> dict[str, str]:
    res = client.post(
        "/identity/_e2e/session",
        json={
            "email": f"assumptions-{label}-{time.time_ns()}@example.com",
            "displayName": f"Assumptions {label}",
        },
    )
    assert res.status_code == 200, res.text
    d = res.json()
    return {
        "Authorization": f"Bearer {d['accessToken']}",
        "X-Workspace-Id": str(d["workspaceId"]),
    }


def test_strategy_assumptions_are_ranked_per_project_and_workspace_isolated(real_company_service):
    client = httpx.Client(base_url=real_company_service.base_url, timeout=15.0)
    headers_a = _session(client, "a")
    headers_b = _session(client, "b")

    proj = client.post("/operations/projects", headers=headers_a, json={"title": "Assumptions E2E"})
    assert proj.status_code == 200, proj.text
    project_id = str(proj.json()["id"])

    def create(statement: str, importance: int, uncertainty: int) -> str:
        res = client.post(
            "/operations/strategy/assumptions",
            headers=headers_a,
            json={
                "projectId": project_id,
                "statement": statement,
                "importance": importance,
                "uncertainty": uncertainty,
            },
        )
        assert res.status_code == 200, res.text
        return str(res.json()["id"])

    low = create("Khách chấp nhận giá thấp", 3, 2)
    high = create("Khách gặp đau này hằng tuần", 9, 8)

    # Xếp hạng: giả định quan trọng + bất định cao nhất đứng đầu.
    ranked = client.get(
        f"/operations/strategy/projects/{project_id}/ranked-assumptions", headers=headers_a
    )
    assert ranked.status_code == 200, ranked.text
    body = ranked.json()
    items = body.get("items") or body.get("data") or body
    assert [str(i["id"]) for i in items][:2] == [high, low]

    # Workspace khác không đọc/sửa/xoá được và không thấy trong list/ranking.
    assert client.get(f"/operations/strategy/assumptions/{high}", headers=headers_b).status_code in (403, 404)
    assert client.patch(
        f"/operations/strategy/assumptions/{high}", headers=headers_b, json={"statement": "hijack"}
    ).status_code in (403, 404)
    assert client.delete(f"/operations/strategy/assumptions/{high}", headers=headers_b).status_code in (403, 404)
    listed_b = client.get("/operations/strategy/assumptions", headers=headers_b)
    assert listed_b.status_code == 200
    assert high not in {str(i["id"]) for i in (listed_b.json().get("items") or [])}
    cross_rank = client.get(
        f"/operations/strategy/projects/{project_id}/ranked-assumptions", headers=headers_b
    )
    assert cross_rank.status_code in (403, 404), cross_rank.text

    # Chủ workspace vẫn xoá được.
    assert client.delete(f"/operations/strategy/assumptions/{low}", headers=headers_a).status_code == 200
    assert client.get(f"/operations/strategy/assumptions/{low}", headers=headers_a).status_code == 404
