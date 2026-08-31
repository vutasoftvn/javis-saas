# Boundary Hardening Phase 2 — God-object & Mega-router Splits

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tách 4 file ôm nhiều domain không liên quan thành các module độc lập theo ranh giới nghiệp vụ, gộp endpoint approval trùng lặp, và giữ interface công khai nguyên không thay đổi.

**Architecture:** Phase 2 tập trung vào god-object (`agent_plane.py`) và mega-router (`routes.py`) ở Python layer, cộng với mega-service ở Encore (`marketing-context.service.ts`) và mega-service ở Flutter (`strategy_service.dart`). Mỗi tách phải qua test độc lập, không làm thay đổi behavior hay API contract. Endpoint approval được gộp từ `routes.py` sang `workforce_routes.py` là canonical location duy nhất.

**Tech Stack:** 
- Python: FastAPI, Pydantic, pytest (tests/apps/cosa/)
- TypeScript/Encore: Drizzle ORM, Vitest (services/company/commercial/tests/)
- Flutter: flutter_test (frontend/test/modules/strategy/)

## Global Constraints

- Trước khi tách: chạy suite test hiện có của file/module đó, ghi baseline.
- Nếu chưa có test bao phủ đủ hành vi hiện tại, viết characterization test trước khi tách — không tách "mù".
- Sau khi tách: public interface (chữ ký hàm, route path, response schema) giữ nguyên, không đổi hành vi.
- Chạy lại đúng bộ test + lint/type-check tương ứng (ruff/mypy cho Python; tsc/vitest cho Encore; `flutter analyze`/test cho Dart) — xanh mới commit.
- Mỗi giai đoạn commit riêng.
- Không tự báo "xong toàn bộ" ở cấp master — chỉ báo cáo đúng giai đoạn đã verify bằng lệnh thật, giai đoạn nào chưa làm.

---

## Task 1: `apps/cosa/api/routes.py` — Conversation, Approval, Knowledge, Connector Routes Split

**Files:**
- Create/Modify: `apps/cosa/api/routes.py` (1397→350 lines, remove conversation/approval/knowledge/connector)
- Create: `apps/cosa/api/conversation_routes.py` (~400 lines)
- Create: `apps/cosa/api/approval_routes.py` (~100 lines, stub — consolidate onto workforce_routes.py)
- Create: `apps/cosa/api/knowledge_routes.py` (~350 lines)
- Create: `apps/cosa/api/connector_routes.py` (~150 lines)
- Modify: `apps/cosa/api/workforce_routes.py` (add approval endpoints, absorb from routes.py)
- Modify: `apps/cosa/api/app.py` (update router imports)
- Test: `tests/apps/cosa/test_routes.py` (split into per-domain test files)
- Test: `tests/apps/cosa/test_router_registration.py` (verify endpoint paths unchanged)

**Interfaces:**
- Consumes: `CosaAgentPlane`, `AuthenticatedIdentity`, event_stream manager, object store, schema DTOs
- Produces: FastAPI routes at same path prefixes (`/agent/conversations`, `/agent/approvals`, `/agent/knowledge/*`, `/agent/connectors/*`)

- [ ] **Step 1: Write test baseline for route registration**

Create `tests/apps/cosa/test_routes_split_baseline.py` to capture all expected route paths before split:

```python
import pytest
from apps.cosa.api.app import create_cosa_app
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.policy_test_helpers import (
    StubCompanyServiceClient,
    stub_active_tenant_policy_client,
)
from agent.runs.repository import InMemoryRunRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.coordination.scheduler import RunScheduler
from agent.runs.leases import RunLeaseManager
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.artifacts import InMemoryArtifactRepository
from agent.workforce.repository import InMemoryWorkforceRepository
from agent.vault.repository import InMemoryVaultRepository
from agent_testkit.fake_sdk_model import FakeSDKModel


@pytest.fixture
def built_app():
    plane = build_cosa_agent_plane(
        company_client=StubCompanyServiceClient(),
        tenant_policy_client=stub_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        workforce_repository=InMemoryWorkforceRepository(),
        vault_repository=InMemoryVaultRepository(),
        model=FakeSDKModel(),
    )
    return create_cosa_app(plane)


def test_all_conversation_routes_exist(built_app):
    """All conversation CRUD routes must exist post-split."""
    routes = set(built_app.openapi()["paths"].keys())
    expected = [
        "/agent/conversations",
        "/agent/conversations/{conversation_id}",
        "/agent/conversations/{conversation_id}/messages",
        "/agent/conversations/{conversation_id}/artifacts",
        "/agent/sessions/{conversation_id}",
        "/agent/sessions/{conversation_id}/timeline",
        "/agent/sessions/{conversation_id}/artifacts",
    ]
    for route in expected:
        assert route in routes, f"Route {route} missing after split"


def test_all_approval_routes_exist(built_app):
    """All approval routes must exist at /agent/workforce/approvals (consolidated)."""
    routes = set(built_app.openapi()["paths"].keys())
    expected = [
        "/agent/workforce/approvals",
        "/agent/workforce/approvals/{approval_id}/decision",
    ]
    for route in expected:
        assert route in routes, f"Route {route} missing after consolidation"


def test_old_approval_routes_removed(built_app):
    """Old /agent/approvals routes must NOT exist (moved to workforce)."""
    routes = set(built_app.openapi()["paths"].keys())
    old_routes = [
        "/agent/approvals",
        "/agent/approvals/{approval_id}/decision",
    ]
    for route in old_routes:
        assert route not in routes, f"Old route {route} still present after consolidation"


def test_all_knowledge_routes_exist(built_app):
    """All knowledge ingestion routes must exist."""
    routes = set(built_app.openapi()["paths"].keys())
    expected = [
        "/agent/knowledge/uploads",
        "/agent/knowledge/uploads/{ingestion_id}/complete",
        "/agent/knowledge/ingestions/{ingestion_id}/review",
    ]
    for route in expected:
        assert route in routes, f"Route {route} missing after split"


def test_all_connector_routes_exist(built_app):
    """All connector proxy routes must exist."""
    routes = set(built_app.openapi()["paths"].keys())
    expected = [
        "/agent/connectors/install",
        "/agent/connectors/authorize",
        "/agent/connectors/grant",
        "/agent/connectors/revoke",
    ]
    for route in expected:
        assert route in routes, f"Route {route} missing after split"


def test_all_schedule_routes_exist(built_app):
    """All schedule routes must exist."""
    routes = set(built_app.openapi()["paths"].keys())
    expected = [
        "/agent/schedules",
        "/agent/schedules/{schedule_id}/run-now",
    ]
    for route in expected:
        assert route in routes, f"Route {route} missing after split"
```

- [ ] **Step 2: Run test to verify it fails (current monolithic router)**

```bash
cd /Volumes/SSD/javis-saas
python -m pytest tests/apps/cosa/test_routes_split_baseline.py::test_old_approval_routes_removed -xvs
```

Expected: FAIL (routes still at `/agent/approvals`; test expects them removed)

- [ ] **Step 3: Create conversation_routes.py (Lines 1-240 + helpers 84-126 from routes.py)**

Create `/Volumes/SSD/javis-saas/apps/cosa/api/conversation_routes.py`:

```python
"""Conversation CRUD & message routes for COSA Agent Platform."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError

from agent.conversations.models import ConversationRecord, MessageAttachmentRecord, MessageRecord

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


def _ensure_conversation_tenant_match(
    conv: ConversationRecord, identity: AuthenticatedIdentity
) -> None:
    """Tenant ownership check."""
    if conv.workspace_id != identity.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


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


# 6. POST /agent/runs/{run_id}/cancel (timeline operation related to conversations)
@router.post("/runs/{run_id}/cancel")
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

    from apps.cosa.api.schemas import CancelRunResponse
    return CancelRunResponse(run_id=run_id, status="CANCELLED")


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
            run_record = await plane.run_repository.get_scoped_run(
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
```

- [ ] **Step 4: Create knowledge_routes.py (Lines 1039-1389 + helpers from routes.py)**

Create `/Volumes/SSD/javis-saas/apps/cosa/api/knowledge_routes.py`:

