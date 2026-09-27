"""Schedule proxy routes for COSA Agent Platform."""

from __future__ import annotations

from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from apps.cosa.api.project_context import verify_project_context
from apps.cosa.api.schemas import CreateScheduleRequest, ScheduleListResponse, ScheduleResponse
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.auth.jwt import MissingPlatformIdentityError
from apps.cosa.config.planes import resolve_platform_control_plane_url

__all__ = ["create_schedule_router"]

router = APIRouter(prefix="/agent", tags=["schedules"])


def _get_plane(request: Request):
    """Lấy `CosaAgentPlane` từ `app.state.plane` — cùng pattern với
    `conversation_routes.py`. Fail-closed nếu app chưa gắn plane (composition
    root thiếu sót), thay vì crash mơ hồ ở tầng dưới."""
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError("CosaAgentPlane chưa sẵn sàng — app.state.plane rỗng.")
    return plane


def _control_plane_bearer(identity: AuthenticatedIdentity) -> str:
    """B5 fix — trước đây forward nguyên Authorization header của client gốc
    sang services/cosa, hoặc fallback `mint_delegation()` (re-sign đúng shape
    token gốc, không mang workspace/role) khi thiếu header. Cả 2 đường đều
    fail ở `verifyWorkspaceMembership` phía services/cosa (forward tiếp sang
    services/company, chỉ hiểu local-session token — khác secret với platform
    token). Giờ LUÔN mint control-plane delegation có cấu trúc (services/cosa
    verify trực tiếp, không round-trip company) — không còn forward header
    gốc nữa.
    """
    try:
        return f"Bearer {identity.mint_control_plane_delegation()}"
    except MissingPlatformIdentityError as exc:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản chưa liên kết với platform identity — không thể dùng schedules qua control-plane",
        ) from exc


class ScheduleStateRequest(BaseModel):
    state: Literal["enabled", "paused", "archived"]


def _schedule_response(d: dict[str, Any]) -> ScheduleResponse:
    return ScheduleResponse(
        id=d["id"],
        workspace_id=d["organizationId"],
        created_by=d["createdBy"],
        schedule_kind=d["scheduleKind"],
        timezone=d["timezone"],
        prompt_template=d["promptTemplate"],
        agent_profile=d["agentProfile"],
        state=d["state"],
        next_run_at=d.get("nextRunAt"),
        last_run_at=d.get("lastRunAt"),
        created_at=d["createdAt"],
        project_id=d.get("projectId"),
        is_legacy_unscoped=d.get("isLegacyUnscoped", False),
        hour=d.get("hour"),
        minute=d.get("minute"),
        weekdays=d.get("weekdays") if isinstance(d.get("weekdays"), list) else None,
    )


# 13. Schedules Proxy Routes (Task 4)
@router.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(
    request: Request,
    body: CreateScheduleRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    verified_project = await verify_project_context(plane, identity, body.project_id)

    control_plane_url = resolve_platform_control_plane_url()
    token = _control_plane_bearer(identity)
    # `runAt`/`hour`/`minute` là optional (`number`/`string`, không phải
    # `number | null`) phía interface Encore.ts (`CreateScheduleParams`) —
    # decoder JSON của Encore chấp nhận field VẮNG MẶT cho optional, nhưng từ
    # chối literal `null` ("invalid type: Option value, expected a number").
    # Trước đây route này luôn gửi cả 3 field kể cả khi `None` -> mọi lần tạo
    # schedule `one_time` (không có hour/minute) hay `daily`/`weekdays`
    # (không có run_at) đều 400 ở control-plane — bug có thật, phát hiện khi
    # viết E2E S10 (schedule-project-scope), không liên quan trực tiếp tới
    # project scoping nhưng chặn hoàn toàn route tạo schedule qua proxy.
    payload: dict[str, Any] = {
        "organizationId": identity.workspace_id,
        "projectId": verified_project.project_id,
        "scheduleKind": body.schedule_kind,
        "timezone": body.timezone,
        "promptTemplate": body.prompt_template,
        "agentProfile": body.agent_profile,
        "connectorGrantIds": body.connector_grant_ids,
    }
    if body.run_at is not None:
        payload["runAt"] = body.run_at.isoformat()
    if body.hour is not None:
        payload["hour"] = body.hour
    if body.minute is not None:
        payload["minute"] = body.minute
    if body.weekdays is not None:
        payload["weekdays"] = body.weekdays

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/schedules",
            json=payload,
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return _schedule_response(resp.json())


@router.get("/schedules", response_model=ScheduleListResponse)
async def list_schedules(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = resolve_platform_control_plane_url()
    token = _control_plane_bearer(identity)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{control_plane_url}/cosa/schedules",
            params={
                "organizationId": identity.workspace_id,
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        items = [_schedule_response(d) for d in data.get("items", [])]
        return ScheduleListResponse(items=items, total=data.get("total", len(items)))


@router.post("/schedules/{schedule_id}/run-now")
async def run_schedule_now_endpoint(
    request: Request,
    schedule_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = resolve_platform_control_plane_url()
    token = _control_plane_bearer(identity)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/schedules/{schedule_id}/run-now",
            json={
                "organizationId": identity.workspace_id,
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


@router.post("/schedules/{schedule_id}/state", response_model=ScheduleResponse)
async def set_schedule_state(
    schedule_id: str,
    body: ScheduleStateRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    """Founder tạm dừng / tiếp tục / lưu trữ lịch (card vận hành ở hub). Organization
    luôn lấy từ danh tính, không nhận từ client."""
    control_plane_url = resolve_platform_control_plane_url()
    token = _control_plane_bearer(identity)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/schedules/{schedule_id}/state",
            json={"organizationId": identity.workspace_id, "state": body.state},
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return _schedule_response(resp.json())


@router.get("/schedules/{schedule_id}/executions")
async def list_schedule_executions(
    schedule_id: str,
    limit: int = Query(default=5, ge=1, le=20),
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> dict[str, Any]:
    """Các lần chạy gần nhất của một lịch (state, run, hội thoại, lỗi rút gọn)."""
    control_plane_url = resolve_platform_control_plane_url()
    token = _control_plane_bearer(identity)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{control_plane_url}/cosa/schedules/{schedule_id}/executions",
            params={"organizationId": identity.workspace_id, "limit": limit},
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        return {
            "items": [
                {
                    "id": item["id"],
                    "scheduled_for": item.get("scheduledFor"),
                    "state": item.get("state"),
                    "run_id": item.get("runId"),
                    "conversation_id": item.get("conversationId"),
                    "error": item.get("error"),
                    "updated_at": item.get("updatedAt"),
                }
                for item in data.get("items", [])
            ]
        }


def create_schedule_router() -> APIRouter:
    """Export router for app.py registration."""
    return router
