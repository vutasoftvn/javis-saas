"""Task 4 (2026-09-14 Schedule Project scope) — proxy `POST /agent/schedules`
(`apps/cosa/api/schedule_routes.py`) phải bắt buộc + verify `project_id` qua
`verify_project_context()` TRƯỚC khi forward sang `services/cosa`, cùng
nguyên tắc đã áp dụng cho conversation routes (xem
`tests/apps/cosa/api/test_conversation_project_context.py`)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.cosa.api.schedule_routes import create_schedule_router
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

WORKSPACE_A = "ws_a"


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