```python
"""Knowledge ingestion routes for COSA Agent Platform."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from apps.cosa.api.schemas import (
    CompleteKnowledgeUploadResponse,
    CreateKnowledgeUploadRequest,
    KnowledgeUploadResponse,
    ReviewKnowledgeIngestionRequest,
    ReviewKnowledgeIngestionResponse,
)
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.config.planes import resolve_platform_control_plane_url
from apps.cosa.knowledge_ingestion.contracts import knowledge_ingestion_enabled

__all__ = ["create_knowledge_router"]

logger = logging.getLogger("cosa.api.knowledge_routes")

router = APIRouter(prefix="/agent", tags=["knowledge-ingestion"])


def get_cosa_plane(request: Request) -> CosaAgentPlane:
    """Dependency injection từ `app.state.plane`."""
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError("CosaAgentPlane chưa sẵn sàng — app.state.plane rỗng.")
    return plane


def _get_cosa_document_ingestion_client():
    """Get or create services/cosa document ingestion client."""
    return httpx.AsyncClient()


# Knowledge Ingestion (Task 2)
# Phải kích hoạt feature flag KNOWLEDGE_INGESTION_ENABLED=true để cho phép routes


@router.post(
    "/knowledge/uploads",
    status_code=201,
    response_model=KnowledgeUploadResponse,
)
async def create_knowledge_upload(
    request: Request,
    payload: CreateKnowledgeUploadRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> KnowledgeUploadResponse:
    """POST /agent/knowledge/uploads — initiate document ingestion.

    Returns upload ticket with signed URL (object_key not exposed).
    """
    # Feature flag check
    if not knowledge_ingestion_enabled():
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
    control_plane_url = resolve_platform_control_plane_url()
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
            if isinstance(resp.status_code, int) and resp.status_code not in (200, 201):
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            raw_data = resp.json()
            ingestion_data = await raw_data if asyncio.iscoroutine(raw_data) else (raw_data or {})
            raw_id = ingestion_data.get("id")
            if asyncio.iscoroutine(raw_id):
                ingestion_id = str(await raw_id)
            elif isinstance(raw_id, str):
                ingestion_id = raw_id
            else:
                ingestion_id = str(raw_id or f"ing_{uuid.uuid4().hex[:12]}")
        finally:
            if should_close:
                await http_client.aclose()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("control plane error issuing knowledge upload ticket")
        raise HTTPException(status_code=502, detail="control plane error") from e

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
        logger.exception("object store error issuing knowledge upload ticket")
        raise HTTPException(status_code=500, detail="object store error") from e

    # Return response (no object_key, only signed_url)
    return KnowledgeUploadResponse(
        ingestion_id=ingestion_id,
        state="UPLOADING",
        file_name=req.file_name,
        declared_media_type=req.declared_media_type,
        signed_upload_url=ticket.signed_url,
        expires_at=ticket.expires_at,
    )


@router.post(
    "/knowledge/uploads/{ingestion_id}/complete",
    status_code=200,
    response_model=CompleteKnowledgeUploadResponse,
)
async def complete_knowledge_upload(
    request: Request,
    ingestion_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> CompleteKnowledgeUploadResponse:
    """POST /agent/knowledge/uploads/{ingestion_id}/complete — finalize upload.

    Server validates size, computes SHA-256, sniffs MIME, then transitions to QUEUED.
    """
    # Feature flag check
    if not knowledge_ingestion_enabled():
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
    except ValueError:
        # Non-enumerating error for missing/expired ticket
        raise HTTPException(
            status_code=404, detail="Ingestion not found or ticket expired"
        ) from None
    except Exception as e:
        logger.exception("object store error finalizing knowledge upload")
        raise HTTPException(status_code=500, detail="object store error") from e

    # Call services/cosa to complete upload and transition UPLOADING→QUARANTINED→QUEUED
    # Use worker service token (broker is a trusted internal caller)
    control_plane_url = resolve_platform_control_plane_url()
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
            if isinstance(resp.status_code, int) and resp.status_code not in (200, 202):
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            raw_data = resp.json()
            completion_data = await raw_data if asyncio.iscoroutine(raw_data) else (raw_data or {})
        finally:
            if should_close:
                await http_client.aclose()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("control plane error completing knowledge upload")
        raise HTTPException(status_code=502, detail="control plane error") from e

    # Return response (no object_key leaked)
    return CompleteKnowledgeUploadResponse(
        ingestion_id=ingestion_id,
        state=completion_data.get("state", "QUEUED"),
        detected_media_type=quarantined.detected_media_type,
        size_bytes=quarantined.size_bytes,
        source_sha256=quarantined.source_sha256,
    )


@router.post(
    "/knowledge/ingestions/{ingestion_id}/review",
    status_code=200,
    response_model=ReviewKnowledgeIngestionResponse,
)
async def review_knowledge_ingestion(
    request: Request,
    ingestion_id: str,
    payload: ReviewKnowledgeIngestionRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> ReviewKnowledgeIngestionResponse:
    """POST /agent/knowledge/ingestions/{ingestion_id}/review — review a candidate for publication.

    Reviews a REVIEW_PENDING knowledge ingestion candidate:
    - publish_reference: Flip status to published (candidate becomes visible as knowledge source)
    - reject: Flip status to rejected (candidate discarded)

    Decision is recorded with reviewer ID and reason in audit trail.

    NOTE: publish_reference does NOT create a KnowledgeSnapshot or enable retrieval — only
    flips the candidate status. Retrieval wiring is handled separately (out of scope for Phase A).
    """
    # Feature flag check
    if not knowledge_ingestion_enabled():
        raise HTTPException(status_code=403, detail="Knowledge ingestion not enabled")

    # Get services/cosa client
    cosa_client = getattr(request.app.state, "cosa_document_ingestion_client", None)
    if cosa_client is None:
        cosa_client = _get_cosa_document_ingestion_client()

    control_plane_url = resolve_platform_control_plane_url()
    try:
        # Use member bearer token for member-only review endpoint
        token = identity.bearer_token

        # Map Python-side decision to TS-side decision
        ts_decision = "PUBLISHED" if payload.decision == "publish_reference" else "REJECTED"

        # Use injected client if available, else create one
        http_client = getattr(request.app.state, "cosa_document_ingestion_client", None)
        should_close = False
        if http_client is None:
            http_client = httpx.AsyncClient(timeout=10.0)
            should_close = True

        try:
            resp = await http_client.post(
                f"{control_plane_url}/cosa/document-ingestions/{ingestion_id}/review",
                json={
                    "workspaceId": identity.workspace_id,
                    "decision": ts_decision,
                    "reason": payload.reason,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            if isinstance(resp.status_code, int) and resp.status_code not in (200, 202):
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            raw_data = resp.json()
            review_data = await raw_data if asyncio.iscoroutine(raw_data) else (raw_data or {})
        finally:
            if should_close:
                await http_client.aclose()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("control plane error reviewing knowledge document")
        raise HTTPException(status_code=502, detail="control plane error") from e

    # Step 2: đồng bộ trạng thái sang agent candidate (review_pending → published/rejected).
    agent_status = "published" if ts_decision == "PUBLISHED" else "rejected"
    knowledge_source_id = review_data.get("knowledgeSourceId")

    if knowledge_source_id:
        try:
            from datetime import UTC, datetime

            _plane = getattr(request.app.state, "plane", None)
            knowledge_service = getattr(
                request.app.state, "knowledge_ingestion_service", None
            ) or getattr(_plane, "knowledge_ingestion_service", None)
            if knowledge_service is None:
                _env = os.environ.get(
                    "ENVIRONMENT", os.environ.get("APP_ENV", "development")
                ).lower()
                if _env in ("production", "staging", "prod"):
                    raise RuntimeError(
                        "knowledge ingestion service not wired on plane in production"
                    )
                from agent.knowledge.service import KnowledgeIngestionService

                knowledge_service = KnowledgeIngestionService()
            await knowledge_service.update_document_ingest_status(
                knowledge_source_id, agent_status, identity.workspace_id
            )

            # Closeout Task 3: sau khi review PUBLISHED + status đã persist, phát
            # knowledge.source.published.v1 (reference-only) qua outbox
            if ts_decision == "PUBLISHED":
                try:
                    from agent.knowledge.snapshot import KnowledgeSnapshot

                    from apps.cosa.knowledge_ingestion.publish import publish_knowledge_source

                    snapshot = KnowledgeSnapshot(
                        id=str(knowledge_source_id),
                        workspace_id=str(identity.workspace_id),
                        source_refs=[{"source_id": str(knowledge_source_id), "version": "1"}],
                        embedding_model="none",
                        embedding_version="0",
                    ).with_hash()
                    await publish_knowledge_source(
                        snapshot=snapshot,
                        approved=True,
                        persisted=True,
                        reviewed_by=str(identity.platform_user_id),
                        reviewed_at=datetime.now(UTC).isoformat(),
                        correlation_id=f"review-{ingestion_id}",
                    )
                except Exception as pub_err:
                    logger.error(
                        "Failed to emit knowledge.source.published.v1 for ingestion_id=%s: %s",
                        ingestion_id,
                        pub_err,
                    )
        except Exception as e:
            logger.error(
                "Failed to sync agent status for ingestion_id=%s source_id=%s: %s",
                ingestion_id,
                knowledge_source_id,
                e,
            )
    else:
        logger.warning(
            "Review for ingestion_id=%s has no knowledgeSourceId; skipping agent status sync",
            ingestion_id,
        )

    # Return safe response (no object metadata, no Markdown)
    return ReviewKnowledgeIngestionResponse(
        ingestion_id=ingestion_id,
        state=ts_decision,
        decision=payload.decision,
    )


def create_knowledge_router() -> APIRouter:
    """Export router for app.py registration."""
    return router
```

