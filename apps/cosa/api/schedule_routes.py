"""Schedule proxy routes for COSA Agent Platform."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from apps.cosa.api.schemas import CreateScheduleRequest, ScheduleListResponse, ScheduleResponse
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.auth.jwt import MissingPlatformIdentityError
from apps.cosa.config.planes import resolve_platform_control_plane_url

__all__ = ["create_schedule_router"]

router = APIRouter(prefix="/agent", tags=["schedules"])


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
    control_plane_url = resolve_platform_control_plane_url()
    token = _control_plane_bearer(identity)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/schedules",
            json={
                "workspaceId": identity.workspace_id,
                "scheduleKind": body.schedule_kind,
                "timezone": body.timezone,
                "runAt": body.run_at.isoformat() if body.run_at else None,
                "hour": body.hour,
                "minute": body.minute,
                "weekdays": body.weekdays,
                "promptTemplate": body.prompt_template,
                "agentProfile": body.agent_profile,
                "connectorGrantIds": body.connector_grant_ids,
            },
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
