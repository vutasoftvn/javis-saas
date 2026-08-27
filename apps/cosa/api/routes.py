from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import uuid

import os
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from agent_core.capabilities.approval_service import ApprovalAlreadyDecidedError
from agent_core.conversations.models import (
    ConversationRecord,
    MessageAttachmentRecord,
    MessageRecord,
)
from apps.cosa.api.event_stream import (
    UX_EVENT_TYPES,
    get_cosa_event_stream_manager,
    redact_ux_event_payload,
)
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.auth.jwt import mint_delegation_token
from apps.cosa.api.schemas import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    AuthorizeConnectorRequest,
    CancelRunResponse,
    CompleteKnowledgeUploadResponse,
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    CreateKnowledgeUploadRequest,
    CreateScheduleRequest,
    EventEnvelopeDTO,
    GrantConnectorRequest,
    InstallConnectorRequest,
    KnowledgeUploadResponse,
    MessageAttachmentResponse,
    MessageCreate,
    MessageResponse,
    RevokeGrantRequest,
    RunResponse,
    RunSummaryResponse,
    ScheduleListResponse,
    ScheduleResponse,
    SessionStatus,
    SessionTimelineResponse,
    SessionViewResponse,
    WorkspaceArtifactResponse,
)
from apps.cosa.composition.agent_plane import CosaAgentPlane



__all__ = ["create_cosa_router", "router"]

router = APIRouter(prefix="/agent", tags=["agent-chat"])


def get_cosa_plane(request: Request) -> CosaAgentPlane:
    """Dependency injection từ `app.state.plane` (Phase 5 Composition
    Lifecycle) — `app.state.plane` được set ĐÚNG 1 LẦN ở FastAPI `lifespan`
    startup (`apps/cosa/api/app.py::create_cosa_app`) hoặc ngay khi tạo app
    nếu test injection qua `create_cosa_app(plane=...)`. Không còn lazy
    singleton tạo `CosaAgentPlane` mới trên request đầu tiên."""
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError(
            "CosaAgentPlane chưa sẵn sàng — app.state.plane rỗng. Lifespan startup "
            "chưa chạy (dùng httpx.ASGITransport mà không trigger lifespan) hoặc "
            "app được tạo sai cách — dùng create_cosa_app() hoặc create_cosa_app(plane=...)."
        )
    return plane


async def _conv_to_response(plane: CosaAgentPlane, conv: ConversationRecord) -> ConversationResponse:
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
        workspace_id=conv.workspace_id,
        created_by_principal=conv.created_by_principal,
        title=conv.title,
        active_agent_profile=conv.active_agent_profile or "operations",
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        archived_at=conv.archived_at,
        messages=msg_responses,
    )


def _ensure_conversation_tenant_match(conv: ConversationRecord, identity: AuthenticatedIdentity) -> None:
    """Tenant ownership check — theo COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_
    2026-08-25.md §13: mọi conversation query phải kèm authenticated workspace/
    company scope, không chỉ conversation_id. Trả 404 (không phải 403) để không
    lộ thông tin tồn tại của resource thuộc tenant khác."""
    if conv.workspace_id != identity.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


async def _get_owned_run_or_404(plane: CosaAgentPlane, run_id: str, identity: AuthenticatedIdentity):
    """Tenant ownership check cho run/approval/SSE — dùng get_scoped_run để enforce
    workspace_id ở layer database, không check sau lookup."""
    run_record = await plane.repository.get_scoped_run(
        run_id=run_id,
        workspace_id=identity.workspace_id,
    )
    if run_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run_record


# 1. POST /agent/conversations
@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
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
    conversations, total = await plane.conversation_repository.list_conversations(workspace_id=identity.workspace_id,
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

    agent_profile = conv.active_agent_profile or "operations"

    # Durable dispatch — thay asyncio.create_task (chết theo HTTP process) bằng
    # 1 scheduled task durable (plane.scheduler); apps/cosa/worker/main.py poll
    # + acquire lease + thực thi ở process riêng. Theo Master Guide §5 /
    # COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §29.6 Phase 4.
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
            "delegation_token": mint_delegation_token(identity.platform_user_id),
        },
    )

    return RunResponse(
        run_id=run_id,
        conversation_id=conversation_id,
        status="RUNNING",
        message_id=stored_user_message.message_id,
    )