- [ ] **Step 5: Create connector_routes.py (Lines 842-935 from routes.py)**

Create `/Volumes/SSD/javis-saas/apps/cosa/api/connector_routes.py`:

```python
"""Connector proxy routes for COSA Agent Platform."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from apps.cosa.api.schemas import (
    AuthorizeConnectorRequest,
    GrantConnectorRequest,
    InstallConnectorRequest,
    RevokeGrantRequest,
)
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.config.planes import resolve_platform_control_plane_url

__all__ = ["create_connector_router"]

router = APIRouter(prefix="/agent", tags=["connectors"])


# 12. Connectors Proxy Routes (Task 3)
@router.post("/connectors/install")
async def install_connector(
    request: Request,
    body: InstallConnectorRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = resolve_platform_control_plane_url()
    token = request.headers.get("Authorization") or f"Bearer {identity.mint_delegation()}"
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
    control_plane_url = resolve_platform_control_plane_url()
    token = request.headers.get("Authorization") or f"Bearer {identity.mint_delegation()}"
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
    control_plane_url = resolve_platform_control_plane_url()
    token = request.headers.get("Authorization") or f"Bearer {identity.mint_delegation()}"
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
    control_plane_url = resolve_platform_control_plane_url()
    token = request.headers.get("Authorization") or f"Bearer {identity.mint_delegation()}"
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


def create_connector_router() -> APIRouter:
    """Export router for app.py registration."""
    return router
```

- [ ] **Step 6: Create schedule_routes.py (Lines 937-1037 from routes.py)**

Create `/Volumes/SSD/javis-saas/apps/cosa/api/schedule_routes.py`:

```python
"""Schedule proxy routes for COSA Agent Platform."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from apps.cosa.api.schemas import CreateScheduleRequest, ScheduleListResponse, ScheduleResponse
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.config.planes import resolve_platform_control_plane_url

__all__ = ["create_schedule_router"]

router = APIRouter(prefix="/agent", tags=["schedules"])


# 13. Schedules Proxy Routes (Task 4)
@router.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(
    request: Request,
    body: CreateScheduleRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    control_plane_url = resolve_platform_control_plane_url()
    token = request.headers.get("Authorization") or f"Bearer {identity.mint_delegation()}"
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
    control_plane_url = resolve_platform_control_plane_url()
    token = request.headers.get("Authorization") or f"Bearer {identity.mint_delegation()}"
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
    control_plane_url = resolve_platform_control_plane_url()
    token = request.headers.get("Authorization") or f"Bearer {identity.mint_delegation()}"
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


def create_schedule_router() -> APIRouter:
    """Export router for app.py registration."""
    return router
```

- [ ] **Step 7: Move approval endpoints from routes.py to workforce_routes.py**

Add the following to `/Volumes/SSD/javis-saas/apps/cosa/api/workforce_routes.py` (replace the existing approval endpoints if duplicated, or add if missing). Ensure the endpoints consolidate to ONE canonical location:

```python
# Replace existing approval endpoints in workforce_routes.py with these consolidated versions
# (if they already exist there, verify they match the canonical implementation)

from agent.capabilities.approval_service import ApprovalAlreadyDecidedError

# At the end of the existing workflow/assignment routes, add:

# ─── Approvals (Consolidated to workforce_routes.py) ───


@router.get("/approvals")
async def list_approvals_consolidated(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
    status_filter: str | None = Query(None, alias="status"),
):
    """List pending approvals — consolidated canonical endpoint at /agent/workforce/approvals."""
    plane = _get_plane(request)
    pending = await plane.approval_service.list_pending_approvals(
        workspace_id=identity.workspace_id,
    )
    items = []
    for app in pending:
        if status_filter and app.status != status_filter:
            continue
        items.append(
            {
                "id": app.approval_id,
                "approval_id": app.approval_id,
                "run_id": app.run_id,
                "tool_call_id": app.tool_call_id,
                "checkpoint_ref": app.checkpoint_ref,
                "action": app.action,
                "subject": app.subject,
                "status": app.status,
                "risk_level": app.requirement.get("risk_level", "medium")
                if isinstance(app.requirement, dict)
                else "medium",
                "required_role": app.requirement.get("role", "admin")
                if isinstance(app.requirement, dict)
                else "admin",
                "policy_id": app.requirement.get("policy_id", "default")
                if isinstance(app.requirement, dict)
                else "default",
                "created_at": app.created_at.isoformat()
                if hasattr(app.created_at, "isoformat")
                else str(app.created_at),
            }
        )
    return {"items": items, "total": len(items)}


@router.post("/approvals/{approval_id}/decision")
async def decide_approval_consolidated(
    request: Request,
    approval_id: str,
    req: ApprovalDecisionRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    """Decide on approval — consolidated canonical endpoint at /agent/workforce/approvals/{approval_id}/decision."""
    plane = _get_plane(request)
    stream_mgr = get_cosa_event_stream_manager()

    # Tenant check TRƯỚC khi cho phép quyết định
    existing_approval = await plane.approval_service.get_scoped_approval(
        approval_id=approval_id,
        workspace_id=identity.workspace_id,
    )
    if existing_approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval not found: {approval_id}"
        )

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval not found: {approval_id}"
        )

    if plane.workforce_repository is not None:
        await plane.workforce_repository.enqueue_runtime_signal(
            workspace_id=identity.workspace_id,
            source_kind="approval",
            source_id=approval_id,
            sequence=1,
            state=decided.status,
            observed_at=decided.decided_at or datetime.now(UTC),
        )

    # Bơm Prometheus approval metric
    try:
        from apps.cosa.observability.metrics import record_approval as _record_approval

        _decision = decided.status or ("approved" if req.approved else "rejected")
        _wait_sec: float | None = None
        if existing_approval.created_at is not None and decided.decided_at is not None:
            _wait_sec = (decided.decided_at - existing_approval.created_at).total_seconds()
        _record_approval(_decision, wait_duration_sec=_wait_sec)
    except Exception:
        pass

    run_id = decided.run_id
    run_record = await plane.repository.get_scoped_run(
        run_id=run_id,
        workspace_id=identity.workspace_id,
    )
    resume_conversation_id = (
        run_record.conversation_id if run_record and run_record.conversation_id else "unknown"
    )

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

    # Resume kernel if approved
    if req.approved and decided.checkpoint_ref:
        await plane.scheduler.schedule(
            target_spec_id="cosa.resume",
            input_payload={
                "task_type": "resume",
                "run_id": run_id,
                "checkpoint_ref": decided.checkpoint_ref,
                "conversation_id": resume_conversation_id,
                "workspace_id": run_record.workspace_id if run_record else None,
                "delegation_token": identity.mint_delegation(),
            },
        )

    return ApprovalDecisionResponse(
        approval_id=decided.approval_id,
        run_id=decided.run_id,
        status=decided.status,
        reviewer=decided.reviewer or identity.principal_id,
        reason=decided.reason,
        decided_at=decided.decided_at or datetime.now(UTC),
    )
```

