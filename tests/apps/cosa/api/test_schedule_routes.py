"""Task 4 (2026-09-14 Schedule Project scope) — proxy `POST /agent/schedules`
(`apps/cosa/api/schedule_routes.py`) phải bắt buộc + verify `project_id` qua
`verify_project_context()` TRƯỚC khi forward sang `services/cosa`, cùng
nguyên tắc đã áp dụng cho conversation routes (xem
`tests/apps/cosa/api/test_conversation_project_context.py`)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.cosa.api.schedule_routes import create_schedule_router
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

WORKSPACE_A = "ws_a"
PROJECT_A = "proj_a"


def _make_app(plane) -> TestClient:
    app = FastAPI()
    app.state.plane = plane
    app.include_router(create_schedule_router())
    override_authenticated_identity(app, workspace_id=WORKSPACE_A)
    return TestClient(app)


def test_create_schedule_rejects_missing_project_id():
    plane = type("Plane", (), {"company_client": AsyncMock()})()
    client = _make_app(plane)

    resp = client.post(
        "/agent/schedules",
        json={
            "schedule_kind": "daily",
            "prompt_template": "daily report",
            # project_id intentionally omitted
        },
    )

    assert resp.status_code == 422


def _plane_with_verified_project(project_id: str = PROJECT_A):
    company_client = AsyncMock()
    company_client.get.return_value = {"id": project_id, "title": "Test Project"}
    return type("Plane", (), {"company_client": company_client})()


def test_create_schedule_omits_null_optional_fields_from_outbound_payload():
    """Finding 3.1 (2026-09-14 whole-branch review): E2E S10 tìm ra bug thật —
    route này từng gửi `runAt`/`hour`/`minute`/`weekdays` là JSON `null` khi
    client không set, bị control-plane Encore.ts từ chối
    ("invalid type: Option value, expected a number") vì field optional phía
    Encore chấp nhận field VẮNG MẶT chứ không chấp nhận `null`. Đã vá trong
    code (payload chỉ thêm key khi giá trị not None) — test này khoá lại hành
    vi bằng cách mock outbound `httpx.AsyncClient.post` và kiểm tra `json=`
    kwarg gửi đi.
    """
    plane = _plane_with_verified_project()
    client = _make_app(plane)

    control_plane_reply = httpx.Response(
        200,
        json={
            "id": "sched_1",
            "workspaceId": WORKSPACE_A,
            "createdBy": "user:test_user",
            "scheduleKind": "one_time",
            "timezone": "Asia/Ho_Chi_Minh",
            "promptTemplate": "one-off report",
            "agentProfile": "operations",
            "state": "enabled",
            "createdAt": "2026-09-14T00:00:00Z",
            "projectId": PROJECT_A,
            "isLegacyUnscoped": False,
        },
    )

    mock_post = AsyncMock(return_value=control_plane_reply)
    with patch("httpx.AsyncClient.post", new=mock_post):
        resp = client.post(
            "/agent/schedules",
            json={
                "schedule_kind": "one_time",
                "prompt_template": "one-off report",
                "project_id": PROJECT_A,
                "run_at": "2026-09-20T09:00:00Z",
                # hour/minute intentionally omitted -> should stay unset,
                # not sent as JSON null.
            },
        )

    assert resp.status_code == 200
    sent_json = mock_post.call_args.kwargs["json"]
    assert "hour" not in sent_json
    assert "minute" not in sent_json
    assert "runAt" in sent_json  # explicitly set on the request -> forwarded

    body = resp.json()
    assert body["project_id"] == PROJECT_A
    assert body["is_legacy_unscoped"] is False


def test_create_schedule_response_maps_project_scope_fields():
    """Finding 4 (2026-09-14 whole-branch review): `project_id`/
    `is_legacy_unscoped` được ghi bắt buộc lúc tạo schedule nhưng trước đây
    chưa bao giờ trả về qua `ScheduleResponse` — client không thấy schedule
    đang scope vào project nào."""
    plane = _plane_with_verified_project()
    client = _make_app(plane)

    control_plane_reply = httpx.Response(
        200,
        json={
            "id": "sched_2",
            "workspaceId": WORKSPACE_A,
            "createdBy": "user:test_user",
            "scheduleKind": "daily",
            "timezone": "Asia/Ho_Chi_Minh",
            "hour": 9,
            "minute": 0,
            "promptTemplate": "daily report",
            "agentProfile": "operations",
            "state": "enabled",
            "createdAt": "2026-09-14T00:00:00Z",
            "projectId": PROJECT_A,
            "isLegacyUnscoped": True,
        },
    )

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=control_plane_reply)):
        resp = client.post(
            "/agent/schedules",
            json={
                "schedule_kind": "daily",
                "prompt_template": "daily report",
                "project_id": PROJECT_A,
                "hour": 9,
                "minute": 0,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == PROJECT_A
    assert body["is_legacy_unscoped"] is True


def test_list_schedules_response_maps_project_scope_fields():
    plane = _plane_with_verified_project()
    client = _make_app(plane)

    control_plane_reply = httpx.Response(
        200,
        json={
            "items": [
                {
                    "id": "sched_3",
                    "workspaceId": WORKSPACE_A,
                    "createdBy": "user:test_user",
                    "scheduleKind": "daily",
                    "timezone": "Asia/Ho_Chi_Minh",
                    "promptTemplate": "daily report",
                    "agentProfile": "operations",
                    "state": "enabled",
                    "createdAt": "2026-09-14T00:00:00Z",
                    "projectId": PROJECT_A,
                    "isLegacyUnscoped": False,
                }
            ],
            "total": 1,
        },
    )

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=control_plane_reply)):
        resp = client.get("/agent/schedules")

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["project_id"] == PROJECT_A
    assert body["items"][0]["is_legacy_unscoped"] is False


def test_create_schedule_rejects_project_not_in_workspace():
    from apps.cosa.capabilities.client import CompanyServiceError

    company_client = AsyncMock()
    company_client.get.side_effect = CompanyServiceError("not found")
    plane = type("Plane", (), {"company_client": company_client})()
    client = _make_app(plane)

    resp = client.post(
        "/agent/schedules",
        json={
            "schedule_kind": "daily",
            "prompt_template": "daily report",
            "project_id": "proj_other_workspace",
        },
    )

    assert resp.status_code == 404
