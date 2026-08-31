"""Knowledge ingestion routes for COSA Agent Platform."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

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