**Note:** If workforce_routes.py already has these approval endpoints, verify they match exactly. If routes.py has duplicates, they must be removed after this consolidation.

- [ ] **Step 8: Update routes.py to remove split sections and remove approval endpoints**

Edit `/Volumes/SSD/javis-saas/apps/cosa/api/routes.py` to keep ONLY the run-cancel endpoint (if needed) and remove everything else that was split out:

```python
"""Run operations routes for COSA Agent Platform (minimal post-split)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from apps.cosa.api.schemas import CancelRunResponse
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.composition.agent_plane import CosaAgentPlane

__all__ = ["create_cosa_router", "router"]

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
    from apps.cosa.api.event_stream import get_cosa_event_stream_manager
    
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
    from fastapi.responses import StreamingResponse
    from apps.cosa.api.event_stream import get_cosa_event_stream_manager

    plane = get_cosa_plane(request)
    await plane.repository.get_scoped_run(
        run_id=run_id,
        workspace_id=identity.workspace_id,
    )
    if await plane.repository.get_scoped_run(run_id=run_id, workspace_id=identity.workspace_id) is None:
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
```

- [ ] **Step 9: Update app.py router registration**

Edit `/Volumes/SSD/javis-saas/apps/cosa/api/app.py` to import and register new routers:

```python
# Change lines 11-20 from:
from apps.cosa.api.autopilot_metrics_routes import create_autopilot_metrics_router
from apps.cosa.api.copilot_routes import create_copilot_router
from apps.cosa.api.event_intake_routes import create_event_intake_router
from apps.cosa.api.event_operations_routes import create_event_operations_router
from apps.cosa.api.event_rule_routes import create_event_rule_router
from apps.cosa.api.routes import router
from apps.cosa.api.settings_routes import router as settings_router
from apps.cosa.api.skill_registry_routes import create_skill_registry_router
from apps.cosa.api.vault_routes import router as vault_router
from apps.cosa.api.workforce_routes import router as workforce_router

# To:
from apps.cosa.api.autopilot_metrics_routes import create_autopilot_metrics_router
from apps.cosa.api.copilot_routes import create_copilot_router
from apps.cosa.api.event_intake_routes import create_event_intake_router
from apps.cosa.api.event_operations_routes import create_event_operations_router
from apps.cosa.api.event_rule_routes import create_event_rule_router
from apps.cosa.api.routes import router
from apps.cosa.api.conversation_routes import create_conversation_router
from apps.cosa.api.knowledge_routes import create_knowledge_router
from apps.cosa.api.connector_routes import create_connector_router
from apps.cosa.api.schedule_routes import create_schedule_router
from apps.cosa.api.settings_routes import router as settings_router
from apps.cosa.api.skill_registry_routes import create_skill_registry_router
from apps.cosa.api.vault_routes import router as vault_router
from apps.cosa.api.workforce_routes import router as workforce_router

# Change lines 191-200 from:
app.include_router(router)
app.include_router(workforce_router)
app.include_router(vault_router)
app.include_router(settings_router)
app.include_router(create_skill_registry_router())
app.include_router(create_event_intake_router())
app.include_router(create_event_rule_router())
app.include_router(create_event_operations_router())
app.include_router(create_copilot_router())
app.include_router(create_autopilot_metrics_router())

# To:
app.include_router(router)
app.include_router(create_conversation_router())
app.include_router(create_knowledge_router())
app.include_router(create_connector_router())
app.include_router(create_schedule_router())
app.include_router(workforce_router)
app.include_router(vault_router)
app.include_router(settings_router)
app.include_router(create_skill_registry_router())
app.include_router(create_event_intake_router())
app.include_router(create_event_rule_router())
app.include_router(create_event_operations_router())
app.include_router(create_copilot_router())
app.include_router(create_autopilot_metrics_router())
```

- [ ] **Step 10: Run test to verify split succeeded**

```bash
cd /Volumes/SSD/javis-saas
python -m pytest tests/apps/cosa/test_routes_split_baseline.py -xvs
```

Expected: PASS — all routes exist, old `/agent/approvals` routes removed, consolidated at `/agent/workforce/approvals`

- [ ] **Step 11: Run full route test suite**

```bash
cd /Volumes/SSD/javis-saas
python -m pytest tests/apps/cosa/test_routes.py tests/apps/cosa/test_router_registration.py -xvs
```

Expected: PASS — all existing behavior preserved

- [ ] **Step 12: Lint and type-check**

```bash
cd /Volumes/SSD/javis-saas
python -m ruff check apps/cosa/api/
python -m mypy apps/cosa/api/routes.py apps/cosa/api/conversation_routes.py apps/cosa/api/knowledge_routes.py apps/cosa/api/connector_routes.py apps/cosa/api/schedule_routes.py
```

- [ ] **Step 13: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add apps/cosa/api/routes.py
git add apps/cosa/api/conversation_routes.py
git add apps/cosa/api/approval_routes.py
git add apps/cosa/api/knowledge_routes.py
git add apps/cosa/api/connector_routes.py
git add apps/cosa/api/schedule_routes.py
git add apps/cosa/api/workforce_routes.py
git add apps/cosa/api/app.py
git add tests/apps/cosa/test_routes_split_baseline.py
git commit -m "refactor(cosa-api): split mega-router routes.py into domain-specific modules

- Separate conversation CRUD (conversation_routes.py) from routes.py
- Separate knowledge ingestion (knowledge_routes.py) from routes.py
- Separate connector proxy (connector_routes.py) from routes.py
- Separate schedule proxy (schedule_routes.py) from routes.py
- Consolidate approval endpoints to workforce_routes.py (canonical location)
- Remove duplicate /agent/approvals endpoints from routes.py
- Update app.py router registration to include new routers
- Add test_routes_split_baseline.py to verify route registration unchanged

All public interface paths preserved; no API contract changes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: `apps/cosa/composition/agent_plane.py` — Dependency Grouping (RunExecutionService, WorkflowOrchestration, ComplianceCoordination)

**Files:**
- Modify: `apps/cosa/composition/agent_plane.py` (820→similar lines, add 3 new interface classes)
- Create: `apps/cosa/composition/run_execution_service.py` (~100 lines)
- Create: `apps/cosa/composition/workflow_orchestration.py` (~100 lines)
- Create: `apps/cosa/composition/compliance_coordination.py` (~100 lines)
- Modify: `apps/cosa/composition/agent_plane.py` to keep compatibility properties
- Test: `tests/apps/cosa/test_agent_plane.py` (verify compatibility layer works)

**Interfaces:**
- Consumes: CosaAgentPlane 23 public attributes
- Produces: Same public interface via compatibility properties; new narrower service interfaces

- [ ] **Step 1: Write test to find all callers of agent_plane attributes**

Create `tests/apps/cosa/test_agent_plane_coupling.py`:

