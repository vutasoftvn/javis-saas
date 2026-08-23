from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from agentos.api.auth import TenantContext, get_tenant_context
from agentos.api.chat.event_stream import (
    ChatEvent,
    RunEventStreamManager,
    get_event_stream_manager,
)
from agentos.api.chat.schemas import (
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
from agentos.api.db.repository import ChatRepository
from agentos.api.db.session import get_db_session
from agentos.core.approval import ApprovalNotFoundError
from agentos.core.factory import build_cosa_agent_plane
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.runtime import AgentRuntime

router = APIRouter(prefix="/agent", tags=["agent-chat"])

# Runtime instance provider (overridable for testing)
_runtime_instance: Optional[AgentRuntime] = None


def get_agent_runtime() -> AgentRuntime:
    global _runtime_instance
    if _runtime_instance is None:
        _runtime_instance = build_cosa_agent_plane()
    return _runtime_instance


def set_agent_runtime(runtime: Optional[AgentRuntime]) -> None:
    global _runtime_instance
    _runtime_instance = runtime


def _conversation_to_response(conv, repo: ChatRepository) -> ConversationResponse:
    messages = repo.list_messages(conv.id)
    msg_responses = []
    for msg in messages:
        att_responses = [
            MessageAttachmentResponse(
                id=att.id,
                message_id=att.message_id,
                object_ref=att.object_ref,
                media_type=att.media_type,
                file_name=att.file_name,
                size=att.size,
                checksum=att.checksum,
                knowledge_ingest_status=att.knowledge_ingest_status,
            )
            for att in (msg.attachments or [])
        ]
        msg_responses.append(
            MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                role=msg.role,
                content=msg.content,
                run_id=msg.run_id,
                parent_message_id=msg.parent_message_id,
                status=msg.status,
                created_at=msg.created_at,
                attachments=att_responses,
            )
        )

    return ConversationResponse(
        id=conv.id,
        company_id=conv.company_id,
        workspace_id=conv.workspace_id,
        created_by_principal=conv.created_by_principal,
        title=conv.title,
        active_agent_profile=conv.active_agent_profile,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        archived_at=conv.archived_at,
        messages=msg_responses,
    )


# 1. POST /agent/conversations
@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    req: ConversationCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db_session),
):
    repo = ChatRepository(db)
    active_profile = req.agent_profile_id or req.active_agent_profile or "co-founder"
    conv = repo.create_conversation(
        company_id=tenant.company_id,
        workspace_id=tenant.workspace_id,
        created_by_principal=f"user:{tenant.user_id}",
        title=req.title or "New Conversation",
        active_agent_profile=active_profile,
    )
    return _conversation_to_response(conv, repo)


# 2. GET /agent/conversations
@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    include_archived: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db_session),
):
    repo = ChatRepository(db)
    items = repo.list_conversations(
        company_id=tenant.company_id,
        workspace_id=tenant.workspace_id,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    responses = [_conversation_to_response(c, repo) for c in items]
    return ConversationListResponse(items=responses, total=len(responses))


# 3. GET /agent/conversations/{conversation_id}
@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db_session),
):
    repo = ChatRepository(db)
    conv = repo.get_conversation(
        conversation_id, company_id=tenant.company_id, workspace_id=tenant.workspace_id
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied",
        )
    return _conversation_to_response(conv, repo)


# 4. PATCH /agent/conversations/{conversation_id}
@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    req: ConversationUpdate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db_session),
):
    repo = ChatRepository(db)
    active_profile = req.agent_profile_id or req.active_agent_profile
    conv = repo.update_conversation(
        conversation_id,
        company_id=tenant.company_id,
        workspace_id=tenant.workspace_id,
        title=req.title,
        active_agent_profile=active_profile,
        archived=req.archived,
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied",
        )
    return _conversation_to_response(conv, repo)


_pending_runs: dict[str, dict[str, Any]] = {}


