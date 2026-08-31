"""Conversation CRUD & message routes for COSA Agent Platform."""

from __future__ import annotations

import logging
import uuid

from agent.conversations.models import ConversationRecord, MessageAttachmentRecord, MessageRecord
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError

from apps.cosa.api.event_stream import (
    UX_EVENT_TYPES,
    get_cosa_event_stream_manager,
    redact_ux_event_payload,
)
from apps.cosa.api.schemas import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    EventEnvelopeDTO,
    MessageAttachmentResponse,
    MessageCreate,
    MessageResponse,
    RunResponse,
    RunSummaryResponse,
    SessionStatus,
    SessionViewResponse,
    WorkspaceArtifactResponse,
)
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.compliance.data_egress_context import DirectMessageDataAccess
from apps.cosa.composition.agent_plane import CosaAgentPlane

__all__ = ["create_conversation_router"]

logger = logging.getLogger("cosa.api.conversation_routes")

router = APIRouter(prefix="/agent", tags=["agent-chat"])


def get_cosa_plane(request: Request) -> CosaAgentPlane:
    """Dependency injection từ `app.state.plane`."""
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError(
            "CosaAgentPlane chưa sẵn sàng — app.state.plane rỗng."
        )
    return plane


async def _conv_to_response(
    plane: CosaAgentPlane, conv: ConversationRecord
) -> ConversationResponse:
    """Convert ConversationRecord to API response DTO."""
    messages = await plane.conversation_repository.list_messages(conv.conversation_id)
    msg_responses = [
        MessageResponse(
            id=m.message_id,
            conversation_id=conv.conversation_id,
            role=m.role,
            content=m.content,
            run_id=m.run_id,
            parent_message_id=m.parent_message_id,
            status=m.status,
            created_at=m.created_at,
            attachments=[
                MessageAttachmentResponse(
                    id=att.attachment_id,
                    message_id=m.message_id,
                    object_ref=att.object_ref,
                    media_type=att.media_type,
                    file_name=att.file_name,
                    size=att.size,
                    checksum=att.checksum,
                    knowledge_ingest_status=att.knowledge_ingest_status,
                )
                for att in m.attachments
            ],
        )
        for m in messages
    ]

    return ConversationResponse(
        id=conv.conversation_id,
        workspace_id=conv.workspace_id or "",
        created_by_principal=conv.created_by_principal,
        title=conv.title,
        active_agent_profile=conv.active_agent_profile or "operations",
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        archived_at=conv.archived_at,
        messages=msg_responses,
    )