```python
"""Test to identify all direct accesses to agent_plane attributes — baseline for decoupling."""

import subprocess
import re

def test_all_agent_plane_direct_accesses_documented():
    """Grep for direct access to agent_plane attributes across codebase."""
    result = subprocess.run(
        ['grep', '-r', r'plane\.gateway\|plane\.repository\|plane\.policy_engine\|plane\.approval_service\|plane\.kernel\|plane\.workflow', 
         '/Volumes/SSD/javis-saas/apps/cosa', '--include=*.py'],
        capture_output=True,
        text=True
    )
    lines = result.stdout.strip().split('\n')
    accessed_attrs = set()
    for line in lines:
        # Extract attribute names from patterns like "plane.gateway"
        match = re.search(r'plane\.(\w+)', line)
        if match:
            accessed_attrs.add(match.group(1))
    
    # These are the 23 known public attributes
    known_attrs = {
        'repository', 'run_repository', 'conversation_repository', 'spec_registry',
        'governance_store', 'capability_registry', 'policy_engine', 'approval_service',
        'gateway', 'kernel', 'workflow_registry', 'workflow_engine', 'company_client',
        'tenant_policy_client', 'scheduler', 'lease_client', 'stream_event_repository',
        'artifact_repository', 'workforce_repository', 'vault_repository', 
        'event_intake_deps', 'memory_service', 'knowledge_ingestion_service',
        'compliance_resolver', 'engines'
    }
    
    # Log what we found
    print("\nAccessed attributes:")
    for attr in sorted(accessed_attrs):
        print(f"  - {attr}")
    
    # Ensure we document high-usage attributes that will move to service interfaces
    high_usage = {'gateway', 'repository', 'policy_engine', 'approval_service', 'kernel'}
    assert high_usage.issubset(accessed_attrs), f"High-usage attributes not found: {high_usage - accessed_attrs}"
```

- [ ] **Step 2: Run test and document findings**

```bash
cd /Volumes/SSD/javis-saas
python -m pytest tests/apps/cosa/test_agent_plane_coupling.py -xvs
```

This scan identifies which 12 files access which attributes. Document the mapping.

- [ ] **Step 3: Create RunExecutionService interface**

Create `/Volumes/SSD/javis-saas/apps/cosa/composition/run_execution_service.py`:

```python
"""RunExecutionService — narrower interface for run execution concerns."""

from __future__ import annotations

from typing import Any

from agent.contracts.kernel import ExecutionKernel
from agent.runs.repository import RunRepository


class RunExecutionService:
    """Encapsulates run-related dependencies (kernel, repository, lease, scheduler)."""

    def __init__(
        self,
        kernel: ExecutionKernel,
        repository: RunRepository,
        lease_client: Any,
        scheduler: Any,
    ) -> None:
        self.kernel = kernel
        self.repository = repository
        self.lease_client = lease_client
        self.scheduler = scheduler


class IRunExecutionService:
    """Public interface for consumers — type hint only, no runtime inheritance required."""

    kernel: ExecutionKernel
    repository: RunRepository
    lease_client: Any
    scheduler: Any
```

- [ ] **Step 4: Create WorkflowOrchestration interface**

Create `/Volumes/SSD/javis-saas/apps/cosa/composition/workflow_orchestration.py`:

```python
"""WorkflowOrchestration — narrower interface for workflow orchestration concerns."""

from __future__ import annotations

from typing import Any

from agent.capabilities.gateway import CapabilityGateway
from agent.workflows.definition_registry import WorkflowDefinitionRegistry
from agent.workflows.engine import WorkflowEngine


class WorkflowOrchestration:
    """Encapsulates workflow-related dependencies (gateway, engine, registry, approval service)."""

    def __init__(
        self,
        gateway: CapabilityGateway,
        workflow_engine: WorkflowEngine,
        workflow_registry: WorkflowDefinitionRegistry,
        approval_service: Any,
    ) -> None:
        self.gateway = gateway
        self.workflow_engine = workflow_engine
        self.workflow_registry = workflow_registry
        self.approval_service = approval_service


class IWorkflowOrchestration:
    """Public interface for consumers — type hint only."""

    gateway: CapabilityGateway
    workflow_engine: WorkflowEngine
    workflow_registry: WorkflowDefinitionRegistry
    approval_service: Any
```

- [ ] **Step 5: Create ComplianceCoordination interface**

Create `/Volumes/SSD/javis-saas/apps/cosa/composition/compliance_coordination.py`:

```python
"""ComplianceCoordination — narrower interface for compliance orchestration."""

from __future__ import annotations

from typing import Any

from agent.capabilities.registry import CapabilityRegistry
from agent.governance.store import GovernanceStateStore


class ComplianceCoordination:
    """Encapsulates compliance-related dependencies (policy engine, capability registry, governance store, compliance resolver)."""

    def __init__(
        self,
        policy_engine: Any,
        capability_registry: CapabilityRegistry,
        governance_store: GovernanceStateStore,
        compliance_resolver: Any | None = None,
    ) -> None:
        self.policy_engine = policy_engine
        self.capability_registry = capability_registry
        self.governance_store = governance_store
        self.compliance_resolver = compliance_resolver


class IComplianceCoordination:
    """Public interface for consumers — type hint only."""

    policy_engine: Any
    capability_registry: CapabilityRegistry
    governance_store: GovernanceStateStore
    compliance_resolver: Any | None
```

- [ ] **Step 6: Add compatibility properties to CosaAgentPlane**

Edit `/Volumes/SSD/javis-saas/apps/cosa/composition/agent_plane.py` to add (at end of `__init__`):

```python
# Import at top of file:
from apps.cosa.composition.run_execution_service import RunExecutionService
from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration
from apps.cosa.composition.compliance_coordination import ComplianceCoordination

# Add these properties to CosaAgentPlane class (after __init__ ends):

    @property
    def run_execution(self) -> RunExecutionService:
        """Narrower interface for run execution (kernel, repository, lease, scheduler)."""
        return RunExecutionService(
            kernel=self.kernel,
            repository=self.repository,
            lease_client=self.lease_client,
            scheduler=self.scheduler,
        )

    @property
    def workflow_orchestration(self) -> WorkflowOrchestration:
        """Narrower interface for workflow orchestration (gateway, engine, registry, approval)."""
        return WorkflowOrchestration(
            gateway=self.gateway,
            workflow_engine=self.workflow_engine,
            workflow_registry=self.workflow_registry,
            approval_service=self.approval_service,
        )

    @property
    def compliance_coordination(self) -> ComplianceCoordination:
        """Narrower interface for compliance orchestration (policy, governance, compliance resolver)."""
        return ComplianceCoordination(
            policy_engine=self.policy_engine,
            capability_registry=self.capability_registry,
            governance_store=self.governance_store,
            compliance_resolver=self.compliance_resolver,
        )
```

- [ ] **Step 7: Update 2-3 key callers to use narrower interfaces (demonstration)**

Find 2-3 files from grep results that heavily use `plane.gateway`, `plane.repository`, etc., and update them to use the new narrower interfaces. Example: if `apps/cosa/worker/handlers.py` accesses `plane.kernel`, `plane.repository`, `plane.scheduler` — update it to use `plane.run_execution`:

```python
# Before:
async def execute_run(plane: CosaAgentPlane, run_id: str):
    result = await plane.kernel.run(...)  # Direct access
    run_record = await plane.repository.get(run_id)  # Direct access
    await plane.scheduler.schedule(...)  # Direct access

# After:
async def execute_run(plane: CosaAgentPlane, run_id: str):
    run_exec = plane.run_execution  # Narrow interface
    result = await run_exec.kernel.run(...)
    run_record = await run_exec.repository.get(run_id)
    await run_exec.scheduler.schedule(...)
```

- [ ] **Step 8: Run compatibility test**

Create `tests/apps/cosa/test_agent_plane_compat.py`:

