"""Release loop của Project operating loop trên HTTP thật (kế thừa loop Founder Trial đã gỡ):
project -> OKR/initiative/cycle/week/commitment/task -> hoàn tất task -> advance week (CAS) ->
interview evidence -> cô lập workspace. Không mock transport."""

from __future__ import annotations

import time

import httpx

from tests.e2e.test_project_operating_loop_scope_and_authority import (
    _create_project,
    _seed_project_loop,
)


def _session(client: httpx.Client, label: str) -> dict[str, str]:
    res = client.post(
        "/identity/_e2e/session",
        json={
            "email": f"release-loop-{label}-{time.time_ns()}@example.com",
            "displayName": f"Release Loop {label}",
        },
    )
    assert res.status_code == 200, res.text
    d = res.json()
    return {
        "Authorization": f"Bearer {d['accessToken']}",
        "X-Workspace-Id": str(d["workspaceId"]),
    }


def test_project_operating_loop_release_loop(real_company_service):
    client = httpx.Client(base_url=real_company_service.base_url, timeout=20.0)
    headers = _session(client, "a")
    project_id = _create_project(client, headers, "Release Loop")
    loop = _seed_project_loop(client, headers, project_id, "release")

    # Loop đọc lại đúng dữ liệu đã seed.
    before = client.get(f"/operations/projects/{project_id}/operating-loop", headers=headers)
    assert before.status_code == 200, before.text
    assert before.json()["activeCycle"]["currentWeek"] == 1

    # Hoàn tất task rồi advance week bằng CAS; advance lặp với week cũ bị từ chối.
    done = client.patch(
        f"/operations/projects/{project_id}/operating-loop/tasks/{loop['task_id']}/status",
        json={"status": "done"},
        headers=headers,
    )
    assert done.status_code == 200, done.text
    advanced = client.patch(
        f"/operations/projects/{project_id}/operating-loop/cycles/{loop['cycle_id']}/week",
        json={"expectedCurrentWeek": 1, "reflection": "tuần 1 xong"},
        headers=headers,
    )
    assert advanced.status_code == 200, advanced.text
    stale = client.patch(
        f"/operations/projects/{project_id}/operating-loop/cycles/{loop['cycle_id']}/week",
        json={"expectedCurrentWeek": 1, "reflection": "không được nhân đôi"},
        headers=headers,
    )
    assert stale.status_code in (400, 409, 412), stale.text
    after = client.get(f"/operations/projects/{project_id}/operating-loop", headers=headers)
    assert after.json()["activeCycle"]["currentWeek"] == 2
    assert next(t for t in after.json()["tasks"] if str(t["id"]) == loop["task_id"])["status"] == "done"

    # Interview evidence gắn Project.
    interview = client.post(
        "/operations/strategy/interviews",
        json={"projectId": project_id, "notes": "Khách xác nhận đau hằng tuần"},
        headers=headers,
    )
    assert interview.status_code == 200, interview.text
    evidence = client.post(
        f"/operations/strategy/interviews/{interview.json()['id']}/submit-evidence",
        json={"claim": "Đau hằng tuần", "supportsOrRefutes": "supports", "factOrInference": "fact"},
        headers=headers,
    )
    assert evidence.status_code == 200, evidence.text

    # Workspace khác không đọc được loop và không sửa được task.
    other = _session(client, "b")
    assert client.get(
        f"/operations/projects/{project_id}/operating-loop", headers=other
    ).status_code in (403, 404)
    assert client.patch(
        f"/operations/projects/{project_id}/operating-loop/tasks/{loop['task_id']}/status",
        json={"status": "todo"},
        headers=other,
    ).status_code in (403, 404)
