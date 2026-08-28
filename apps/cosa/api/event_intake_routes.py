from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from apps.cosa.events.router import handle_event, Unauthenticated, PermissionDenied


def create_event_intake_router() -> APIRouter:
    router = APIRouter(prefix="/agent/internal", tags=["event-intake"])

    @router.post("/events")
    async def intake(request: Request, x_cosa_local_signature: str = Header(default="")):
        plane = getattr(request.app.state, "plane", None)
        deps = getattr(plane, "event_intake_deps", None) if plane else None
        if deps is None:
            raise HTTPException(status_code=500, detail="event intake dependencies not configured")

        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="invalid JSON body")

        try:
            result = await handle_event(deps, body, x_cosa_local_signature)
        except Unauthenticated as e:
            raise HTTPException(status_code=401, detail=str(e))
        except PermissionDenied as e:
            raise HTTPException(status_code=403, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return result.model_dump(exclude_none=True)

    return router