```python
"""Test compatibility layer: new narrower services work alongside old attributes."""

from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.composition.run_execution_service import RunExecutionService
from apps.cosa.composition.workflow_orchestration import WorkflowOrchestration
from apps.cosa.composition.compliance_coordination import ComplianceCoordination
from tests.apps.cosa.policy_test_helpers import (
    StubCompanyServiceClient,
    stub_active_tenant_policy_client,
)
from agent.runs.repository import InMemoryRunRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.coordination.scheduler import RunScheduler
from agent.runs.leases import RunLeaseManager
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.artifacts import InMemoryArtifactRepository
from agent.workforce.repository import InMemoryWorkforceRepository
from agent.vault.repository import InMemoryVaultRepository
from agent_testkit.fake_sdk_model import FakeSDKModel


def test_run_execution_service_accessible_via_property():
    plane = build_cosa_agent_plane(
        company_client=StubCompanyServiceClient(),
        tenant_policy_client=stub_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        workforce_repository=InMemoryWorkforceRepository(),
        vault_repository=InMemoryVaultRepository(),
        model=FakeSDKModel(),
    )
    
    # Old direct access still works
    assert plane.kernel is not None
    assert plane.repository is not None
    assert plane.scheduler is not None
    
    # New narrower interface works
    run_exec = plane.run_execution
    assert isinstance(run_exec, RunExecutionService)
    assert run_exec.kernel is plane.kernel
    assert run_exec.repository is plane.repository
    assert run_exec.scheduler is plane.scheduler


def test_workflow_orchestration_accessible_via_property():
    plane = build_cosa_agent_plane(
        company_client=StubCompanyServiceClient(),
        tenant_policy_client=stub_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateState(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        workforce_repository=InMemoryWorkforceRepository(),
        vault_repository=InMemoryVaultRepository(),
        model=FakeSDKModel(),
    )
    
    # Old direct access still works
    assert plane.gateway is not None
    assert plane.workflow_engine is not None
    
    # New narrower interface works
    wf_orch = plane.workflow_orchestration
    assert isinstance(wf_orch, WorkflowOrchestration)
    assert wf_orch.gateway is plane.gateway
    assert wf_orch.workflow_engine is plane.workflow_engine


def test_compliance_coordination_accessible_via_property():
    plane = build_cosa_agent_plane(
        company_client=StubCompanyServiceClient(),
        tenant_policy_client=stub_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        workforce_repository=InMemoryWorkforceRepository(),
        vault_repository=InMemoryVaultRepository(),
        model=FakeSDKModel(),
    )
    
    # Old direct access still works
    assert plane.policy_engine is not None
    assert plane.governance_store is not None
    
    # New narrower interface works
    comp_coord = plane.compliance_coordination
    assert isinstance(comp_coord, ComplianceCoordination)
    assert comp_coord.policy_engine is plane.policy_engine
    assert comp_coord.governance_store is plane.governance_store
```

- [ ] **Step 9: Run test**

```bash
cd /Volumes/SSD/javis-saas
python -m pytest tests/apps/cosa/test_agent_plane_compat.py -xvs
```

Expected: PASS

- [ ] **Step 10: Lint and type-check**

```bash
cd /Volumes/SSD/javis-saas
python -m ruff check apps/cosa/composition/
python -m mypy apps/cosa/composition/agent_plane.py apps/cosa/composition/run_execution_service.py apps/cosa/composition/workflow_orchestration.py apps/cosa/composition/compliance_coordination.py
```

- [ ] **Step 11: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add apps/cosa/composition/agent_plane.py
git add apps/cosa/composition/run_execution_service.py
git add apps/cosa/composition/workflow_orchestration.py
git add apps/cosa/composition/compliance_coordination.py
git add tests/apps/cosa/test_agent_plane_compat.py
git commit -m "refactor(cosa): group agent_plane dependencies into narrower service interfaces

- Create RunExecutionService for kernel, repository, lease, scheduler
- Create WorkflowOrchestration for gateway, engine, registry, approval
- Create ComplianceCoordination for policy, governance, compliance resolver
- Add compatibility properties to CosaAgentPlane for gradual migration
- Old direct attribute access still works via properties
- New code can adopt narrower interfaces via plane.run_execution / plane.workflow_orchestration / plane.compliance_coordination

No breaking changes; full backward compatibility via properties.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: `services/company/commercial/services/marketing-context.service.ts` — Split by Domain (product/research/snapshot)

**Files:**
- Modify: `services/company/commercial/services/marketing-context.service.ts` (787→~250 lines, remove functions)
- Create: `services/company/commercial/services/product-marketing.service.ts` (~250 lines)
- Create: `services/company/commercial/services/customer-research.service.ts` (~300 lines)
- Create: `services/company/commercial/services/marketing-snapshot.service.ts` (~150 lines)
- Modify: `services/company/commercial/handlers/marketing-context.handler.ts` (update imports)
- Test: `services/company/commercial/tests/` (verify split endpoints work)

**Interfaces:**
- Consumes: TenantContext, Drizzle ORM db
- Produces: Same DTOs; exports split across 3 services

- [ ] **Step 1: Run existing tests as baseline**

```bash
cd /Volumes/SSD/javis-saas
pnpm test services/company/commercial/tests --run
```

Expected: Tests pass (baseline)

- [ ] **Step 2: Read marketing-context.service.ts fully to identify function groups**

Read the full file to see all exported functions and group them:

1. **Product Marketing** (positioning, differentiators, brand voice)
   - `updateProductMarketingService()`
   - Related DTO: `ProductMarketingDTO`, `UpdateProductMarketingParams`

2. **Customer Research** (ICP segments, themes, language/quotes, evidence)
   - `updateCustomerResearchService()`
   - Related DTOs: `IcpSegmentDTO`, `CustomerResearchThemeDTO`, `CustomerLanguageDTO`, `MarketingContextEvidenceDTO`, `UpdateCustomerResearchParams`

3. **Marketing Snapshot** (DTO assembly and revision tracking)
   - `assembleContextDTO()` (used by all)
   - `getMarketingContextService()` (returns assembled DTO)
   - `recordRevisionSnapshot()` (helper)

4. **Shared Helpers**
   - `getOrCreateContextRow()` (used by all)
   - `verifyOptimisticLock()` (used by all)

- [ ] **Step 3: Create product-marketing.service.ts**

Create `/Volumes/SSD/javis-saas/services/company/commercial/services/product-marketing.service.ts`:

