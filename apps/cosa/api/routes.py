from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from agent_core.capabilities.approval_service import ApprovalAlreadyDecidedError
from agent_core.contracts.run import RunRequest, RunStatus
from agent_core.conversations.models import (
    ConversationRecord,
    MessageAttachmentRecord,
    MessageRecord,
)
from apps.cosa.agents.specs import COSA_FINANCE_AGENT_SPEC, COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.api.event_stream import (
    CosaEventStreamManager,
    get_cosa_event_stream_manager,
)
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.api.schemas import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    CancelRunResponse,
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageAttachmentResponse,
    MessageCreate,
    MessageResponse,
    RunResponse,
)
from apps.cosa.composition.agent_plane import CosaAgentPlane, build_cosa_agent_plane

__all__ = ["create_cosa_router", "router"]

router = APIRouter(prefix="/agent", tags=["agent-chat"])

_plane_instance: Optional[CosaAgentPlane] = None


def get_cosa_plane() -> CosaAgentPlane:
    global _plane_instance
    if _plane_instance is None:
        _plane_instance = build_cosa_agent_plane()
    return _plane_instance


def set_cosa_plane(plane: Optional[CosaAgentPlane]) -> None:
    global _plane_instance
    _plane_instance = plane


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
        company_id=conv.company_id,
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
    if conv.company_id != identity.company_id or conv.workspace_id != identity.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


async def _get_owned_run_or_404(plane: CosaAgentPlane, run_id: str, identity: AuthenticatedIdentity):
    """Tenant ownership check cho run/approval/SSE — cùng nguyên tắc với
    _ensure_conversation_tenant_match."""
    run_record = await plane.repository.get_run(run_id)
    if run_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if run_record.company_id != identity.company_id or run_record.workspace_id != identity.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run_record


# 1. POST /agent/conversations
@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    req: ConversationCreate,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane()
    active_profile = req.agent_profile_id or req.active_agent_profile or "operations"

    conv = ConversationRecord(
        conversation_id=f"conv_{uuid.uuid4().hex[:12]}",
        company_id=identity.company_id,
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
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    include_archived: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    plane = get_cosa_plane()
    conversations, total = await plane.conversation_repository.list_conversations(
        company_id=identity.company_id,
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
    conversation_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane()
    conv = await plane.conversation_repository.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    _ensure_conversation_tenant_match(conv, identity)
    return await _conv_to_response(plane, conv)


# 4. PATCH /agent/conversations/{conversation_id}
@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    req: ConversationUpdate,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane()
    existing = await plane.conversation_repository.get_conversation(conversation_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    _ensure_conversation_tenant_match(existing, identity)

    conv = await plane.conversation_repository.update_conversation(
        conversation_id,
        title=req.title,
        active_agent_profile=req.agent_profile_id or req.active_agent_profile,
        archived=req.archived,
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return await _conv_to_response(plane, conv)


async def _append_message(
    plane: CosaAgentPlane,
    *,
    conversation_id: str,
    role: str,
    content: str,
    run_id: Optional[str] = None,
    status_: str = "completed",
) -> MessageRecord:
    message = MessageRecord(
        conversation_id=conversation_id,
        role=role,
        content=content,
        run_id=run_id,
        status=status_,
    )
    return await plane.conversation_repository.add_message(message)


async def _execute_canonical_run_task(
    *,
    run_id: str,
    conversation_id: str,
    user_prompt: str,
    agent_profile: str,
    plane: CosaAgentPlane,
    stream_mgr: CosaEventStreamManager,
    principal: str,
    workspace_id: str,
    company_id: str,
):
    # 1. Resolve Spec
    if "finance" in agent_profile:
        spec = COSA_FINANCE_AGENT_SPEC
    else:
        spec = COSA_OPERATIONS_AGENT_SPEC

    # 2. Emit initial events
    stream_mgr.emit(
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="run.started",
        payload={"run_id": run_id, "conversation_id": conversation_id, "goal": user_prompt},
    )
    stream_mgr.emit(
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="reasoning.status",
        payload={"status": "thinking"},
    )
    stream_mgr.emit(
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="message.started",
        payload={"role": "assistant"},
    )

    req = RunRequest(
        run_id=run_id,
        principal=principal,
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": user_prompt},
        workspace_id=workspace_id,
        company_id=company_id,
        conversation_id=conversation_id,
    )

    try:
        run_result = await plane.kernel.run(req, spec)

        if run_result.status == RunStatus.COMPLETED:
            output_text = str(run_result.final_output.get("response", run_result.final_output)) if isinstance(run_result.final_output, dict) else str(run_result.final_output or "")

            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="message.delta",
                payload={"delta": output_text},
            )

            # Persist assistant message
            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content=output_text,
                run_id=run_id,
                status_="completed",
            )

            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.completed",
                payload={"output": output_text, "status": "COMPLETED"},
            )

        elif run_result.status == RunStatus.WAITING_APPROVAL:
            wait_desc = run_result.interruptions_waits[0] if run_result.interruptions_waits else None
            appr_id = wait_desc.related_ref if wait_desc else None
            ckpt_ref = wait_desc.checkpoint_ref if wait_desc else None

            # checkpoint_ref/approval_id không cần cache riêng — đã durable trong
            # agent_core.approvals (RunApprovalRecord.checkpoint_ref), tra cứu lại
            # qua plane.repository/plane.approval_service khi cần resume (xem decide_approval).
            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="approval.required",
                payload={
                    "approval_id": appr_id,
                    "checkpoint_ref": ckpt_ref,
                    "reason": wait_desc.reason if wait_desc else "Approval required",
                },
            )

        else:
            err_msg = run_result.errors[0] if run_result.errors else "Run failed"
            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content=f"Error: {err_msg}",
                run_id=run_id,
                status_="failed",
            )
            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": err_msg},
            )

    except Exception as exc:
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content=f"Unexpected error: {str(exc)}",
            run_id=run_id,
            status_="failed",
        )
        stream_mgr.emit(
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": str(exc)},
        )


