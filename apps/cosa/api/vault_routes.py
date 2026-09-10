"""Vault API Routes for COSA Agent Platform.

Task 7 (plan local-first-enterprise-knowledge) — reopen với local semantics
thật: WorkspaceDocumentStore (Task 3) + LocalIngestionRepository (Task 5) +
KnowledgeAuthorization (Task 6). Server-owned upload ticket (không nhận
workspace/object path/checksum/size từ client), stream upload
(`request.stream()`, không `await request.body()`), không bao giờ trả local
path/object key/ticket secret ra khỏi response tạo ticket.

Retrieval (`/retrieval/query`) vẫn giữ 501 — Task 8 mới có authorized
retrieval contract thật.
"""

from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from apps.cosa.api.mvp_response import MvpSourceRef, MvpSuccess, mvp_item, mvp_list
from apps.cosa.api.vault_schemas import (
    ArchiveOrPurgeOut,
    CompleteUploadOut,
    CreateDocumentRequest,
    CreateDocumentUploadOut,
    LegalHoldOut,
    LegalHoldRequest,
    RetrievalQueryRequest,
    ReviewDocumentOut,
    ReviewDocumentRequest,
    VaultDocumentOut,
)
from apps.cosa.auth.dependency import (
    AuthenticatedIdentity,
    get_authenticated_identity,
)
from apps.cosa.knowledge_ingestion.authorization import KnowledgeAuthorization
from apps.cosa.knowledge_ingestion.contracts import (
    MIME_TYPE_LIMITS,
    knowledge_ingestion_enabled,
)

router = APIRouter(prefix="/agent/vault", tags=["vault"])

_WORKSPACE_OPERATOR_ROLES = frozenset({"founder", "co-founder", "admin"})

# Task 12 (plan local-first-enterprise-knowledge) — mọi route enabled:true
# phải trả MvpSuccess envelope ({"data":..., "meta":...}) — MvpRequestClient
# (frontend Dart) reject thẳng bất kỳ response nào thiếu "data"/"meta", cùng
# convention workforce_routes.py đã dùng từ trước (bug thật phát hiện lúc làm
# Task 12: 8 route vault ban đầu trả Pydantic model trần, chưa từng test qua
# MvpRequestClient thật nên không ai bắt được cho tới lúc build VaultService).
_VAULT_SOURCE = MvpSourceRef(kind="agent_db", ref="vault.documents")

# Message cố tình chung chung — không tiết lộ storage topology (tên bucket,
# provider, schema DB...) cho client.
_NOT_RELEASED_DETAIL = "Vault document ingestion is not released"


def _not_released() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_NOT_RELEASED_DETAIL,
    )


def _get_plane(request: Request) -> Any:
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError("CosaAgentPlane chưa sẵn sàng — app.state.plane rỗng.")
    return plane


def _feature_disabled() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Knowledge ingestion not enabled"
    )


def _document_to_out(doc: Any, decision: Any | None = None) -> VaultDocumentOut:
    return VaultDocumentOut(
        document_id=str(doc.document_id),
        workspace_id=doc.workspace_id,
        title=doc.title,
        kind=doc.kind,
        state=doc.state,
        current_version_id=str(doc.current_version_id) if doc.current_version_id else None,
        knowledge_source_id=str(doc.knowledge_source_id) if doc.knowledge_source_id else None,
        created_by=doc.created_by,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
        can_review=bool(decision.review) if decision is not None else False,
        can_publish=bool(decision.publish) if decision is not None else False,
        can_manage=bool(decision.manage) if decision is not None else False,
    )


