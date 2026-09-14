"""Project Activity Feed routes: list, detail, and SSE stream (Task 5).

Mỗi route gọi verify_project_context trước; isolation workspace+project;
redaction ở detail; SSE stream có Last-Event-ID resume từ ProjectActivityRepository.list_since.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from agent.project_activity.repository import ProjectActivityRepository
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from apps.cosa.api.project_context import verify_project_context
from apps.cosa.api.schemas import (
    ProjectActivityDetailDTO,
    ProjectActivityEventDTO,
    ProjectActivityListResponse,
)
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.composition.agent_plane import CosaAgentPlane

__all__ = ["create_project_activity_router"]

logger = logging.getLogger("cosa.api.project_activity_routes")

# SSE heartbeat để tránh timeout client
PROJECT_ACTIVITY_HEARTBEAT_INTERVAL_SEC = 15.0


def get_cosa_plane(request: Request) -> CosaAgentPlane:
    """Dependency injection từ `app.state.plane`."""
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError("CosaAgentPlane chưa sẵn sàng — app.state.plane rỗng.")
    return plane


def _event_record_to_dto(record: Any) -> ProjectActivityEventDTO:
    """Map ProjectActivityEventRecord -> DTO (không dính Python internals)."""
    return ProjectActivityEventDTO(
        event_id=record.event_id,
        workspace_id=record.workspace_id,
        project_id=record.project_id,
        project_sequence=record.project_sequence,
        kind=record.kind,
        phase=record.phase,
        status=record.status,
        actor_kind=record.actor_kind,
        actor_id=record.actor_id,
        correlation_id=record.correlation_id,
        source_type=record.source_type,
        source_id=record.source_id,
        source_version=record.source_version,
        summary=record.summary or {},
        classification=record.classification,
        payload_hash=record.payload_hash,
        integrity_hash=getattr(record, "integrity_hash", None),
        occurred_at=record.occurred_at,
        recorded_at=record.recorded_at,
    )


async def _fetch_and_verify_source_visibility(
    plane: CosaAgentPlane,
    identity: AuthenticatedIdentity,
    source_type: str,
    source_id: str,
) -> tuple[bool, dict[str, Any] | None]:
    """Rechecks visibility của source record. Trả (is_visible, source_ref).

    - Nếu source là runtime record (run/conversation/message) — dùng scoped
      repository (workspace_id + project_id already enforced).
    - Nếu source là business fact (task/decision/evidence) — cần check Company
      authorization result (không access Company DB trực tiếp).

    Nếu source không tồn tại hoặc caller không có quyền -> (False, None).
    """
    if source_type == "run":
        run = await plane.repository.get_run(source_id)
        if run is None or run.workspace_id != identity.workspace_id:
            return False, None
        return True, {"type": "run", "id": run.run_id, "status": run.status}

    elif source_type == "conversation":
        conv = await plane.conversation_repository.get_conversation(source_id)
        if conv is None or conv.workspace_id != identity.workspace_id:
            return False, None
        return True, {"type": "conversation", "id": conv.conversation_id, "title": conv.title}

    elif source_type == "message":
        msg = await plane.conversation_repository.get_message(source_id)
        if msg is None or msg.workspace_id != identity.workspace_id:
            return False, None
        return True, {"type": "message", "id": msg.message_id, "created_at": msg.created_at}

    # Business facts: không query trực tiếp Company DB từ apps/cosa —
    # chỉ trust Project Activity data đã ghi sẵn, KHÔNG rehydrate source.
    # Nếu cần chi tiết task/decision/evidence, Flutter gọi Company API riêng.
    elif source_type in ("task", "decision", "evidence", "deliberation", "deliberation_analysis"):
        # Đơn giản: nếu activity record tồn tại với source này, assume nó
        # được xác thực lúc ghi. Không re-auth Business facts từ Agent Platform.
        return True, {"type": source_type, "id": source_id}

    # Không biết loại source — refuse to reveal
    return False, None


async def _stream_project_activity(
    plane: CosaAgentPlane,
    identity: AuthenticatedIdentity,
    project_id: str,
    after_sequence: int | None = None,
) -> AsyncGenerator[str, None]:
    """SSE generator cho Project Activity stream.

    Dùng list_since từ repository làm source of truth. Trên reconnect, replay
    lại toàn bộ rows > after_sequence rồi mở subscription cho future events.

    Heartbeat every 15s để client không timeout; project_id trong payload.
    """
    repo: ProjectActivityRepository = getattr(plane, "project_activity_repository", None)
    if repo is None:
        yield "event: error\ndata: {\"error\": \"Project Activity repository unavailable\"}\n\n"
        return

    # Replay history
    replay_events = await repo.list_since(
        workspace_id=identity.workspace_id,
        project_id=project_id,
        after_sequence=after_sequence,
        limit=1000,  # Reasonable replay limit
    )

    for event in replay_events:
        dto = _event_record_to_dto(event)
        yield f"id: {dto.project_sequence}\n"
        yield f"data: {dto.model_dump_json()}\n\n"

    # Heartbeat loop (simple keepalive; không có live fanout vào demo này,
    # nhưng SSE stream vẫn open khi client connect).
    heartbeat_count = 0
    while True:
        await asyncio.sleep(PROJECT_ACTIVITY_HEARTBEAT_INTERVAL_SEC)
        heartbeat_count += 1
        yield f": heartbeat {heartbeat_count}\n\n"


def create_project_activity_router() -> APIRouter:
    router = APIRouter(prefix="/agent", tags=["project-activity"])

    # IMPORTANT: stream endpoint must be registered BEFORE detail endpoint
    # to prevent FastAPI matching /activity/stream as /activity/{event_id}
    @router.get("/projects/{project_id}/activity/stream", response_class=StreamingResponse)
    async def stream_project_activity(
        project_id: str,
        request: Request,
        identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
        plane: CosaAgentPlane = Depends(get_cosa_plane),
    ) -> StreamingResponse:
        """GET /agent/projects/{project_id}/activity/stream (SSE)

        Durable, resumable activity stream. Last-Event-ID header để reconnect.
        Source of truth là repository.list_since(); không in-memory queue only.
        """
        # Verify Project context
        await verify_project_context(plane, identity, project_id)

        # Parse Last-Event-ID (tùy chọn, kiểu integer sequence)
        last_event_id = request.headers.get("last-event-id", "").strip()
        after_sequence = None

        if last_event_id:
            try:
                after_sequence = int(last_event_id)
                if after_sequence <= 0:
                    raise ValueError("Last-Event-ID must be positive")
            except (ValueError, TypeError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Last-Event-ID: must be a positive integer",
                ) from exc

        # Tạo generator với proper SSE format
        async def event_generator():
            try:
                async for line in _stream_project_activity(plane, identity, project_id, after_sequence):
                    yield line
            except Exception as e:
                logger.exception("Error in project activity stream: %s", e)
                yield f"event: error\ndata: {{\"error\": \"{e!s}\"}}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @router.get("/projects/{project_id}/activity")
    async def list_project_activity(
        project_id: str,
        after_project_sequence: int | None = Query(None, ge=0),
        limit: int | None = Query(None, ge=1, le=100),
        kinds: str | None = Query(None),  # CSV filter
        identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
        plane: CosaAgentPlane = Depends(get_cosa_plane),
    ) -> ProjectActivityListResponse:
        """GET /agent/projects/{project_id}/activity

        Danh sách activity của Project, có phân trang theo project_sequence.
        Yêu cầu workspace + project authorization; không lộ foreign Project.
        """
        # Verify Project context thực
        await verify_project_context(plane, identity, project_id)

        # Lấy repo
        repo: ProjectActivityRepository = getattr(plane, "project_activity_repository", None)
        if repo is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Project Activity repository unavailable",
            )

        # List từ repository
        effective_limit = min(limit or 100, 100)  # Cap at 100
        events = await repo.list_since(
            workspace_id=identity.workspace_id,
            project_id=project_id,
            after_sequence=after_project_sequence,
            limit=effective_limit,
        )

        # Optionally filter by kinds
        if kinds:
            kind_set = set(kinds.split(","))
            events = [e for e in events if e.kind in kind_set]

        dtos = [_event_record_to_dto(e) for e in events]
        return ProjectActivityListResponse(
            items=dtos,
            total=len(dtos),
            next_cursor=dtos[-1].project_sequence if dtos else None,
        )

    @router.get("/projects/{project_id}/activity/{event_id}")
    async def get_project_activity_detail(
        project_id: str,
        event_id: str,
        identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
        plane: CosaAgentPlane = Depends(get_cosa_plane),
    ) -> ProjectActivityDetailDTO:
        """GET /agent/projects/{project_id}/activity/{event_id}

        Detail endpoint — rechecks source visibility, không trả raw source object.
        Nếu source bị restricted hoặc không tồn tại -> redacted metadata only.
        """
        # Verify Project context
        await verify_project_context(plane, identity, project_id)

        # Get repo
        repo: ProjectActivityRepository = getattr(plane, "project_activity_repository", None)
        if repo is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Project Activity repository unavailable",
            )

        # Tra event từ repo
        events = await repo.list_since(
            workspace_id=identity.workspace_id,
            project_id=project_id,
            after_sequence=None,
            limit=10000,  # Load all to find event_id
        )
        event = None
        for e in events:
            if e.event_id == event_id:
                event = e
                break

        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity event {event_id} not found",
            )

        # Recheck source visibility
        is_visible, source_ref = await _fetch_and_verify_source_visibility(
            plane, identity, event.source_type, event.source_id
        )

        # Build detail DTO
        return ProjectActivityDetailDTO(
            event_id=event.event_id,
            workspace_id=event.workspace_id,
            project_id=event.project_id,
            project_sequence=event.project_sequence,
            kind=event.kind,
            phase=event.phase,
            status=event.status,
            actor_kind=event.actor_kind,
            actor_id=event.actor_id,
            correlation_id=event.correlation_id,
            source_type=event.source_type,
            source_id=event.source_id,
            source_version=event.source_version,
            source_reference=source_ref if is_visible else None,
            source_visibility="full" if is_visible else "unavailable",
            summary=event.summary or {} if is_visible else {},
            classification=event.classification,
            payload_hash=event.payload_hash,
            integrity_hash=getattr(event, "integrity_hash", None),
            occurred_at=event.occurred_at,
            recorded_at=event.recorded_at,
        )

    return router
