from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from agent_core.contracts.identity import InvocationIdentity
from agent_core.contracts.run import RunRequest, RunStatus
from apps.cosa.agents.specs import COSA_FINANCE_AGENT_SPEC, COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.api.event_stream import (
    CosaEventStreamManager,
    get_cosa_event_stream_manager,
)
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

# In-memory storage for conversations/messages in API layer
_conversations: dict[str, dict[str, Any]] = {}
_messages: dict[str, list[dict[str, Any]]] = {}
_pending_runs: dict[str, dict[str, Any]] = {}

_plane_instance: Optional[CosaAgentPlane] = None


def get_cosa_plane() -> CosaAgentPlane:
    global _plane_instance
    if _plane_instance is None:
        _plane_instance = build_cosa_agent_plane()
    return _plane_instance


def set_cosa_plane(plane: Optional[CosaAgentPlane]) -> None:
    global _plane_instance
    _plane_instance = plane


def _conv_to_response(conv_id: str) -> ConversationResponse:
    conv = _conversations[conv_id]
    msg_list = _messages.get(conv_id, [])
    msg_responses = [
        MessageResponse(
            id=m["id"],
            conversation_id=conv_id,
            role=m["role"],
            content=m["content"],
            run_id=m.get("run_id"),
            parent_message_id=m.get("parent_message_id"),
            status=m.get("status", "completed"),
            created_at=m.get("created_at", datetime.now(timezone.utc)),
            attachments=[
                MessageAttachmentResponse(
                    id=att["id"],
                    message_id=m["id"],
                    object_ref=att["object_ref"],
                    media_type=att["media_type"],
                    file_name=att["file_name"],
                    size=att.get("size", 0),
                    checksum=att.get("checksum"),
                    knowledge_ingest_status=att.get("knowledge_ingest_status", "COMPLETED"),
                )
                for att in m.get("attachments", [])
            ],
        )
        for m in msg_list
    ]

    return ConversationResponse(
        id=conv["id"],
        company_id=conv.get("company_id", "company_1"),
        workspace_id=conv.get("workspace_id", "ws_1"),
        created_by_principal=conv.get("created_by_principal", "user:default"),
        title=conv.get("title", "New Conversation"),
        active_agent_profile=conv.get("active_agent_profile", "operations"),
        created_at=conv.get("created_at", datetime.now(timezone.utc)),
        updated_at=conv.get("updated_at", datetime.now(timezone.utc)),
        archived_at=conv.get("archived_at"),
        messages=msg_responses,
    )


# 1. POST /agent/conversations
@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    req: ConversationCreate,
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
    x_company_id: Optional[str] = Header(None, alias="X-Company-Id"),
):
    conv_id = f"conv_{uuid.uuid4().hex[:12]}"
    active_profile = req.agent_profile_id or req.active_agent_profile or "operations"
    now = datetime.now(timezone.utc)

    _conversations[conv_id] = {
        "id": conv_id,
        "company_id": x_company_id or "company_1",
        "workspace_id": x_workspace_id or "ws_1",
        "created_by_principal": "user:default",
        "title": req.title or "New Conversation",
        "active_agent_profile": active_profile,
        "created_at": now,
        "updated_at": now,
        "archived_at": None,
    }
    _messages[conv_id] = []
    return _conv_to_response(conv_id)


# 2. GET /agent/conversations
@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    include_archived: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    items = []
    for conv_id, conv in list(_conversations.items()):
        if not include_archived and conv.get("archived_at") is not None:
            continue
        items.append(_conv_to_response(conv_id))

    paginated = items[offset : offset + limit]
    return ConversationListResponse(items=paginated, total=len(items))


# 3. GET /agent/conversations/{conversation_id}
@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    if conversation_id not in _conversations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return _conv_to_response(conversation_id)


# 4. PATCH /agent/conversations/{conversation_id}
@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(conversation_id: str, req: ConversationUpdate):
    if conversation_id not in _conversations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    conv = _conversations[conversation_id]
    if req.title is not None:
        conv["title"] = req.title
    if req.active_agent_profile is not None or req.agent_profile_id is not None:
        conv["active_agent_profile"] = req.agent_profile_id or req.active_agent_profile
    if req.archived is not None:
        conv["archived_at"] = datetime.now(timezone.utc) if req.archived else None
    conv["updated_at"] = datetime.now(timezone.utc)
    return _conv_to_response(conversation_id)