# 1. POST /agent/conversations
@router.post(
    "/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED
)
async def create_conversation(
    request: Request,
    req: ConversationCreate,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane(request)
    active_profile = req.agent_profile_id or req.active_agent_profile or "operations"

    conv = ConversationRecord(
        conversation_id=f"conv_{uuid.uuid4().hex[:12]}",
        workspace_id=identity.workspace_id,
        created_by_principal=identity.principal_id,
        title=req.title or "New Conversation",
        active_agent_profile=active_profile,
    )
    conv = await plane.conversation_repository.create_conversation(conv)
    return await _conv_to_response(plane, conv)


# 2. GET /agent/conversations
@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    include_archived: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    plane = get_cosa_plane(request)
    conversations, total = await plane.conversation_repository.list_conversations(
        workspace_id=identity.workspace_id,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    items = [await _conv_to_response(plane, conv) for conv in conversations]
    return ConversationListResponse(items=items, total=total)


# 3. GET /agent/conversations/{conversation_id}
@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    request: Request,
    conversation_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane(request)
    conv = await plane.conversation_repository.get_scoped_conversation(
        workspace_id=identity.workspace_id,
        conversation_id=conversation_id,
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return await _conv_to_response(plane, conv)


# 4. PATCH /agent/conversations/{conversation_id}
@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    request: Request,
    conversation_id: str,
    req: ConversationUpdate,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane(request)
    existing = await plane.conversation_repository.get_scoped_conversation(
        workspace_id=identity.workspace_id,
        conversation_id=conversation_id,
    )
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    conv = await plane.conversation_repository.update_conversation(
        conversation_id,
        title=req.title,
        active_agent_profile=req.agent_profile_id or req.active_agent_profile,
        archived=req.archived,
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return await _conv_to_response(plane, conv)


# 5. POST /agent/conversations/{conversation_id}/messages
@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_message(
    request: Request,
    conversation_id: str,
    req: MessageCreate,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane(request)
    conv = await plane.conversation_repository.get_scoped_conversation(
        workspace_id=identity.workspace_id,
        conversation_id=conversation_id,
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    # Validate phân loại dữ liệu TRƯỚC side effect
    try:
        DirectMessageDataAccess(
            categories=frozenset(req.data_access.categories),
            subject_reference=req.data_access.subject_reference,
            source_ref="pending",
            source_hash="pending",
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    run_id = f"run_{uuid.uuid4().hex[:16]}"
    stream_mgr = get_cosa_event_stream_manager()
    stream_mgr.start_run(run_id)

    # Save user message
    user_message = MessageRecord(
        conversation_id=conversation_id,
        role=req.role or "user",
        content=req.content,
        run_id=run_id,
        parent_message_id=req.parent_message_id,
        status="completed",
    )
    attachments = [
        MessageAttachmentRecord(
            message_id=user_message.message_id,
            object_ref=a.object_ref,
            media_type=a.media_type,
            file_name=a.file_name,
            size=a.size,
            checksum=a.checksum,
        )
        for a in (req.attachments or [])
    ]
    stored_user_message = await plane.conversation_repository.add_message(user_message, attachments)

    # Dựng context egress THẬT từ ID + nội dung ĐÃ LƯU
    direct_message_data_access = DirectMessageDataAccess.from_message(
        message_id=stored_user_message.message_id,
        content=stored_user_message.content,
        categories=frozenset(req.data_access.categories),
        subject_reference=req.data_access.subject_reference,
    )

    agent_profile = conv.active_agent_profile or "operations"

    # Durable dispatch — schedule task
    await plane.scheduler.schedule(
        target_spec_id=f"cosa.{agent_profile}",
        input_payload={
            "task_type": "run",
            "run_id": run_id,
            "conversation_id": conversation_id,
            "user_prompt": req.content,
            "agent_profile": agent_profile,
            "principal": identity.principal_id,
            "workspace_id": identity.workspace_id,
            "delegation_token": identity.mint_delegation(),
            "direct_message_data_access": direct_message_data_access.model_dump(mode="json"),
        },
    )

    return RunResponse(
        run_id=run_id,
        conversation_id=conversation_id,
        status="RUNNING",
        message_id=stored_user_message.message_id,
    )


# 9. GET /agent/sessions/{conversation_id}
@router.get("/sessions/{conversation_id}", response_model=SessionViewResponse)
async def get_session_view(
    request: Request,
    conversation_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane(request)
    conv = await plane.conversation_repository.get_scoped_conversation(
        workspace_id=identity.workspace_id,
        conversation_id=conversation_id,
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session/Conversation {conversation_id} not found in current workspace.",
        )

    messages = await plane.conversation_repository.list_messages(conv.conversation_id)
    msg_responses = [
        MessageResponse(
            id=m.message_id,
            conversation_id=conv.conversation_id,
            role=m.role,
            content=m.content,
            run_id=m.run_id,
            parent_message_id=m.parent_message_id,
            status=m.status,
            created_at=m.created_at,
            attachments=[
                MessageAttachmentResponse(
                    id=att.attachment_id,
                    message_id=m.message_id,
                    object_ref=att.object_ref,
                    media_type=att.media_type,
                    file_name=att.file_name,
                    size=att.size,
                    checksum=att.checksum,
                    knowledge_ingest_status=att.knowledge_ingest_status,
                )
                for att in m.attachments
            ],
        )
        for m in messages
    ]

    # Fetch stream events for timeline
    events = await plane.stream_event_repository.list_since_for_conversation(conv.conversation_id)
    timeline_dtos: list[EventEnvelopeDTO] = []
    for ev in events:
        if ev.event_type in UX_EVENT_TYPES:
            timeline_dtos.append(
                EventEnvelopeDTO(
                    run_id=ev.run_id,
                    conversation_id=ev.conversation_id,
                    sequence=ev.sequence or 0,
                    event_type=ev.event_type,
                    timestamp=ev.created_at,
                    payload=redact_ux_event_payload(ev.event_type, ev.payload),
                    correlation_id=ev.correlation_id,
                )
            )

    # Determine latest run
    latest_run_summary: RunSummaryResponse | None = None
    latest_run_id: str | None = None
    if events:
        latest_run_id = events[-1].run_id
    elif messages:
        for m in reversed(messages):
            if m.run_id:
                latest_run_id = m.run_id
                break

    if latest_run_id:
        try:
            run_record = await plane.repository.get_scoped_run(
                run_id=latest_run_id,
                workspace_id=identity.workspace_id,
            )
            if run_record:
                latest_run_summary = RunSummaryResponse(
                    run_id=run_record.run_id,
                    status=run_record.status.value
                    if hasattr(run_record.status, "value")
                    else str(run_record.status),
                    created_at=run_record.created_at,
                    completed_at=run_record.completed_at,
                )
        except Exception:
            pass

    # Derive session status
    session_status: SessionStatus = "idle"
    if timeline_dtos:
        last_approval_event = None
        for dto in timeline_dtos:
            if dto.event_type in ("approval.required", "approval.resolved"):
                last_approval_event = dto.event_type
        if last_approval_event == "approval.required":
            session_status = "waiting_approval"
        else:
            last_dto = timeline_dtos[-1]
            if last_dto.event_type == "run.failed":
                session_status = "failed"
            elif last_dto.event_type == "run.completed":
                session_status = "completed"
            elif latest_run_summary and latest_run_summary.status.upper() in (
                "RUNNING",
                "IN_PROGRESS",
            ):
                session_status = "running"
            elif latest_run_summary and latest_run_summary.status.upper() in (
                "COMPLETED",
                "SUCCESS",
            ):
                session_status = "completed"
            elif latest_run_summary and latest_run_summary.status.upper() in (
                "FAILED",
                "CANCELLED",
            ):
                session_status = "failed"
            else:
                session_status = "running"
    elif latest_run_summary:
        if latest_run_summary.status.upper() in ("RUNNING", "IN_PROGRESS"):
            session_status = "running"
        elif latest_run_summary.status.upper() in ("COMPLETED", "SUCCESS"):
            session_status = "completed"
        elif latest_run_summary.status.upper() in ("FAILED", "CANCELLED"):
            session_status = "failed"

    # Artifacts
    artifacts_dtos: list[WorkspaceArtifactResponse] = []
    if hasattr(plane, "artifact_repository") and plane.artifact_repository is not None:
        art_records = await plane.artifact_repository.list_for_conversation(
            workspace_id=identity.workspace_id,
            conversation_id=conv.conversation_id,
        )
        artifacts_dtos = [
            WorkspaceArtifactResponse(
                artifact_id=a.artifact_id,
                workspace_id=a.workspace_id,
                conversation_id=a.conversation_id,
                run_id=a.run_id,
                source_message_id=a.source_message_id,
                artifact_kind=a.artifact_kind,
                display_name=a.display_name,
                media_type=a.media_type,
                object_ref=a.object_ref,
                checksum=a.checksum,
                size_bytes=a.size_bytes,
                status=a.status,
                input_artifact_ids=a.input_artifact_ids,
                created_at=a.created_at,
                archived_at=a.archived_at,
            )
            for a in art_records
        ]

    enabled_connector_keys = []
    if isinstance(conv.metadata, dict) and "enabled_connector_keys" in conv.metadata:
        enabled_connector_keys = conv.metadata["enabled_connector_keys"]

    return SessionViewResponse(
        id=conv.conversation_id,
        workspace_id=conv.workspace_id or "",
        title=conv.title,
        agent_profile=conv.active_agent_profile or "operations",
        status=session_status,
        latest_run=latest_run_summary,
        messages=msg_responses,
        timeline=timeline_dtos,
        artifacts=artifacts_dtos,
        enabled_connector_keys=enabled_connector_keys,
    )


# 10. GET /agent/sessions/{conversation_id}/timeline
@router.get("/sessions/{conversation_id}/timeline", response_model=list[EventEnvelopeDTO])
async def get_session_timeline(
    request: Request,
    conversation_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    after_sequence: int | None = Query(None, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    plane = get_cosa_plane(request)
    conv = await plane.conversation_repository.get_scoped_conversation(
        workspace_id=identity.workspace_id,
        conversation_id=conversation_id,
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session/Conversation {conversation_id} not found in current workspace.",
        )

    events = await plane.stream_event_repository.list_since_for_conversation(
        conversation_id=conv.conversation_id,
        after_sequence=after_sequence,
        limit=limit,
    )
    results: list[EventEnvelopeDTO] = []
    for ev in events:
        if ev.event_type in UX_EVENT_TYPES:
            results.append(
                EventEnvelopeDTO(
                    run_id=ev.run_id,
                    conversation_id=ev.conversation_id,
                    sequence=ev.sequence or 0,
                    event_type=ev.event_type,
                    timestamp=ev.created_at,
                    payload=redact_ux_event_payload(ev.event_type, ev.payload),
                    correlation_id=ev.correlation_id,
                )
            )
    return results


# 11. GET /agent/conversations/{conversation_id}/artifacts (and /sessions alias)
@router.get(
    "/conversations/{conversation_id}/artifacts", response_model=list[WorkspaceArtifactResponse]
)
@router.get("/sessions/{conversation_id}/artifacts", response_model=list[WorkspaceArtifactResponse])
async def list_conversation_artifacts(
    request: Request,
    conversation_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane(request)
    conv = await plane.conversation_repository.get_scoped_conversation(
        workspace_id=identity.workspace_id,
        conversation_id=conversation_id,
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found in current workspace.",
        )

    if not hasattr(plane, "artifact_repository") or plane.artifact_repository is None:
        return []

    art_records = await plane.artifact_repository.list_for_conversation(
        workspace_id=identity.workspace_id,
        conversation_id=conv.conversation_id,
    )
    return [
        WorkspaceArtifactResponse(
            artifact_id=a.artifact_id,
            workspace_id=a.workspace_id,
            conversation_id=a.conversation_id,
            run_id=a.run_id,
            source_message_id=a.source_message_id,
            artifact_kind=a.artifact_kind,
            display_name=a.display_name,
            media_type=a.media_type,
            object_ref=a.object_ref,
            checksum=a.checksum,
            size_bytes=a.size_bytes,
            status=a.status,
            input_artifact_ids=a.input_artifact_ids,
            created_at=a.created_at,
            archived_at=a.archived_at,
        )
        for a in art_records
    ]


def create_conversation_router() -> APIRouter:
    """Export router for app.py registration."""
    return router
