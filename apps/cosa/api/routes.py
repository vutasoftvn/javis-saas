"""Run operations routes for COSA Agent Platform (minimal post-split)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from apps.cosa.api.event_stream import get_cosa_event_stream_manager
from apps.cosa.api.schemas import CancelRunResponse
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.composition.agent_plane import CosaAgentPlane

__all__ = ["create_cosa_router", "router"]

logger = logging.getLogger("cosa.api.routes")

router = APIRouter(prefix="/agent", tags=["agent-chat"])


def get_cosa_plane(request: Request) -> CosaAgentPlane:
    """Dependency injection từ `app.state.plane`."""
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError("CosaAgentPlane chưa sẵn sàng — app.state.plane rỗng.")
    return plane


# 6. POST /agent/runs/{run_id}/cancel
@router.post("/runs/{run_id}/cancel", response_model=CancelRunResponse)
async def cancel_run(
    request: Request,
    run_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane(request)
    stream_mgr = get_cosa_event_stream_manager()

    owned_run = await plane.repository.get_scoped_run(
        run_id=run_id,
        workspace_id=identity.workspace_id,
    )
    if owned_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    await plane.kernel.cancel(run_id)

    await stream_mgr.emit(
        plane.stream_event_repository,
        run_id=run_id,
        conversation_id=owned_run.conversation_id or "unknown",
        event_type="run.cancelled",
        payload={"run_id": run_id},
    )

    return CancelRunResponse(run_id=run_id, status="CANCELLED")


# 8. GET /agent/runs/{run_id}/events
@router.get("/runs/{run_id}/events")
async def get_run_events(
    request: Request,
    run_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    since_sequence: int | None = Query(None),
    last_event_id: int | None = Header(None, alias="Last-Event-ID"),
):
    plane = get_cosa_plane(request)
    owned_run = await plane.repository.get_scoped_run(
        run_id=run_id,
        workspace_id=identity.workspace_id,
    )
    if owned_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    stream_mgr = get_cosa_event_stream_manager()
    effective_sequence = since_sequence if since_sequence is not None else last_event_id

    return StreamingResponse(
        stream_mgr.stream_events(
            plane.stream_event_repository, run_id, since_sequence=effective_sequence
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def create_cosa_router() -> APIRouter:
    return router