# 5. POST /agent/conversations/{conversation_id}/messages
@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_message(
    conversation_id: str,
    req: MessageCreate,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane()
    conv = await plane.conversation_repository.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    _ensure_conversation_tenant_match(conv, identity)

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

    asyncio.create_task(
        _execute_canonical_run_task(
            run_id=run_id,
            conversation_id=conversation_id,
            user_prompt=req.content,
            agent_profile=agent_profile,
            plane=plane,
            stream_mgr=stream_mgr,
            principal=identity.principal_id,
            workspace_id=identity.workspace_id,
            company_id=identity.company_id,
        )
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
    run_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane()
    stream_mgr = get_cosa_event_stream_manager()

    await _get_owned_run_or_404(plane, run_id, identity)
    await plane.kernel.cancel(run_id)

    stream_mgr.emit(
        run_id=run_id,
        conversation_id="unknown",
        event_type="run.cancelled",
        payload={"run_id": run_id},
    )

    return CancelRunResponse(run_id=run_id, status="CANCELLED")


# 7. POST /agent/approvals/{approval_id}/decision
@router.post("/approvals/{approval_id}/decision", response_model=ApprovalDecisionResponse)
async def decide_approval(
    approval_id: str,
    req: ApprovalDecisionRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = get_cosa_plane()
    stream_mgr = get_cosa_event_stream_manager()

    # Tenant check TRƯỚC khi cho phép quyết định — approval_id không tự mang
    # tenant scope, phải tra run liên kết trước (theo COSA_FINAL_INTEGRATION_
    # AND_LEGACY_EXIT_PLAN_2026-08-25.md §29: reviewer identity từ authenticated
    # context, không phải "user:reviewer" hardcode).
    existing_approval = await plane.approval_service.get_approval(approval_id)
    if existing_approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval not found: {approval_id}")
    await _get_owned_run_or_404(plane, existing_approval.run_id, identity)

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
    run_record = await plane.repository.get_run(run_id)
    resume_conversation_id = run_record.conversation_id if run_record and run_record.conversation_id else "unknown"

    stream_mgr.emit(
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
    # durable (agent_core.approvals.checkpoint_ref), không cần cache in-memory riêng.
    if req.approved and decided.checkpoint_ref:
        ckpt_ref = decided.checkpoint_ref

        async def do_resume():
            res = await plane.kernel.resume(
                run_id=run_id,
                checkpoint_ref=ckpt_ref,
                updates={"approved": True},
            )
            if res.status == RunStatus.COMPLETED:
                output_text = str(res.final_output.get("response", res.final_output)) if isinstance(res.final_output, dict) else str(res.final_output or "")

                if resume_conversation_id != "unknown":
                    await _append_message(
                        plane,
                        conversation_id=resume_conversation_id,
                        role="assistant",
                        content=output_text,
                        run_id=run_id,
                        status_="completed",
                    )

                stream_mgr.emit(
                    run_id=run_id,
                    conversation_id=resume_conversation_id,
                    event_type="message.delta",
                    payload={"delta": output_text},
                )

                stream_mgr.emit(
                    run_id=run_id,
                    conversation_id=resume_conversation_id,
                    event_type="run.completed",
                    payload={"output": output_text, "status": "COMPLETED"},
                )

        asyncio.create_task(do_resume())

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
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    # LƯU Ý CHƯA ĐỦ AN TOÀN: list_pending_approvals chỉ filter theo
    # workspace_id, không join sang company_id — nếu 2 company khác nhau vô
    # tình dùng cùng workspace_id (không nên xảy ra theo thiết kế hiện tại,
    # nhưng chưa có ràng buộc DB-level nào chặn) thì việc lọc ở đây chưa đủ.
    # Theo dõi ở COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §29.
    plane = get_cosa_plane()
    pending = await plane.approval_service.list_pending_approvals(workspace_id=identity.workspace_id)
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
    run_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    since_sequence: Optional[int] = Query(None),
    last_event_id: Optional[int] = Header(None, alias="Last-Event-ID"),
):
    plane = get_cosa_plane()
    await _get_owned_run_or_404(plane, run_id, identity)

    stream_mgr = get_cosa_event_stream_manager()
    effective_sequence = since_sequence if since_sequence is not None else last_event_id

    return StreamingResponse(
        stream_mgr.stream_events(run_id, since_sequence=effective_sequence),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def create_cosa_router() -> APIRouter:
    return router