async def _execute_canonical_run_task(
    *,
    run_id: str,
    conversation_id: str,
    user_prompt: str,
    agent_profile: str,
    plane: CosaAgentPlane,
    stream_mgr: CosaEventStreamManager,
    workspace_id: str = "1",
    company_id: str = "1",
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
        principal="user:default",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": user_prompt},
        workspace_id=workspace_id,
        company_id=company_id,
    )

    _pending_runs[run_id] = {
        "run_id": run_id,
        "conversation_id": conversation_id,
        "user_prompt": user_prompt,
        "agent_profile": agent_profile,
        "spec": spec,
        "workspace_id": workspace_id,
        "company_id": company_id,
    }

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
            _messages.setdefault(conversation_id, []).append({
                "id": f"msg_{uuid.uuid4().hex[:12]}",
                "role": "assistant",
                "content": output_text,
                "run_id": run_id,
                "status": "completed",
                "created_at": datetime.now(timezone.utc),
            })

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

            _pending_runs[run_id]["checkpoint_ref"] = ckpt_ref
            _pending_runs[run_id]["approval_id"] = appr_id

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
            _messages.setdefault(conversation_id, []).append({
                "id": f"msg_{uuid.uuid4().hex[:12]}",
                "role": "assistant",
                "content": f"Error: {err_msg}",
                "run_id": run_id,
                "status": "failed",
                "created_at": datetime.now(timezone.utc),
            })
            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": err_msg},
            )


    except Exception as exc:
        _messages.setdefault(conversation_id, []).append({
            "id": f"msg_{uuid.uuid4().hex[:12]}",
            "role": "assistant",
            "content": f"Unexpected error: {str(exc)}",
            "run_id": run_id,
            "status": "failed",
            "created_at": datetime.now(timezone.utc),
        })
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
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
    x_company_id: Optional[str] = Header(None, alias="X-Company-Id"),
):
    if conversation_id not in _conversations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    run_id = f"run_{uuid.uuid4().hex[:16]}"
    plane = get_cosa_plane()
    stream_mgr = get_cosa_event_stream_manager()
    stream_mgr.start_run(run_id)

    # Save user message
    user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    _messages.setdefault(conversation_id, []).append({
        "id": user_msg_id,
        "role": req.role or "user",
        "content": req.content,
        "run_id": run_id,
        "parent_message_id": req.parent_message_id,
        "status": "completed",
        "created_at": datetime.now(timezone.utc),
        "attachments": [a.model_dump() for a in (req.attachments or [])],
    })

    conv = _conversations[conversation_id]
    agent_profile = conv.get("active_agent_profile", "operations")

    asyncio.create_task(
        _execute_canonical_run_task(
            run_id=run_id,
            conversation_id=conversation_id,
            user_prompt=req.content,
            agent_profile=agent_profile,
            plane=plane,
            stream_mgr=stream_mgr,
            workspace_id=x_workspace_id or "1",
            company_id=x_company_id or "1",
        )
    )

    return RunResponse(
        run_id=run_id,
        conversation_id=conversation_id,
        status="RUNNING",
        message_id=user_msg_id,
    )


# 6. POST /agent/runs/{run_id}/cancel
@router.post("/runs/{run_id}/cancel", response_model=CancelRunResponse)
async def cancel_run(run_id: str):
    plane = get_cosa_plane()
    stream_mgr = get_cosa_event_stream_manager()

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
async def decide_approval(approval_id: str, req: ApprovalDecisionRequest):
    plane = get_cosa_plane()
    stream_mgr = get_cosa_event_stream_manager()

    decided = await plane.approval_service.submit_decision(
        approval_id=approval_id,
        reviewer="user:reviewer",
        approved=req.approved,
        reason=req.reason or "",
    )

    if not decided:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval not found: {approval_id}")

    run_id = decided.run_id
    stream_mgr.emit(
        run_id=run_id,
        conversation_id="unknown",
        event_type="approval.resolved",
        payload={
            "approval_id": approval_id,
            "status": decided.status,
            "reviewer": decided.reviewer,
            "reason": decided.reason,
        },
    )

    # Resume kernel if approved
    if req.approved and run_id in _pending_runs:
        pending = _pending_runs[run_id]
        ckpt_ref = pending.get("checkpoint_ref")
        if ckpt_ref:
            async def do_resume():
                res = await plane.kernel.resume(
                    run_id=run_id,
                    checkpoint_ref=ckpt_ref,
                    updates={"approved": True},
                )
                if res.status == RunStatus.COMPLETED:
                    output_text = str(res.final_output.get("response", res.final_output)) if isinstance(res.final_output, dict) else str(res.final_output or "")
                    stream_mgr.emit(
                        run_id=run_id,
                        conversation_id=pending["conversation_id"],
                        event_type="message.delta",
                        payload={"delta": output_text},
                    )

                    stream_mgr.emit(
                        run_id=run_id,
                        conversation_id=pending["conversation_id"],
                        event_type="run.completed",
                        payload={"output": output_text, "status": "COMPLETED"},
                    )

            asyncio.create_task(do_resume())

    return ApprovalDecisionResponse(
        approval_id=decided.approval_id,
        run_id=decided.run_id,
        status=decided.status,
        reviewer=decided.reviewer or "user:reviewer",
        reason=decided.reason,
        decided_at=decided.decided_at or datetime.now(timezone.utc),
    )


# 7.1 GET /agent/approvals
@router.get("/approvals")
async def list_approvals(
    status_filter: Optional[str] = Query(None, alias="status"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
):
    plane = get_cosa_plane()
    pending = await plane.approval_service.list_pending_approvals(workspace_id=x_workspace_id)
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
    since_sequence: Optional[int] = Query(None),
    last_event_id: Optional[int] = Header(None, alias="Last-Event-ID"),
):
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