async def _run_agent_task(
    run_id: str,
    conversation_id: str,
    user_goal: str,
    tenant: TenantContext,
    agent_key: str,
    db: Session,
    runtime: AgentRuntime,
    stream_mgr: RunEventStreamManager,
):
    repo = ChatRepository(db)
    _pending_runs[run_id] = {
        "run_id": run_id,
        "conversation_id": conversation_id,
        "user_goal": user_goal,
        "tenant": tenant,
        "agent_key": agent_key,
    }

    def persist_event(ev: ChatEvent):
        repo.save_run_event(
            run_id=ev.run_id,
            sequence=ev.sequence,
            event_type=ev.event_type,
            payload=ev.payload,
        )

    def emit_tool_event(event_type: str, payload: dict) -> None:
        # Bridges Executor's live tool-call lifecycle (agentos/core/executor.py)
        # into the SSE contract (§17.1.2): tool.requested/started/completed/failed.
        stream_mgr.emit(
            run_id=run_id,
            conversation_id=conversation_id,
            event_type=event_type,
            payload=payload,
            correlation_id=tenant.correlation_id,
            on_event_persisted=persist_event,
        )

    # 1. run.started
    stream_mgr.emit(
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="run.started",
        payload={"run_id": run_id, "conversation_id": conversation_id, "goal": user_goal},
        correlation_id=tenant.correlation_id,
        on_event_persisted=persist_event,
    )

    # 2. reasoning.status
    stream_mgr.emit(
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="reasoning.status",
        payload={"status": "thinking"},
        correlation_id=tenant.correlation_id,
        on_event_persisted=persist_event,
    )

    # 3. message.started
    stream_mgr.emit(
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="message.started",
        payload={"role": "assistant"},
        correlation_id=tenant.correlation_id,
        on_event_persisted=persist_event,
    )

    # Build context with recent conversation turns
    past_messages = repo.list_messages(conversation_id, limit=20)
    history = [{"role": m.role, "content": m.content} for m in past_messages]

    # Resolve Agent Profile if available
    profile = None
    if hasattr(runtime, "_profile_registry") and runtime._profile_registry is not None:
        if runtime._profile_registry.has(agent_key):
            profile = runtime._profile_registry.get(agent_key)
        elif runtime._profile_registry.list():
            profile = runtime._profile_registry.get_default()

    task_metadata: dict[str, Any] = {
        "conversation_id": conversation_id,
        "run_id": run_id,
        "conversation_messages": history,
        "history": history,
    }
    if profile:
        agent_perm_level = profile.permission_level
        task_metadata["allowed_skills"] = profile.skills
        task_metadata["allowed_tools"] = profile.tools_allow
        task_metadata["mission"] = profile.mission
        task_metadata["max_tool_calls"] = profile.max_tool_calls
        task_metadata["max_runtime_seconds"] = profile.max_runtime_seconds
        task_metadata["preferred_runtime"] = profile.preferred_runtime
        task_metadata["agent_profile_id"] = profile.id
    else:
        agent_perm_level = tenant.to_agent_permission_level()

    task = TaskContext(
        goal=user_goal,
        agent_key=profile.id if profile else agent_key,
        workspace_id=tenant.workspace_id,
        company_id=tenant.company_id,
        user_id=tenant.user_id,
        workforce_member_id=tenant.workforce_member_id,
        role=tenant.membership_role,
        agent_permission_level=agent_perm_level,
        correlation_id=tenant.correlation_id,
        metadata=task_metadata,
    )


    try:
        result = await runtime.run(task, on_tool_event=emit_tool_event)

        if result.status == AgentRunStatus.COMPLETED:
            # Emit delta
            output_text = result.output or ""
            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="message.delta",
                payload={"delta": output_text},
                correlation_id=tenant.correlation_id,
                on_event_persisted=persist_event,
            )

            # citation — structured provenance from ContextBuilder's knowledge_citations (Phase 7D)
            knowledge_citations = getattr(runtime.last_context, "knowledge_citations", None) or []
            if knowledge_citations:
                for citation in knowledge_citations:
                    payload = {
                        "chunk_id": citation.chunk_id,
                        "source_id": citation.source_id,
                        "source_title": citation.source_title,
                        "source_uri": citation.source_uri,
                        "text": citation.chunk_text,
                        "page_or_section": citation.page_or_section,
                        "score": citation.similarity_score,
                    }
                    stream_mgr.emit(
                        run_id=run_id,
                        conversation_id=conversation_id,
                        event_type="citation",
                        payload=payload,
                        correlation_id=tenant.correlation_id,
                        on_event_persisted=persist_event,
                    )
            else:
                knowledge_snippets = getattr(runtime.last_context, "knowledge_snippets", None) or []
                for snippet in knowledge_snippets:
                    stream_mgr.emit(
                        run_id=run_id,
                        conversation_id=conversation_id,
                        event_type="citation",
                        payload={"text": snippet},
                        correlation_id=tenant.correlation_id,
                        on_event_persisted=persist_event,
                    )

            # Save assistant message
            repo.create_message(
                conversation_id=conversation_id,
                role="assistant",
                content=output_text,
                run_id=run_id,
                status="completed",
            )
            # run.completed
            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.completed",
                payload={"output": output_text, "tool_calls_made": result.tool_calls_made},
                correlation_id=tenant.correlation_id,
                on_event_persisted=persist_event,
            )

        elif result.status in (AgentRunStatus.WAITING_APPROVAL, AgentRunStatus.PAUSED):
            approval_meta = {}
            if result.approval_id and hasattr(runtime, "_approval_service") and runtime._approval_service is not None:
                try:
                    appr_obj = runtime._approval_service.get(result.approval_id)
                    approval_meta = {
                        "tool_name": appr_obj.tool_name or appr_obj.action,
                        "action": appr_obj.action,
                        "checkpoint_index": appr_obj.checkpoint_index,
                    }
                except Exception:
                    pass
            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="approval.required",
                payload={"approval_id": result.approval_id, "error": result.error, **approval_meta},
                correlation_id=tenant.correlation_id,
                on_event_persisted=persist_event,
            )

        else:
            # FAILED
            err_msg = result.error or "Run failed"
            repo.create_message(
                conversation_id=conversation_id,
                role="assistant",
                content=f"Error: {err_msg}",
                run_id=run_id,
                status="failed",
            )
            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": err_msg},
                correlation_id=tenant.correlation_id,
                on_event_persisted=persist_event,
            )

    except Exception as exc:
        repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content=f"Unexpected error: {str(exc)}",
            run_id=run_id,
            status="failed",
        )
        stream_mgr.emit(
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": str(exc)},
            correlation_id=tenant.correlation_id,
            on_event_persisted=persist_event,
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
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db_session),
):
    repo = ChatRepository(db)
    conv = repo.get_conversation(
        conversation_id, company_id=tenant.company_id, workspace_id=tenant.workspace_id
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied",
        )

    run_id = str(uuid.uuid4())
    runtime = get_agent_runtime()
    stream_mgr = get_event_stream_manager()
    stream_mgr.start_run(run_id)

    def persist_event(ev: ChatEvent):
        repo.save_run_event(
            run_id=ev.run_id,
            sequence=ev.sequence,
            event_type=ev.event_type,
            payload=ev.payload,
        )

    # Save user message
    user_msg = repo.create_message(
        conversation_id=conversation_id,
        role=req.role or "user",
        content=req.content,
        run_id=run_id,
        parent_message_id=req.parent_message_id,
        status="completed",
    )

    # Save attachments if any
    if req.attachments:
        for att in req.attachments:
            attachment = repo.create_attachment(
                message_id=user_msg.id,
                object_ref=att.object_ref,
                media_type=att.media_type,
                file_name=att.file_name,
                size=att.size,
                checksum=att.checksum,
            )
            # attachment.processed — emitted synchronously here (not in the
            # background task) since attachment persistence is already done
            # by the time this handler returns 202.
            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="attachment.processed",
                payload={
                    "attachment_id": attachment.id,
                    "file_name": attachment.file_name,
                    "media_type": attachment.media_type,
                    "knowledge_ingest_status": attachment.knowledge_ingest_status,
                },
                correlation_id=tenant.correlation_id,
                on_event_persisted=persist_event,
            )

    # Start background execution
    agent_key = conv.active_agent_profile or "founder_assistant"
    asyncio.create_task(
        _run_agent_task(
            run_id=run_id,
            conversation_id=conversation_id,
            user_goal=req.content,
            tenant=tenant,
            agent_key=agent_key,
            db=db,
            runtime=runtime,
            stream_mgr=stream_mgr,
        )
    )

    return RunResponse(
        run_id=run_id,
        conversation_id=conversation_id,
        status="RUNNING",
        message_id=user_msg.id,
    )