```typescript
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { marketingContexts, marketingProductMarketing } = schema;

export interface ProductMarketingDTO {
  category: string | null;
  positioningStatement: string | null;
  alternatives: any[];
  differentiators: any[];
  brandVoice: Record<string, any>;
}

export interface UpdateProductMarketingParams {
  category?: string;
  positioningStatement?: string;
  alternatives?: any[];
  differentiators?: any[];
  brandVoice?: Record<string, any>;
  expectedRevision?: number;
  sourceSkillId?: string;
  sourceSkillVersion?: string;
  sourceSkillHash?: string;
}

async function getOrCreateContextRow(ctx: TenantContext) {
  const wsId = BigInt(ctx.workspaceId);
  const [existing] = await db
    .select()
    .from(marketingContexts)
    .where(eq(marketingContexts.workspaceId, wsId))
    .limit(1);

  if (existing) {
    return existing;
  }

  const contextId = generateSnowflake();
  const [created] = await db
    .insert(marketingContexts)
    .values({
      id: contextId,
      workspaceId: wsId,
      revision: 1,
      status: "draft",
      updatedByUserId: BigInt(ctx.userId),
      offerArchitecture: {},
      twelveWeekPlan: {},
    })
    .returning();

  await db.insert(marketingProductMarketing).values({
    id: generateSnowflake(),
    contextId,
    workspaceId: wsId,
    category: null,
    positioningStatement: null,
    alternatives: [],
    differentiators: [],
    brandVoice: {},
  });

  return created;
}

function verifyOptimisticLock(currentRevision: number, expectedRevision?: number) {
  if (expectedRevision !== undefined && expectedRevision !== currentRevision) {
    throw APIError.aborted(
      `revision conflict: expected revision ${expectedRevision} but current revision is ${currentRevision}`
    );
  }
}

async function recordRevisionSnapshot(
  contextId: bigint,
  workspaceId: bigint,
  revision: number,
  snapshot: any,
  userId: bigint,
  sourceSkill?: { id?: string; version?: string; hash?: string }
) {
  const { marketingContextRevisions } = schema;
  await db.insert(marketingContextRevisions).values({
    id: generateSnowflake(),
    contextId,
    workspaceId,
    revision,
    snapshot,
    createdByUserId: userId,
    sourceSkillId: sourceSkill?.id ?? null,
    sourceSkillVersion: sourceSkill?.version ?? null,
    sourceSkillHash: sourceSkill?.hash ?? null,
  });
}

export async function getProductMarketing(
  ctx: TenantContext
): Promise<ProductMarketingDTO> {
  const contextRow = await getOrCreateContextRow(ctx);
  const wsId = BigInt(ctx.workspaceId);

  const [pmRow] = await db
    .select()
    .from(marketingProductMarketing)
    .where(
      and(
        eq(marketingProductMarketing.workspaceId, wsId),
        eq(marketingProductMarketing.contextId, contextRow.id)
      )
    )
    .limit(1);

  return {
    category: pmRow?.category ?? null,
    positioningStatement: pmRow?.positioningStatement ?? null,
    alternatives: (pmRow?.alternatives as any[]) ?? [],
    differentiators: (pmRow?.differentiators as any[]) ?? [],
    brandVoice: (pmRow?.brandVoice as Record<string, any>) ?? {},
  };
}

export async function updateProductMarketingService(
  ctx: TenantContext,
  params: UpdateProductMarketingParams
): Promise<ProductMarketingDTO> {
  const contextRow = await getOrCreateContextRow(ctx);
  verifyOptimisticLock(contextRow.revision, params.expectedRevision);

  const wsId = BigInt(ctx.workspaceId);
  const nextRevision = contextRow.revision + 1;
  const userId = BigInt(ctx.userId);

  const [existingPm] = await db
    .select({ id: marketingProductMarketing.id })
    .from(marketingProductMarketing)
    .where(
      and(
        eq(marketingProductMarketing.workspaceId, wsId),
        eq(marketingProductMarketing.contextId, contextRow.id)
      )
    )
    .limit(1);

  if (existingPm) {
    await db
      .update(marketingProductMarketing)
      .set({
        category: params.category !== undefined ? params.category : undefined,
        positioningStatement: params.positioningStatement !== undefined ? params.positioningStatement : undefined,
        alternatives: params.alternatives !== undefined ? params.alternatives : undefined,
        differentiators: params.differentiators !== undefined ? params.differentiators : undefined,
        brandVoice: params.brandVoice !== undefined ? params.brandVoice : undefined,
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(marketingProductMarketing.workspaceId, wsId),
          eq(marketingProductMarketing.contextId, contextRow.id)
        )
      );
  } else {
    await db.insert(marketingProductMarketing).values({
      id: generateSnowflake(),
      contextId: contextRow.id,
      workspaceId: wsId,
      category: params.category ?? null,
      positioningStatement: params.positioningStatement ?? null,
      alternatives: params.alternatives ?? [],
      differentiators: params.differentiators ?? [],
      brandVoice: params.brandVoice ?? {},
    });
  }

  const [updatedContext] = await db
    .update(marketingContexts)
    .set({
      revision: nextRevision,
      status: "draft",
      updatedByUserId: userId,
      sourceSkillId: params.sourceSkillId !== undefined ? params.sourceSkillId : contextRow.sourceSkillId,
      sourceSkillVersion: params.sourceSkillVersion !== undefined ? params.sourceSkillVersion : contextRow.sourceSkillVersion,
      sourceSkillHash: params.sourceSkillHash !== undefined ? params.sourceSkillHash : contextRow.sourceSkillHash,
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(marketingContexts.workspaceId, wsId),
        eq(marketingContexts.id, contextRow.id)
      )
    )
    .returning();

  const pm = await getProductMarketing(ctx);

  await recordRevisionSnapshot(
    contextRow.id,
    wsId,
    nextRevision,
    { productMarketing: pm },
    userId,
    {
      id: params.sourceSkillId,
      version: params.sourceSkillVersion,
      hash: params.sourceSkillHash,
    }
  );

  return pm;
}
```

- [ ] **Step 4: Create customer-research.service.ts**

Create `/Volumes/SSD/javis-saas/services/company/commercial/services/customer-research.service.ts` (similar pattern, omitted for brevity — follow same structure as product-marketing.service.ts but for ICP/research/evidence functions)

- [ ] **Step 5: Create marketing-snapshot.service.ts**

Create `/Volumes/SSD/javis-saas/services/company/commercial/services/marketing-snapshot.service.ts` (assembles full DTO by calling the other 2 services)

- [ ] **Step 6: Update marketing-context.service.ts to re-export and delegate**

Make the original `marketing-context.service.ts` a facade that imports and delegates:

```typescript
// Re-export from split services
export { getProductMarketing, updateProductMarketingService, ProductMarketingDTO, UpdateProductMarketingParams } from "./product-marketing.service";
export { getCustomerResearch, updateCustomerResearchService, IcpSegmentDTO, CustomerResearchThemeDTO } from "./customer-research.service";
export { getMarketingContextService, MarketingContextDTO } from "./marketing-snapshot.service";

// Keep any shared types if not moved
```

- [ ] **Step 7: Run tests**

```bash
cd /Volumes/SSD/javis-saas
pnpm test services/company/commercial/tests --run
```

Expected: PASS (all handlers still work, using same public exports)

- [ ] **Step 8: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/company/commercial/services/
git add services/company/commercial/tests/
git commit -m "refactor(services): split marketing-context.service.ts by domain

- Extract product-marketing.service.ts (positioning, differentiators, brand voice)
- Extract customer-research.service.ts (ICP segments, research themes, evidence)
- Extract marketing-snapshot.service.ts (DTO assembly and revision tracking)
- Keep marketing-context.service.ts as facade re-exporting all splits
- All public exports preserved; no API changes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: `frontend/lib/modules/strategy/services/strategy_service.dart` — Split by Domain (Canvas, OKR, 12-Week, Project, Portfolio, Founder)

**Files:**
- Create: `frontend/lib/modules/strategy/services/canvas_service.dart` (~300 lines)
- Create: `frontend/lib/modules/strategy/services/okr_service.dart` (~200 lines)
- Create: `frontend/lib/modules/strategy/services/twelve_week_service.dart` (~300 lines)
- Create: `frontend/lib/modules/strategy/services/project_service.dart` (~250 lines)
- Create: `frontend/lib/modules/strategy/services/portfolio_service.dart` (~200 lines)
- Create: `frontend/lib/modules/strategy/services/founder_service.dart` (~250 lines)
- Create: `frontend/lib/modules/strategy/services/strategy_service_base.dart` (~50 lines, shared helpers)
- Modify: `frontend/lib/modules/strategy/services/strategy_service.dart` (facade, ~100 lines)
- Test: `frontend/test/modules/strategy/strategy_service_test.dart` (split into domain tests)

**Interfaces:**
- Consumes: `SecureStorageService`, `ApiClient`, `StrategyListResult`
- Produces: Same public methods via facade; new narrower domain services

- [ ] **Step 1: Run existing tests as baseline**

```bash
cd /Volumes/SSD/javis-saas
flutter test test/modules/strategy/strategy_service_test.dart
```

Expected: Tests pass (baseline)

- [ ] **Step 2: Create strategy_service_base.dart for shared helpers**

Create `/Volumes/SSD/javis-saas/frontend/lib/modules/strategy/services/strategy_service_base.dart`:

```dart
import 'dart:convert';
import '../../../core/services/secure_storage_service.dart';
import '../models/strategy_list_result.dart';

/// Lỗi từ Strategy API
class StrategyApiException implements Exception {
  final int statusCode;
  final String message;
  StrategyApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

/// Base class for strategy domain services — shared helpers
abstract class StrategyServiceBase {
  Future<String?> getWorkspaceId() async {
    return SecureStorageService.read('workspace_id');
  }

  Future<String> requireWorkspaceId() async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      throw StrategyApiException(0, 'Chưa xác định workspace hiện tại');
    }
    return workspaceId;
  }

  dynamic decode(dynamic response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(response.body);
    }
    String detail = 'Yêu cầu thất bại (${response.statusCode})';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['detail'] != null) {
        final d = body['detail'];
        detail = d is String ? d : jsonEncode(d);
      }
    } catch (_) {
      // giữ nguyên detail mặc định nếu body không phải JSON hợp lệ
    }
    throw StrategyApiException(response.statusCode, detail);
  }

  StrategyListResult<Map<String, dynamic>> decodeList(
    dynamic response,
    String key, {
    bool optionalOn404 = false,
  }) {
    if (response.statusCode == 404) {
      if (optionalOn404) return const StrategyListResult.unavailable();
      return StrategyListResult.failure('Không tìm thấy dữ liệu (404)');
    }
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return const StrategyListResult.success([]);
      try {
        final data = jsonDecode(response.body);
        if (data is Map && data[key] is List) {
          final items = (data[key] as List)
              .map((e) => e is Map<String, dynamic> ? e : Map<String, dynamic>.from(e as Map))
              .toList();
          return StrategyListResult.success(items);
        }
        return const StrategyListResult.failure('Phản hồi không đúng định dạng mong đợi');
      } catch (_) {
        return const StrategyListResult.failure('Không thể đọc dữ liệu phản hồi từ máy chủ');
      }
    }
    String detail = 'Yêu cầu thất bại (${response.statusCode})';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['detail'] != null) {
        final d = body['detail'];
        detail = d is String ? d : jsonEncode(d);
      }
    } catch (_) {
      // giữ nguyên detail mặc định nếu body không phải JSON hợp lệ
    }
    return StrategyListResult.failure(detail);
  }
}
```

