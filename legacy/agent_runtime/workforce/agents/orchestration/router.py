import json
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from workforce.agents.orchestration import service as orchestration_service
from workforce.agents.orchestration.result import ChiefOfStaffResult
from workforce.agents.orchestration.mission_control_bus import mission_control_bus

from core.auth import get_current_workspace_member
from db.models import WorkspaceMember
from db.session import get_db

router = APIRouter()


class OrchestrateRequest(BaseModel):
    goal: str
    context: Optional[dict[str, Any]] = None


@router.post("/orchestrate", response_model=ChiefOfStaffResult)
async def orchestrate_founder_mission(
    payload: OrchestrateRequest,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> ChiefOfStaffResult:
    """Trigger an autonomous Chief of Staff multi-agent orchestration mission."""
    if not payload.goal or not payload.goal.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Goal description is required",
        )

    result = await orchestration_service.orchestrate_mission(
        db=db,
        workspace_id=current_member.workspace_id,
        user_id=current_member.user_id,
        goal=payload.goal.strip(),
        context=payload.context,
    )
    return result


@router.get("/stream/{run_id}")
async def stream_mission_events(
    run_id: str,
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Server-Sent Events (SSE) stream for live mission execution updates."""

    async def event_generator():
        async for event in mission_control_bus.subscribe(run_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