# 6. POST /agent/runs/{run_id}/cancel
@router.post("/runs/{run_id}/cancel", response_model=CancelRunResponse)
async def cancel_run(
    request: Request,
    run_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane(request)
    stream_mgr = get_cosa_event_stream_manager()

    owned_run = await _get_owned_run_or_404(plane, run_id, identity)
    await plane.kernel.cancel(run_id)

    await stream_mgr.emit(
        plane.stream_event_repository,
        run_id=run_id,
        conversation_id=owned_run.conversation_id or "unknown",
        event_type="run.cancelled",
        payload={"run_id": run_id},
    )

    return CancelRunResponse(run_id=run_id, status="CANCELLED")


# 7. POST /agent/approvals/{approval_id}/decision
@router.post("/approvals/{approval_id}/decision", response_model=ApprovalDecisionResponse)
async def decide_approval(
    request: Request,
    approval_id: str,
    req: ApprovalDecisionRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane(request)
    stream_mgr = get_cosa_event_stream_manager()

    # Tenant check TRƯỚC khi cho phép quyết định — dùng get_scoped_approval để
    # enforce workspace_id ở query layer, ngăn chặn timing leak
    # nơi attacker phân biệt "approval exists for another tenant" vs "approval not found".
    existing_approval = await plane.approval_service.get_scoped_approval(
        approval_id=approval_id,
        workspace_id=identity.workspace_id,
    )
    if existing_approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval not found: {approval_id}")

    try:
        decided = await plane.approval_service.submit_decision(
            approval_id=approval_id,
            reviewer=identity.principal_id,
            approved=req.approved,
            reason=req.reason or "",
        )
    except ApprovalAlreadyDecidedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not decided:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval not found: {approval_id}")

    run_id = decided.run_id
    # We already checked ownership via _get_owned_run_or_404(existing_approval.run_id),
    # so we can safely use get_scoped_run for additional defense-in-depth
    run_record = await plane.repository.get_scoped_run(
        run_id=run_id,
        workspace_id=identity.workspace_id,
    )
    resume_conversation_id = run_record.conversation_id if run_record and run_record.conversation_id else "unknown"

    await stream_mgr.emit(
        plane.stream_event_repository,
        run_id=run_id,
        conversation_id=resume_conversation_id,
        event_type="approval.resolved",
        payload={
            "approval_id": approval_id,
            "status": decided.status,
            "reviewer": decided.reviewer,
            "reason": decided.reason,
        },
    )

    # Resume kernel if approved — checkpoint_ref lấy trực tiếp từ RunApprovalRecord
    # durable (agent_core.approvals.checkpoint_ref), không cần cache in-memory
    # riêng. Durable dispatch — thay asyncio.create_task(do_resume()) bằng 1
    # scheduled task durable, cùng nguyên tắc với create_message (Phase 4).
    if req.approved and decided.checkpoint_ref:
        await plane.scheduler.schedule(
            target_spec_id="cosa.resume",
            input_payload={
                "task_type": "resume",
                "run_id": run_id,
                "checkpoint_ref": decided.checkpoint_ref,
                "conversation_id": resume_conversation_id,
                "workspace_id": run_record.workspace_id if run_record else None,
                "delegation_token": mint_delegation_token(identity.platform_user_id),
            },
        )

    return ApprovalDecisionResponse(
        approval_id=decided.approval_id,
        run_id=decided.run_id,
        status=decided.status,
        reviewer=decided.reviewer or identity.principal_id,
        reason=decided.reason,
        decided_at=decided.decided_at or datetime.now(timezone.utc),
    )


# 7.1 GET /agent/approvals
@router.get("/approvals")
async def list_approvals(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    plane = get_cosa_plane(request)
    pending = await plane.approval_service.list_pending_approvals(workspace_id=identity.workspace_id,
    )
    items = []
    for app in pending:
        if status_filter and app.status != status_filter:
            continue
        items.append({
            "id": app.approval_id,
            "approval_id": app.approval_id,
            "run_id": app.run_id,
            "tool_call_id": app.tool_call_id,
            "checkpoint_ref": app.checkpoint_ref,
            "action": app.action,
            "subject": app.subject,
            "status": app.status,
            "risk_level": app.requirement.get("risk_level", "medium") if isinstance(app.requirement, dict) else "medium",
            "required_role": app.requirement.get("role", "admin") if isinstance(app.requirement, dict) else "admin",
            "policy_id": app.requirement.get("policy_id", "default") if isinstance(app.requirement, dict) else "default",
            "created_at": app.created_at.isoformat() if hasattr(app.created_at, "isoformat") else str(app.created_at),
        })
    return {"items": items, "total": len(items)}


# 8. GET /agent/runs/{run_id}/events
@router.get("/runs/{run_id}/events")
async def get_run_events(
    request: Request,
    run_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    since_sequence: Optional[int] = Query(None),
    last_event_id: Optional[int] = Header(None, alias="Last-Event-ID"),
):
    plane = get_cosa_plane(request)
    await _get_owned_run_or_404(plane, run_id, identity)

    stream_mgr = get_cosa_event_stream_manager()
    effective_sequence = since_sequence if since_sequence is not None else last_event_id

    return StreamingResponse(
        stream_mgr.stream_events(plane.stream_event_repository, run_id, since_sequence=effective_sequence),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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
    latest_run_summary: Optional[RunSummaryResponse] = None
    latest_run_id: Optional[str] = None
    if events:
        latest_run_id = events[-1].run_id
    elif messages:
        for m in reversed(messages):
            if m.run_id:
                latest_run_id = m.run_id
                break

    if latest_run_id:
        try:
            # Enforce scoped run lookup: even though latest_run_id comes from a scoped
            # conversation's events, verify workspace_id for defense-in-depth
            run_record = await plane.run_repository.get_scoped_run(
                run_id=latest_run_id,
                workspace_id=identity.workspace_id,
            )
            if run_record:
                latest_run_summary = RunSummaryResponse(
                    run_id=run_record.run_id,
                    status=run_record.status.value if hasattr(run_record.status, "value") else str(run_record.status),
                    created_at=run_record.created_at,
                    completed_at=run_record.completed_at,
                )
        except Exception:
            pass

    # Derive session status
    session_status: SessionStatus = "idle"
    if timeline_dtos:
        last_approval_event = None
        for ev in timeline_dtos:
            if ev.event_type in ("approval.required", "approval.resolved"):
                last_approval_event = ev.event_type
        if last_approval_event == "approval.required":
            session_status = "waiting_approval"
        else:
            last_event = timeline_dtos[-1]
            if last_event.event_type == "run.failed":
                session_status = "failed"
            elif last_event.event_type == "run.completed":
                session_status = "completed"
            elif latest_run_summary and latest_run_summary.status.upper() in ("RUNNING", "IN_PROGRESS"):
                session_status = "running"
            elif latest_run_summary and latest_run_summary.status.upper() in ("COMPLETED", "SUCCESS"):
                session_status = "completed"
            elif latest_run_summary and latest_run_summary.status.upper() in ("FAILED", "CANCELLED"):
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
        art_records = await plane.artifact_repository.list_for_conversation(workspace_id=identity.workspace_id, conversation_id=conv.conversation_id,
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
        workspace_id=conv.workspace_id,
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
    after_sequence: Optional[int] = Query(None, ge=0),
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


# 11. GET /agent/conversations/{conversation_id}/artifacts
@router.get("/conversations/{conversation_id}/artifacts", response_model=list[WorkspaceArtifactResponse])
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

    art_records = await plane.artifact_repository.list_for_conversation(workspace_id=identity.workspace_id, conversation_id=conv.conversation_id,
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


# 12. Connectors Proxy Routes (Task 3)
@router.post("/connectors/install")
async def install_connector(
    request: Request,
    body: InstallConnectorRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
    token = request.headers.get("Authorization") or f"Bearer {mint_delegation_token(identity.platform_user_id)}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/connectors/install",
            json={
                "workspaceId": identity.workspace_id,
                "connectorKey": body.connector_key,
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


@router.post("/connectors/authorize")
async def authorize_connector(
    request: Request,
    body: AuthorizeConnectorRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
    token = request.headers.get("Authorization") or f"Bearer {mint_delegation_token(identity.platform_user_id)}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/connectors/authorize",
            json={
                "installationId": body.installation_id,
                "secretRef": body.secret_ref,
                "grantedScopes": body.granted_scopes,
                "expiresAt": body.expires_at.isoformat(),
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


@router.post("/connectors/grant")
async def grant_connector(
    request: Request,
    body: GrantConnectorRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
    token = request.headers.get("Authorization") or f"Bearer {mint_delegation_token(identity.platform_user_id)}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/connectors/grant",
            json={
                "workspaceId": identity.workspace_id,
                "conversationId": body.conversation_id,
                "authorizationId": body.authorization_id,
                "allowedActions": body.allowed_actions,
                "expiresAt": body.expires_at.isoformat() if body.expires_at else None,
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


@router.post("/connectors/revoke")
async def revoke_connector(
    request: Request,
    body: RevokeGrantRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
    token = request.headers.get("Authorization") or f"Bearer {mint_delegation_token(identity.platform_user_id)}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{control_plane_url}/cosa/connectors/revoke",
            json={
                "workspaceId": identity.workspace_id,
                "conversationId": body.conversation_id,
                "grantId": body.grant_id,
            },
            headers={"Authorization": token},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


# 13. Schedules Proxy Routes (Task 4)
@router.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(
    request: Request,
    body: CreateScheduleRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
    token = request.headers.get("Authorization") or f"Bearer {mint_delegation_token(identity.platform_user_id)}"
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
    control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
    token = request.headers.get("Authorization") or f"Bearer {mint_delegation_token(identity.platform_user_id)}"
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
    control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
    token = request.headers.get("Authorization") or f"Bearer {mint_delegation_token(identity.platform_user_id)}"
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


# Knowledge Ingestion (Task 2)
# Phải kích hoạt feature flag KNOWLEDGE_INGESTION_ENABLED=true để cho phép routes

@router.post("/knowledge/uploads", status_code=201, response_model=KnowledgeUploadResponse, tags=["knowledge-ingestion"])
async def create_knowledge_upload(
    request: Request,
    payload: CreateKnowledgeUploadRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> KnowledgeUploadResponse:
    """POST /agent/knowledge/uploads — initiate document ingestion.

    Returns upload ticket with signed URL (object_key not exposed).
    """
    # Feature flag check
    if not os.environ.get("KNOWLEDGE_INGESTION_ENABLED", "false").lower() == "true":
        raise HTTPException(status_code=403, detail="Knowledge ingestion not enabled")

    # Use payload directly (FastAPI validation already done)
    req = payload

    # Get object store from app state
    object_store = getattr(request.app.state, "knowledge_object_store", None)
    if object_store is None:
        raise HTTPException(status_code=500, detail="Object store not initialized")

    # Get services/cosa client
    cosa_client = getattr(request.app.state, "cosa_document_ingestion_client", None)
    if cosa_client is None:
        cosa_client = _get_cosa_document_ingestion_client()

    # Create control-plane record via services/cosa
    control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
    try:
        # Use member bearer token for public endpoint
        token = identity.bearer_token
        # Use injected client if available, else create one
        http_client = getattr(request.app.state, "cosa_document_ingestion_client", None)
        should_close = False
        if http_client is None:
            http_client = httpx.AsyncClient(timeout=10.0)
            should_close = True

        try:
            resp = await http_client.post(
                f"{control_plane_url}/cosa/document-ingestions",
                json={
                    "workspaceId": identity.workspace_id,
                    "originalFilename": req.file_name,
                    "declaredMediaType": req.declared_media_type,
                    "idempotencyKey": req.idempotency_key,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code not in (200, 201):
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            ingestion_data = resp.json()
            ingestion_id = ingestion_data.get("id")
        finally:
            if should_close:
                await http_client.aclose()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Control plane error: {e}")

    # Issue upload ticket
    try:
        from apps.cosa.knowledge_ingestion.contracts import MIME_TYPE_LIMITS

        max_bytes = MIME_TYPE_LIMITS.get(req.declared_media_type, 10 * 1024 * 1024)
        ticket = await object_store.issue_upload_ticket(
            ingestion_id=ingestion_id,
            workspace_id=identity.workspace_id,
            media_type=req.declared_media_type,
            max_bytes=max_bytes,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Object store error: {e}")

    # Return response (no object_key, only signed_url)
    return KnowledgeUploadResponse(
        ingestion_id=ingestion_id,
        state="UPLOADING",
        file_name=req.file_name,
        declared_media_type=req.declared_media_type,
        signed_upload_url=ticket.signed_url,
        expires_at=ticket.expires_at,
    )


@router.post("/knowledge/uploads/{ingestion_id}/complete", status_code=200, response_model=CompleteKnowledgeUploadResponse, tags=["knowledge-ingestion"])
async def complete_knowledge_upload(
    request: Request,
    ingestion_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> CompleteKnowledgeUploadResponse:
    """POST /agent/knowledge/uploads/{ingestion_id}/complete — finalize upload.

    Server validates size, computes SHA-256, sniffs MIME, then transitions to QUEUED.
    """
    # Feature flag check
    if not os.environ.get("KNOWLEDGE_INGESTION_ENABLED", "false").lower() == "true":
        raise HTTPException(status_code=403, detail="Knowledge ingestion not enabled")

    # Get object store
    object_store = getattr(request.app.state, "knowledge_object_store", None)
    if object_store is None:
        raise HTTPException(status_code=500, detail="Object store not initialized")

    # Finalize upload in storage
    try:
        quarantined = await object_store.finalize_upload(
            ingestion_id=ingestion_id,
            workspace_id=identity.workspace_id,
        )
    except ValueError as e:
        # Non-enumerating error for missing/expired ticket
        raise HTTPException(status_code=404, detail="Ingestion not found or ticket expired")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Object store error: {e}")

    # Call services/cosa to complete upload and transition UPLOADING→QUARANTINED→QUEUED
    # Use worker service token (broker is a trusted internal caller)
    control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
    try:
        # Use worker service token for this internal endpoint
        worker_token = os.environ.get("COSA_WORKER_SERVICE_TOKEN", "")
        if not worker_token:
            raise HTTPException(status_code=500, detail="Worker service token not configured")

        # Use injected client if available, else create one
        http_client = getattr(request.app.state, "cosa_document_ingestion_client", None)
        should_close = False
        if http_client is None:
            http_client = httpx.AsyncClient(timeout=10.0)
            should_close = True

        try:
            resp = await http_client.post(
                f"{control_plane_url}/cosa/document-ingestions/{ingestion_id}/complete",
                json={
                    "detectedMediaType": quarantined.detected_media_type,
                    "sizeBytes": quarantined.size_bytes,
                    "sourceSha256": quarantined.source_sha256,
                    "objectKey": quarantined.object_key,
                },
                headers={"Authorization": f"Bearer {worker_token}"},
            )
            if resp.status_code not in (200, 202):
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            completion_data = resp.json()
        finally:
            if should_close:
                await http_client.aclose()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Control plane error: {e}")

    # Return response (no object_key leaked)
    return CompleteKnowledgeUploadResponse(
        ingestion_id=ingestion_id,
        state=completion_data.get("state", "QUEUED"),
        detected_media_type=quarantined.detected_media_type,
        size_bytes=quarantined.size_bytes,
        source_sha256=quarantined.source_sha256,
    )


def _get_cosa_document_ingestion_client():
    """Get or create services/cosa document ingestion client."""
    return httpx.AsyncClient()


def create_cosa_router() -> APIRouter:
    return router



