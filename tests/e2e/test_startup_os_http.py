"""E2E HTTP proof cho Startup OS (plan 2026-09-18 Phase 3–4) trên process Company thật.

Luồng Founder dùng từ Flutter: mở phiên onboarding, ghi chiều, chốt snapshot, đọc
độ tươi 7 chiều, tạo Goal, đọc cây Goal / Goal cần rà soát / dự án chờ triage.
Khoá các lỗi đã sửa:
- payload chiều dùng key Company không lưu bị từ chối 400 thay vì lưu null;
- context có id bigint trả JSON được (trước đây ném "Do not know how to serialize
  a BigInt") và snapshot chốt được;
- chiều chưa từng ghi nhận không bị báo "tươi".
"""

from __future__ import annotations

import time

import httpx

from tests.e2e.conftest import CompanyServiceHandle


def test_startup_os_founder_flow(real_company_service: CompanyServiceHandle) -> None:
    client = httpx.Client(base_url=real_company_service.base_url, timeout=20.0)
    registration = client.post(
        "/identity/_e2e/session",
        json={
            "email": f"startup-os-{time.time_ns()}@example.com",
            "displayName": "Startup OS Founder",
        },
    )
    assert registration.status_code == 200, registration.text
    session = registration.json()
    ws = str(session["workspaceId"])
    headers = {"Authorization": f"Bearer {session['accessToken']}", "X-Workspace-Id": ws}

    cadence = client.get(
        "/operations/onboard/cadence/status", params={"workspaceId": ws}, headers=headers
    )
    assert cadence.status_code == 200, cadence.text
    cadences = cadence.json()["cadences"]
    assert len(cadences) == 7
    assert all(c["neverReviewed"] and c["urgency"] == "critical" for c in cadences)

    started = client.post(
        "/operations/onboard/sessions",
        json={"workspaceId": ws, "sessionType": "partial_update"},
        headers=headers,
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["sessionId"]

    legacy = client.post(
        "/operations/onboard/dimensions/stage_scale",
        json={"workspaceId": ws, "sessionId": session_id, "data": {"arr": 150000}},
        headers=headers,
    )
    assert legacy.status_code == 400, legacy.text

    saved = client.post(
        "/operations/onboard/dimensions/stage_scale",
        json={
            "workspaceId": ws,
            "sessionId": session_id,
            "data": {"stage": "pre_pmf", "headcountFt": 4, "revenueArr": 150000},
        },
        headers=headers,
    )
    assert saved.status_code == 200, saved.text

    context = client.get(
        "/operations/onboard/context/current", params={"workspaceId": ws}, headers=headers
    )
    assert context.status_code == 200, context.text
    stage = context.json()["fullContext"]["stage_scale"]
    assert stage["stage"] == "pre_pmf"
    assert isinstance(stage["id"], str)

    snapshot = client.post(
        "/operations/onboard/snapshots",
        json={"workspaceId": ws, "sessionId": session_id, "changedDimensions": ["stage_scale"]},
        headers=headers,
    )
    assert snapshot.status_code == 200, snapshot.text

    refreshed = client.get(
        "/operations/onboard/cadence/status", params={"workspaceId": ws}, headers=headers
    ).json()["cadences"]
    by_dim = {c["dimension"]: c for c in refreshed}
    assert by_dim["stage_scale"]["neverReviewed"] is False
    assert by_dim["challenges"]["neverReviewed"] is True

    goal = client.post(
        "/operations/goals",
        json={"workspaceId": ws, "title": "100 khách trả tiền", "goalType": "tactical"},
        headers=headers,
    )
    assert goal.status_code == 200, goal.text
    warnings = goal.json()["cadenceWarnings"]
    assert [w["dimension"] for w in warnings] == ["challenges"]

    tree = client.get("/operations/goals/tree", params={"workspaceId": ws}, headers=headers)
    assert tree.status_code == 200, tree.text
    assert [n["title"] for n in tree.json()["tree"]] == ["100 khách trả tiền"]

    review = client.get(
        "/operations/goals/needing-review", params={"workspaceId": ws}, headers=headers
    )
    assert review.status_code == 200, review.text
    assert review.json()["goals"] == []

    pending = client.get(
        "/operations/projects/pending-review", params={"workspaceId": ws}, headers=headers
    )
    assert pending.status_code == 200, pending.text
    assert isinstance(pending.json()["projects"], list)

    unauthenticated = client.get("/operations/goals/tree", params={"workspaceId": ws})
    assert unauthenticated.status_code == 401, unauthenticated.text
