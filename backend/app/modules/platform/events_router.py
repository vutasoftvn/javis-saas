import json
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.core.events import event_broker, EventEnvelope

router = APIRouter()


@router.get("/stream")
async def stream_workspace_events(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Kênh phát luồng sự kiện thời gian thực (SSE) cho toàn bộ workspace (§106, §127)."""
    if member.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden to this workspace event stream"
        )

    async def event_generator():
        # Gửi sự kiện bắt tay khởi tạo kết nối
        yield {
            "event": "system.connected",
            "data": json.dumps({
                "workspace_id": str(workspace_id),
                "user_id": str(member.user_id),
                "status": "connected"
            })
        }

        try:
            async for envelope in event_broker.subscribe(str(workspace_id)):
                yield {
                    "event": envelope.event_type,
                    "data": json.dumps(envelope.model_dump())
                }
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())