def _parse_document_id(document_id: str) -> UUID:
    try:
        return UUID(document_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found") from e


# ─── Documents ───


@router.get("/documents", response_model=MvpSuccess[list[VaultDocumentOut]])
async def list_documents(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[VaultDocumentOut]]:
    plane = _get_plane(request)
    docs = await plane.vault_repository.list_authorized_documents(
        identity.workspace_id, identity.principal_id, {identity.role_id}
    )
    auth = KnowledgeAuthorization(plane.vault_repository)
    out: list[VaultDocumentOut] = []
    for d in docs:
        decision = await auth.resolve(identity, d.document_id)
        out.append(_document_to_out(d, decision))
    return mvp_list(out, [_VAULT_SOURCE])


@router.post("/documents", status_code=201, response_model=MvpSuccess[CreateDocumentUploadOut])
async def create_document(
    request: Request,
    req: CreateDocumentRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[CreateDocumentUploadOut]:
    if not knowledge_ingestion_enabled():
        raise _feature_disabled()
    plane = _get_plane(request)
    deps = getattr(plane, "knowledge_ingestion_deps", None)
    if deps is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")

    from agent.vault.models import VaultClassification, VaultVisibility

    try:
        classification = (
            VaultClassification(req.classification)
            if req.classification
            else VaultClassification.INTERNAL
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail="invalid classification") from e

    # Task 6 Step 4 — upload tạo document PRIVATE cho member trừ khi 1 manager
    # (workspace operator) tường minh yêu cầu workspace/role visibility.
    is_operator = (identity.role_id or "").lower() in _WORKSPACE_OPERATOR_ROLES
    requested_visibility = req.visibility
    if requested_visibility and is_operator:
        try:
            visibility = VaultVisibility(requested_visibility)
        except ValueError as e:
            raise HTTPException(status_code=422, detail="invalid visibility") from e
    else:
        visibility = VaultVisibility.PRIVATE

    document = await plane.vault_repository.create_draft(
        identity.workspace_id,
        req.title,
        created_by=identity.principal_id,
        classification=classification,
        visibility=visibility,
    )

    max_bytes = MIME_TYPE_LIMITS.get(req.media_type, 10 * 1024 * 1024)
    upload_id = str(document.document_id)
    ticket = await deps.store.issue_ticket(identity.workspace_id, upload_id, max_bytes=max_bytes)

    upload_url = (
        f"/agent/vault/uploads/{upload_id}/content"
        f"?workspace_id={identity.workspace_id}&secret={ticket.secret}"
    )
    return mvp_item(
        CreateDocumentUploadOut(
            document_id=upload_id,
            upload_id=upload_id,
            upload_url=upload_url,
            expires_at=ticket.expires_at.isoformat(),
            max_bytes=max_bytes,
        ),
        [_VAULT_SOURCE],
    )


@router.put("/uploads/{upload_id}/content", status_code=204, response_model=None)
async def upload_content(request: Request, upload_id: str) -> None:
    """Ticket secret (query param `secret`) LÀ authorization cho action này —
    one-time, short-lived, không phải phiên đăng nhập thường. Stream thật qua
    `request.stream()`, không buffer toàn bộ body trước."""
    if not knowledge_ingestion_enabled():
        raise _feature_disabled()
    workspace_id = request.query_params.get("workspace_id")
    secret = request.query_params.get("secret")
    if not workspace_id or not secret:
        raise HTTPException(status_code=400, detail="missing workspace_id or secret")

    plane = _get_plane(request)
    deps = getattr(plane, "knowledge_ingestion_deps", None)
    if deps is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")

    chunks = [chunk async for chunk in request.stream()]
    from apps.cosa.knowledge_ingestion.workspace_store import (
        UploadTicketExpired,
        UploadTicketNotFound,
    )

    try:
        await deps.store.write_upload_stream(workspace_id, upload_id, secret, chunks)
    except (UploadTicketNotFound, UploadTicketExpired) as e:
        raise HTTPException(status_code=404, detail="upload ticket not found") from e
    except ValueError as e:
        raise HTTPException(status_code=413, detail="upload too large") from e


@router.post("/uploads/{upload_id}/complete", response_model=MvpSuccess[CompleteUploadOut])
async def complete_upload(
    request: Request,
    upload_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[CompleteUploadOut]:
    if not knowledge_ingestion_enabled():
        raise _feature_disabled()
    plane = _get_plane(request)
    deps = getattr(plane, "knowledge_ingestion_deps", None)
    if deps is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")

    from apps.cosa.knowledge_ingestion.workspace_store import UploadTicketNotFound

    try:
        quarantined = await deps.store.finalize_upload(identity.workspace_id, upload_id)
    except UploadTicketNotFound as e:
        raise HTTPException(status_code=404, detail="upload not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail="upload not completed") from e

    # Task 3's WorkspaceDocumentStore không tự sniff MIME (chỉ hash/size) —
    # sniff từ magic bytes ở đây, cùng logic InMemoryDocumentObjectStore đã
    # dùng trước Task 3 (server-derived, không tin client khai báo).
    from apps.cosa.knowledge_ingestion.object_store import InMemoryDocumentObjectStore

    content = await deps.store.read_quarantine_object(
        identity.workspace_id, quarantined.quarantine_relative_path
    )
    detected_media_type = InMemoryDocumentObjectStore()._sniff_mime_type(content)

    await deps.local_repository.create_queued(
        identity.workspace_id,
        upload_id,
        quarantine_relative_path=quarantined.quarantine_relative_path,
        declared_media_type=None,
        detected_media_type=detected_media_type,
        source_sha256=quarantined.source_sha256,
        size_bytes=quarantined.size_bytes,
        created_by=identity.principal_id,
    )

    if getattr(plane, "scheduler", None) is not None:
        await plane.scheduler.schedule(
            target_spec_id="cosa.agents.operations",
            input_payload={
                "task_type": "knowledge_ingestion",
                "workspace_id": identity.workspace_id,
                "upload_id": upload_id,
            },
        )

    return mvp_item(CompleteUploadOut(upload_id=upload_id, state="QUEUED"), [_VAULT_SOURCE])


@router.get("/documents/{document_id}", response_model=MvpSuccess[VaultDocumentOut])
async def get_document(
    request: Request,
    document_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[VaultDocumentOut]:
    plane = _get_plane(request)
    doc_uuid = _parse_document_id(document_id)
    auth = KnowledgeAuthorization(plane.vault_repository)
    decision = await auth.resolve(identity, doc_uuid)
    if not decision.discover:
        raise HTTPException(status_code=404, detail="not found")
    document = await plane.vault_repository.get_document(identity.workspace_id, doc_uuid)
    if document is None:
        raise HTTPException(status_code=404, detail="not found")
    return mvp_item(_document_to_out(document, decision), [_VAULT_SOURCE])


@router.post("/documents/{document_id}/review", response_model=MvpSuccess[ReviewDocumentOut])
async def review_document(
    request: Request,
    document_id: str,
    req: ReviewDocumentRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[ReviewDocumentOut]:
    """Reject 1 candidate đang REVIEW_PENDING — publish dùng route riêng
    `/documents/{document_id}/publish` (yêu cầu `publish`, không phải
    `review`, đúng Task 6 Step 4: 2 permission tách biệt)."""
    plane = _get_plane(request)
    doc_uuid = _parse_document_id(document_id)
    auth = KnowledgeAuthorization(plane.vault_repository)
    decision = await auth.resolve(identity, doc_uuid)
    if not decision.review:
        raise HTTPException(status_code=404, detail="not found")

    document = await plane.vault_repository.get_document(identity.workspace_id, doc_uuid)
    if document is None:
        raise HTTPException(status_code=404, detail="not found")

    deps = getattr(plane, "knowledge_ingestion_deps", None)
    if deps is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")

    upload_id = str(doc_uuid)
    ok = await deps.local_repository.reject(identity.workspace_id, upload_id, "reviewer_rejected")
    if not ok:
        raise HTTPException(status_code=409, detail="candidate not in review_pending state")
    return mvp_item(ReviewDocumentOut(upload_id=upload_id, state="REJECTED"), [_VAULT_SOURCE])


@router.post("/documents/{document_id}/publish", response_model=MvpSuccess[ReviewDocumentOut])
async def publish_document(
    request: Request,
    document_id: str,
    req: ReviewDocumentRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[ReviewDocumentOut]:
    plane = _get_plane(request)
    doc_uuid = _parse_document_id(document_id)
    auth = KnowledgeAuthorization(plane.vault_repository)
    decision = await auth.resolve(identity, doc_uuid)
    if not decision.publish:
        raise HTTPException(status_code=404, detail="not found")

    document = await plane.vault_repository.get_document(identity.workspace_id, doc_uuid)
    if document is None:
        raise HTTPException(status_code=404, detail="not found")

    deps = getattr(plane, "knowledge_ingestion_deps", None)
    if deps is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")

    upload_id = str(doc_uuid)
    attempt_state = await deps.local_repository.get_state(identity.workspace_id, upload_id)
    if attempt_state is None or attempt_state.value != "REVIEW_PENDING":
        raise HTTPException(status_code=409, detail="candidate not in review_pending state")

    # Copy quarantine content vào Vault CÓ KIỂM CHỨNG trước khi ghi nhận
    # version — publish() KHÔNG tự copy file (Task 5 docstring).
    quarantine_ref = await deps.local_repository.get_quarantine_relative_path(
        identity.workspace_id, upload_id
    )
    if not quarantine_ref:
        raise HTTPException(status_code=500, detail="ingestion attempt missing storage reference")

    # Bug tìm thấy trong lúc làm Task 11 (purge): trước đây dùng
    # `document.document_id` làm "version_id" cho `promote_to_vault()` —
    # HẰNG SỐ qua mọi lần publish của cùng 1 document, nên republish (1
    # document nhiều version theo thời gian) ghi đè LÊN CÙNG 1 file vật lý
    # mỗi lần, trong khi mỗi version DB row lại có version_id riêng — version
    # cũ trong DB trỏ object_ref đúng "relative_ref" nhưng nội dung file đã bị
    # version mới ghi đè (checksum cũ không còn khớp file thật). Generate
    # đúng 1 UUID version_id TRƯỚC, dùng CHO CẢ physical filename lẫn DB row
    # — mỗi version có file vật lý riêng biệt, và purge (Task 11) mới xoá
    # đúng file theo version_id thật.
    version_uuid = uuid4()
    version_id = str(version_uuid)
    object_ref = await deps.store.promote_to_vault(
        identity.workspace_id, version_id, quarantine_ref
    )
    source_sha256, size_bytes = await deps.local_repository.get_source_metadata(
        identity.workspace_id, upload_id
    )

    version = await plane.vault_repository.append_version(
        workspace_id=identity.workspace_id,
        document_id=doc_uuid,
        object_ref={"relative_ref": object_ref.relative_ref},
        checksum_sha256=source_sha256 or "",
        size_bytes=size_bytes or 0,
        source_uri=f"workspaces/{identity.workspace_id}/vault/{version_id}",
        created_by=identity.principal_id,
        version_id=version_uuid,
    )
    await plane.vault_repository.update_document_state(identity.workspace_id, doc_uuid, "PUBLISHED")

    ok = await deps.local_repository.publish(
        identity.workspace_id,
        upload_id,
        vault_document_id=str(doc_uuid),
        vault_version_id=str(version.version_id),
    )
    if not ok:
        raise HTTPException(status_code=409, detail="publish race — attempt already progressed")

    return mvp_item(ReviewDocumentOut(upload_id=upload_id, state="PUBLISHED"), [_VAULT_SOURCE])


@router.delete("/documents/{document_id}", response_model=MvpSuccess[ArchiveOrPurgeOut])
async def delete_document(
    request: Request,
    document_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[ArchiveOrPurgeOut]:
    """Archive — KHÔNG xoá file trong request này (Task 7 Step 4: archive/
    purge schedule background durable work, trả 202-style accepted)."""
    plane = _get_plane(request)
    doc_uuid = _parse_document_id(document_id)
    auth = KnowledgeAuthorization(plane.vault_repository)
    decision = await auth.resolve(identity, doc_uuid)
    if not decision.manage:
        raise HTTPException(status_code=404, detail="not found")

    updated = await plane.vault_repository.update_document_state(
        identity.workspace_id, doc_uuid, "ARCHIVED"
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return mvp_item(ArchiveOrPurgeOut(document_id=document_id, accepted=True), [_VAULT_SOURCE])


@router.post("/documents/{document_id}/revoke", response_model=MvpSuccess[ArchiveOrPurgeOut])
async def revoke_document(
    request: Request,
    document_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[ArchiveOrPurgeOut]:
    """Revoke a published document."""
    plane = _get_plane(request)
    doc_uuid = _parse_document_id(document_id)
    auth = KnowledgeAuthorization(plane.vault_repository)
    decision = await auth.resolve(identity, doc_uuid)
    if not decision.manage:
        raise HTTPException(status_code=404, detail="not found")

    updated = await plane.vault_repository.update_document_state(
        identity.workspace_id, doc_uuid, "REVOKED"
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return mvp_item(ArchiveOrPurgeOut(document_id=document_id, accepted=True), [_VAULT_SOURCE])


@router.post(
    "/documents/{document_id}/purge",
    status_code=202,
    response_model=MvpSuccess[ArchiveOrPurgeOut],
)
async def purge_document(
    request: Request,
    document_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[ArchiveOrPurgeOut]:
    """Task 11 — 2 giai đoạn: đồng bộ trong request chỉ chuyển
    `PURGE_PENDING` (đã loại khỏi retrieval ngay — `retrieve_authorized_
    citations()` chỉ đọc `state='PUBLISHED'`), dọn dẹp vật lý thật (chunk/
    embedding/file) chạy sau qua scheduler durable. `legal_hold=true` chặn
    hoàn toàn (409), không có cách nào bypass qua route này."""
    plane = _get_plane(request)
    doc_uuid = _parse_document_id(document_id)
    auth = KnowledgeAuthorization(plane.vault_repository)
    decision = await auth.resolve(identity, doc_uuid)
    if not decision.manage:
        raise HTTPException(status_code=404, detail="not found")

    deps = getattr(plane, "knowledge_ingestion_deps", None)
    if deps is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")

    from apps.cosa.knowledge_ingestion.purge import PurgeBlocked, VaultPurgeService

    purge_service = VaultPurgeService(
        plane.vault_repository, plane.knowledge_ingestion_service, deps.store
    )
    try:
        await purge_service.request_purge(identity.workspace_id, doc_uuid, identity.principal_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="not found") from e
    except PurgeBlocked as e:
        raise HTTPException(status_code=409, detail="document is under legal hold") from e

    if getattr(plane, "scheduler", None) is not None:
        await plane.scheduler.schedule(
            target_spec_id="cosa.agents.operations",
            input_payload={
                "task_type": "vault_purge",
                "workspace_id": identity.workspace_id,
                "document_id": document_id,
            },
        )

    return mvp_item(ArchiveOrPurgeOut(document_id=document_id, accepted=True), [_VAULT_SOURCE])


@router.post("/documents/{document_id}/legal-hold", response_model=MvpSuccess[LegalHoldOut])
async def set_legal_hold(
    request: Request,
    document_id: str,
    req: LegalHoldRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[LegalHoldOut]:
    """Gap ghi nhận ở Task 11 (`docs/operations/local-knowledge-runbook.md`)
    — trước đây `VaultPurgeService.set_legal_hold()` chỉ gọi được qua script
    nội bộ, không có route HTTP nào. `legal_hold=true` chặn `purge` hoàn
    toàn (409, xem `purge_document`) — cùng mức quyền `manage` với archive/
    purge, không có role "legal/compliance" riêng trong hệ thống hiện tại."""
    plane = _get_plane(request)
    doc_uuid = _parse_document_id(document_id)
    auth = KnowledgeAuthorization(plane.vault_repository)
    decision = await auth.resolve(identity, doc_uuid)
    if not decision.manage:
        raise HTTPException(status_code=404, detail="not found")

    deps = getattr(plane, "knowledge_ingestion_deps", None)
    if deps is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="not ready")

    from apps.cosa.knowledge_ingestion.purge import VaultPurgeService

    purge_service = VaultPurgeService(
        plane.vault_repository, plane.knowledge_ingestion_service, deps.store
    )
    await purge_service.set_legal_hold(
        identity.workspace_id, doc_uuid, req.legal_hold, set_by=identity.principal_id
    )

    return mvp_item(
        LegalHoldOut(document_id=document_id, legal_hold=req.legal_hold), [_VAULT_SOURCE]
    )


# ─── Knowledge Graph & Sources & Retrieval ───


@router.get("/knowledge/graph", response_model=None)
async def get_knowledge_graph(
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> NoReturn:
    raise _not_released()


@router.get("/knowledge/sources", response_model=None)
async def list_indexed_sources(
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> NoReturn:
    raise _not_released()


@router.post("/retrieval/query", response_model=None)
async def retrieval_query(
    req: RetrievalQueryRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> NoReturn:
    raise _not_released()
