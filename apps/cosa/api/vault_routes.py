"""Vault API Routes for COSA Agent Platform."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from apps.cosa.api.mvp_response import MvpSourceRef, mvp_item, mvp_list
from apps.cosa.api.vault_schemas import (
    ConfirmUploadRequest,
    CreateUploadTicketRequest,
    DeleteDocumentOut,
    KnowledgeGraphEdgeOut,
    KnowledgeGraphNodeOut,
    RetrievalHitOut,
    RetrievalQueryRequest,
    UploadTicketOut,
    VaultDocumentDetailOut,
    VaultDocumentOut,
    VaultDocumentVersionOut,
    VaultIndexedSourceOut,
    VaultKnowledgeGraphOut,
)
from apps.cosa.auth.dependency import (
    AuthenticatedIdentity,
    get_authenticated_identity,
    require_workspace_operator,
)
from apps.cosa.composition.agent_plane import CosaAgentPlane

router = APIRouter(prefix="/agent/vault", tags=["vault"])


def _get_plane(request: Request) -> CosaAgentPlane:
    plane = getattr(request.app.state, "plane", None) or getattr(request.app.state, "cosa_agent_plane", None)
    if plane is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CosaAgentPlane is not initialized",
        )
    return plane


# ─── Documents ───

@router.get("/documents")
async def list_documents(
    request: Request,
    state: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    records = await plane.vault_repository.list_documents(
        workspace_id=identity.workspace_id,
        state=state,
        limit=limit,
    )
    items = [
        VaultDocumentOut(
            document_id=str(r.document_id),
            workspace_id=r.workspace_id,
            title=r.title,
            kind=r.kind,
            state=r.state,
            current_version_id=str(r.current_version_id) if r.current_version_id else None,
            knowledge_source_id=str(r.knowledge_source_id) if r.knowledge_source_id else None,
            created_by=r.created_by,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in records
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="vault.documents")])


@router.post("/documents/upload-ticket")
async def create_upload_ticket(
    req: CreateUploadTicketRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    require_workspace_operator(identity)
    plane = _get_plane(request)

    # 1. Create a draft document record
    doc = await plane.vault_repository.create_draft(
        workspace_id=identity.workspace_id,
        title=req.file_name,
        kind="document",
        created_by=identity.principal_id,
    )

    ticket_id = f"tkt_{uuid4().hex[:12]}"
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    out = UploadTicketOut(
        ticket_id=ticket_id,
        document_id=str(doc.document_id),
        upload_url=f"/agent/vault/documents/{doc.document_id}/upload",
        expires_at=expires_at.isoformat(),
        max_bytes=req.size_bytes,
        media_type=req.media_type,
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="vault.documents")])


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found in workspace",
        )

    doc = await plane.vault_repository.get_document(identity.workspace_id, doc_uuid)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found in workspace",
        )

    versions = await plane.vault_repository.list_versions(identity.workspace_id, doc_uuid)
    v_items = [
        VaultDocumentVersionOut(
            version_id=str(v.version_id),
            workspace_id=v.workspace_id,
            document_id=str(v.document_id),
            object_ref=v.object_ref,
            checksum_sha256=v.checksum_sha256,
            size_bytes=v.size_bytes,
            source_uri=v.source_uri,
            created_by=v.created_by,
            created_at=v.created_at.isoformat(),
        )
        for v in versions
    ]

    out = VaultDocumentDetailOut(
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
        versions=v_items,
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="vault.documents")])


@router.post("/documents/{document_id}/confirm")
async def confirm_upload(
    document_id: str,
    req: ConfirmUploadRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    require_workspace_operator(identity)
    plane = _get_plane(request)
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found in workspace",
        )

    doc = await plane.vault_repository.get_document(identity.workspace_id, doc_uuid)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found in workspace",
        )

    # Append new version
    version_rec = await plane.vault_repository.append_version(
        workspace_id=identity.workspace_id,
        document_id=doc_uuid,
        object_ref={"bucket": "vault", "key": f"{identity.workspace_id}/{document_id}"},
        checksum_sha256=req.checksum_sha256,
        size_bytes=req.size_bytes,
        source_uri=f"vault://{identity.workspace_id}/{document_id}",
        created_by=identity.principal_id,
    )

    # Update document state to INDEXED or QUARANTINED
    updated_doc = await plane.vault_repository.update_document_state(
        workspace_id=identity.workspace_id,
        document_id=doc_uuid,
        state="INDEXED",
    )
    if updated_doc is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document state",
        )

    out = VaultDocumentOut(
        document_id=str(updated_doc.document_id),
        workspace_id=updated_doc.workspace_id,
        title=updated_doc.title,
        kind=updated_doc.kind,
        state=updated_doc.state,
        current_version_id=str(updated_doc.current_version_id) if updated_doc.current_version_id else None,
        knowledge_source_id=str(updated_doc.knowledge_source_id) if updated_doc.knowledge_source_id else None,
        created_by=updated_doc.created_by,
        created_at=updated_doc.created_at.isoformat(),
        updated_at=updated_doc.updated_at.isoformat(),
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="vault.documents")])


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    require_workspace_operator(identity)
    plane = _get_plane(request)
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found in workspace",
        )

    deleted = await plane.vault_repository.delete_document(identity.workspace_id, doc_uuid)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found in workspace",
        )

    out = DeleteDocumentOut(document_id=document_id, deleted=True)
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="vault.documents")])


# ─── Knowledge Graph & Sources & Retrieval ───

@router.get("/knowledge/graph")
async def get_knowledge_graph(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    graph = await plane.vault_repository.get_knowledge_graph(identity.workspace_id)
    out = VaultKnowledgeGraphOut(
        nodes=[
            KnowledgeGraphNodeOut(
                id=n.id,
                label=n.label,
                kind=n.kind,
                source_ref=n.source_ref,
                metadata=n.metadata,
            )
            for n in graph.nodes
        ],
        edges=[
            KnowledgeGraphEdgeOut(
                source_id=e.source_id,
                target_id=e.target_id,
                relation=e.relation,
                weight=e.weight,
            )
            for e in graph.edges
        ],
    )
    return mvp_item(out, [MvpSourceRef(kind="agent_db", ref="vault.knowledge_graph")])


@router.get("/knowledge/sources")
async def list_indexed_sources(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    # Read indexed documents as knowledge sources
    docs = await plane.vault_repository.list_documents(
        workspace_id=identity.workspace_id,
        state="INDEXED",
    )
    items = [
        VaultIndexedSourceOut(
            source_id=str(d.document_id),
            workspace_id=d.workspace_id,
            title=d.title,
            source_type=d.kind,
            status="INDEXED",
            chunk_count=1,
            indexed_at=d.updated_at.isoformat(),
        )
        for d in docs
    ]
    return mvp_list(items, [MvpSourceRef(kind="agent_db", ref="vault.documents")])


@router.post("/retrieval/query")
async def retrieval_query(
    req: RetrievalQueryRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    plane = _get_plane(request)
    # Search indexed documents matching query
    docs = await plane.vault_repository.list_documents(
        workspace_id=identity.workspace_id,
        state="INDEXED",
    )
    hits: list[RetrievalHitOut] = []
    q_lower = req.query.lower()
    for d in docs:
        if q_lower in d.title.lower():
            hits.append(
                RetrievalHitOut(
                    source_id=str(d.document_id),
                    title=d.title,
                    content=f"Document content for {d.title}",
                    score=0.95,
                    metadata={"kind": d.kind, "document_id": str(d.document_id)},
                )
            )

    return mvp_list(hits, [MvpSourceRef(kind="agent_db", ref="vault.knowledge_retrieval")])