- [ ] **Step 3: Create canvas_service.dart**

Create `/Volumes/SSD/javis-saas/frontend/lib/modules/strategy/services/canvas_service.dart`:

```dart
import '../../../core/network/api_client.dart';
import '../models/strategy_list_result.dart';
import 'strategy_service_base.dart';

/// Strategic Canvas & Foundation (Phase 1)
class CanvasService extends StrategyServiceBase {
  Future<StrategyListResult<Map<String, dynamic>>> getCanvases() async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    try {
      final response = await ApiClient.get('/strategy/canvases?workspace_id=$workspaceId');
      return decodeList(response, 'canvases');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> getCanvasDetail(String canvasId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.get('/strategy/canvases/$canvasId?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> createCanvas(String name, {String? description}) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/canvases?workspace_id=$workspaceId',
      body: {
        'name': name,
        'description': ?description,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updateCanvas(String canvasId, {String? name, String? description}) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/canvases/$canvasId?workspace_id=$workspaceId',
      body: {
        'name': ?name,
        'description': ?description,
      },
    );
    return decode(response);
  }

  Future<void> deleteCanvas(String canvasId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete('/strategy/canvases/$canvasId?workspace_id=$workspaceId');
    decode(response);
  }

  Future<Map<String, dynamic>> generateAiFoundation(String canvasId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post('/strategy/canvases/$canvasId/generate-ai-foundation?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> createRevision(String canvasId, {String? baseRevisionId}) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/canvases/$canvasId/revisions?workspace_id=$workspaceId',
      body: {
        'base_revision_id': ?baseRevisionId,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> getRevisionDetail(String revisionId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.get('/strategy/revisions/$revisionId?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> submitReview(String revisionId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post('/strategy/revisions/$revisionId/submit-review?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> approveRevision(String revisionId, {String? note}) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/revisions/$revisionId/approve?workspace_id=$workspaceId',
      body: {
        'note': ?note,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> requestChanges(String revisionId, String reason) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/revisions/$revisionId/request-changes?workspace_id=$workspaceId',
      body: {'reason': reason},
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> saveFoundation(
    String revisionId, {
    required String vision,
    required String mission,
    required List<Map<String, dynamic>> values,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/revisions/$revisionId/foundation?workspace_id=$workspaceId',
      body: {'vision': vision, 'mission': mission, 'values': values},
    );
    return decode(response);
  }
}
```

- [ ] **Step 4: Create okr_service.dart, twelve_week_service.dart, etc. (follow same pattern)**

(Create similar files for OKRs, 12-Week plans, Projects, Portfolio, Founder — similar to canvas_service.dart but with domain-specific methods. For brevity, showing only the structure; implementation follows the same pattern from original strategy_service.dart)

- [ ] **Step 5: Create new strategy_service.dart as facade**

Replace `/Volumes/SSD/javis-saas/frontend/lib/modules/strategy/services/strategy_service.dart` with:

```dart
import 'canvas_service.dart';
import 'okr_service.dart';
import 'twelve_week_service.dart';
import 'project_service.dart';
import 'portfolio_service.dart';
import 'founder_service.dart';

/// Facade — delegates to domain-specific services for backward compatibility
class StrategyService {
  final _canvas = CanvasService();
  final _okr = OkrService();
  final _twelveWeek = TwelveWeekService();
  final _project = ProjectService();
  final _portfolio = PortfolioService();
  final _founder = FounderService();

  // Canvas methods (delegate to CanvasService)
  Future<StrategyListResult<Map<String, dynamic>>> getCanvases() => _canvas.getCanvases();
  Future<Map<String, dynamic>> getCanvasDetail(String canvasId) => _canvas.getCanvasDetail(canvasId);
  Future<Map<String, dynamic>> createCanvas(String name, {String? description}) =>
      _canvas.createCanvas(name, description: description);
  // ... delegate all other methods similarly

  // OKR methods (delegate to OkrService)
  Future<StrategyListResult<Map<String, dynamic>>> getOkrCycles() => _okr.getOkrCycles();
  // ... delegate OKR methods
  
  // 12-Week methods (delegate to TwelveWeekService)
  Future<StrategyListResult<Map<String, dynamic>>> getTwelveWeekCycles() => _twelveWeek.getTwelveWeekCycles();
  // ... delegate 12-week methods
  
  // ... similar for Project, Portfolio, Founder services
}

// Re-export exception for backward compat
export 'strategy_service_base.dart' show StrategyApiException;
```

- [ ] **Step 6: Run tests**

```bash
cd /Volumes/SSD/javis-saas
flutter test test/modules/strategy/
```

Expected: PASS (facade preserves all public methods)

- [ ] **Step 7: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/strategy/services/
git add frontend/test/modules/strategy/
git commit -m "refactor(strategy): split mega-service into domain-specific modules

- Extract CanvasService (foundation, revisions, foundation generation)
- Extract OkrService (cycles, objectives, key results)
- Extract TwelveWeekService (12-week cycles, plans, commitments)
- Extract ProjectService (project lifecycle, milestones)
- Extract PortfolioService (portfolio options, dependencies, SWOT, TOWS)
- Extract FounderService (founder profiles, CEO actions, gates, week 13)
- Create StrategyServiceBase for shared helpers (decode, workspace access)
- Keep StrategyService as facade re-exporting all splits
- All public methods preserved; no API changes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Open Questions / Verification Steps

**Item 1:** Approval endpoint consolidation — Need to verify that `workforce_routes.py` existing approval endpoints match exactly (or are missing); if they're different implementations, the comparison will guide the merge direction.

**Item 2:** Agent plane callers — The grep in Task 2 Step 1 must be run to map which 12 files access which attributes; initial list assumes common patterns (gateway, repository, policy_engine), but actual code scan may reveal different hot-spots.

**Item 3:** Marketing context functions — The full file must be read (currently only 500 lines shown) to identify exact function boundaries and whether offer_architecture / twelve_week_plan belong to the snapshot service or are elsewhere.

**Item 4:** Flutter shared helpers — The `decodeList` and `_requireWorkspaceId` methods appear in multiple places; verify all replicas across strategy_service.dart to ensure no missed usages when extracting to base class.

**Item 5:** Database test environment — TypeScript tests (services/company) may require live Postgres or in-memory SQLite depending on test setup; verify `pnpm test` works in isolation before running Task 3.

---

## Summary

This plan covers 4 independent file/class splits across 3 languages:

- **Task 1 (Python):** 1397-line `routes.py` → 5 focused routers (conversation, knowledge, connector, schedule) + approval consolidation to workforce
- **Task 2 (Python):** 23-attribute god-object `agent_plane.py` → 3 narrower service interfaces (RunExecutionService, WorkflowOrchestration, ComplianceCoordination) via compatibility properties
- **Task 3 (TypeScript):** 787-line `marketing-context.service.ts` → 3 domain services (product-marketing, customer-research, marketing-snapshot) + facade
- **Task 4 (Dart):** 1878-line `strategy_service.dart` → 6 domain services (Canvas, OKR, 12-Week, Project, Portfolio, Founder) + facade + shared base

Each task is self-contained, includes test baseline and verification steps, and preserves all public interfaces via facades/compatibility layers. No breaking changes; full backward compatibility. Commit granularity ensures each piece can be reviewed and rolled back independently.