# 6. POST /agent/runs/{run_id}/cancel
@router.post("/runs/{run_id}/cancel", response_model=CancelRunResponse)
async def cancel_run(
    run_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db_session),
):
    stream_mgr = get_event_stream_manager()
    repo = ChatRepository(db)

    stream_mgr.emit(
        run_id=run_id,
        conversation_id="unknown",
        event_type="run.cancelled",
        payload={"run_id": run_id, "cancelled_by": f"user:{tenant.user_id}"},
        correlation_id=tenant.correlation_id,
        on_event_persisted=lambda ev: repo.save_run_event(
            run_id=ev.run_id,
            sequence=ev.sequence,
            event_type=ev.event_type,
            payload=ev.payload,
        ),
    )

    return CancelRunResponse(run_id=run_id, status="CANCELLED")


# 7. POST /agent/approvals/{approval_id}/decision
@router.post("/approvals/{approval_id}/decision", response_model=ApprovalDecisionResponse)
async def decide_approval(
    approval_id: str,
    req: ApprovalDecisionRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db_session),
):
    runtime = get_agent_runtime()
    repo = ChatRepository(db)
    stream_mgr = get_event_stream_manager()

    try:
        approval = runtime._approval_service.decide(
            approval_id,
            reviewer=f"user:{tenant.user_id}",
            approved=req.approved,
            reason=req.reason,
        )
    except ApprovalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval not found: {approval_id}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Emit approval.resolved event
    if approval.run_id:
        pending = _pending_runs.get(approval.run_id)
        # Giữ correlation_id gốc của run bị pause (roadmap §8a.3: correlation_id phải
        # giữ nguyên xuyên suốt trước/trong/sau resume, không lấy correlation_id của
        # request quyết định approval — có thể do 1 người review khác gửi tới).
        resolved_correlation_id = approval.correlation_id or tenant.correlation_id
        stream_mgr.emit(
            run_id=approval.run_id,
            conversation_id=pending["conversation_id"] if pending else "unknown",
            event_type="approval.resolved",
            payload={
                "approval_id": approval_id,
                "status": approval.status.value,
                "reviewer": f"user:{tenant.user_id}",
                "reason": req.reason,
            },
            correlation_id=resolved_correlation_id,
            on_event_persisted=lambda ev: repo.save_run_event(
                run_id=ev.run_id,
                sequence=ev.sequence,
                event_type=ev.event_type,
                payload=ev.payload,
            ),
        )

        if pending:
            if req.approved:
                # Resume execution with the exact same run_id
                asyncio.create_task(
                    _run_agent_task(
                        run_id=approval.run_id,
                        conversation_id=pending["conversation_id"],
                        user_goal=pending["user_goal"],
                        tenant=pending["tenant"],
                        agent_key=pending["agent_key"],
                        db=db,
                        runtime=runtime,
                        stream_mgr=stream_mgr,
                    )
                )
            else:
                _pending_runs.pop(approval.run_id, None)
                stream_mgr.emit(
                    run_id=approval.run_id,
                    conversation_id=pending["conversation_id"],
                    event_type="run.failed",
                    payload={"error": f"Tool call was rejected: {req.reason or 'User denied'}"},
                    correlation_id=resolved_correlation_id,
                    on_event_persisted=lambda ev: repo.save_run_event(
                        run_id=ev.run_id,
                        sequence=ev.sequence,
                        event_type=ev.event_type,
                        payload=ev.payload,
                    ),
                )
                repo.create_message(
                    conversation_id=pending["conversation_id"],
                    role="assistant",
                    content=f"Yêu cầu thực thi bị từ chối: {req.reason or 'User denied'}",
                    run_id=approval.run_id,
                    status="failed",
                )

    return ApprovalDecisionResponse(
        approval_id=approval.id,
        run_id=approval.run_id,
        status=approval.status.value,
        reviewer=approval.reviewer or f"user:{tenant.user_id}",
        reason=approval.reason,
        decided_at=approval.decided_at or datetime.now(timezone.utc),
    )



# 8. GET /agent/runs/{run_id}/events
@router.get("/runs/{run_id}/events")
async def get_run_events(
    run_id: str,
    since_sequence: Optional[int] = Query(None),
    last_event_id: Optional[int] = Header(None, alias="Last-Event-ID"),
    tenant: TenantContext = Depends(get_tenant_context),
):
    stream_mgr = get_event_stream_manager()
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
