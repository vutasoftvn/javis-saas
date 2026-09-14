"""Schedule proxy routes for COSA Agent Platform."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

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
        "workspaceId": identity.workspace_id,
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
    if body.weekdays:
        payload["weekdays"] = body.weekdays

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/schedules",
            json=payload,
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        return ScheduleResponse(
            id=data["id"],
            workspace_id=data["workspaceId"],
            created_by=data["createdBy"],
            schedule_kind=data["scheduleKind"],
            timezone=data["timezone"],
            prompt_template=data["promptTemplate"],
            agent_profile=data["agentProfile"],
            state=data["state"],
            next_run_at=data.get("nextRunAt"),
            last_run_at=data.get("lastRunAt"),
            created_at=data["createdAt"],
        )


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
                "workspaceId": identity.workspace_id,
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        items = [
            ScheduleResponse(
                id=d["id"],
                workspace_id=d["workspaceId"],
                created_by=d["createdBy"],
                schedule_kind=d["scheduleKind"],
                timezone=d["timezone"],
                prompt_template=d["promptTemplate"],
                agent_profile=d["agentProfile"],
                state=d["state"],
                next_run_at=d.get("nextRunAt"),
                last_run_at=d.get("lastRunAt"),
                created_at=d["createdAt"],
            )
            for d in data.get("items", [])
        ]
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
                "workspaceId": identity.workspace_id,
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


def create_schedule_router() -> APIRouter:
    """Export router for app.py registration."""
    return router
