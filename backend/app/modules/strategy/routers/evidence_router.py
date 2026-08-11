import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import (
    WorkspaceMember,
    ContextPack,
    ContextPackSource,
    EvidenceItem,
)
from app.modules.strategy.strategy_canvas_service import StrategyCanvasService
from app.modules.strategy.schemas.evidence_schemas import (
    ContextPackCreate,
    ContextPackUpdate,
    EvidenceLinkRequest,
    EvidenceCreate,
)

router = APIRouter()


def _service(workspace_id: uuid.UUID, member: WorkspaceMember, db: Session) -> StrategyCanvasService:
    return StrategyCanvasService(db=db, user_id=member.user_id, workspace_id=workspace_id, role=member.role)


def _serialize_context_pack(pack: ContextPack, db: Optional[Session] = None) -> dict:
    linked_evidence_ids = []
    if db is not None:
        rows = db.query(ContextPackSource).filter(
            ContextPackSource.context_pack_id == pack.id,
            ContextPackSource.evidence_id.isnot(None),
        ).all()
        linked_evidence_ids = [str(r.evidence_id) for r in rows]
    return {
        "id": str(pack.id),
        "strategy_revision_id": str(pack.strategy_revision_id) if pack.strategy_revision_id else None,
        "business_context": pack.business_context,
        "internal_resources": pack.internal_resources,
        "status": pack.status,
        "approved_by": str(pack.approved_by) if pack.approved_by else None,
        "approved_at": pack.approved_at,
        "linked_evidence_ids": linked_evidence_ids,
    }


def _serialize_evidence(item: EvidenceItem) -> dict:
    return {
        "id": str(item.id),
        "title": item.title,
        "summary": item.summary,
        "source_type": item.source_type,
        "source_url_or_vault_uri": item.source_url_or_vault_uri,
        "published_at": item.published_at,
        "captured_at": item.captured_at,
        "reliability": item.reliability,
        "tags": item.tags,
    }


@router.post("/revisions/{revision_id}/context-packs")
def create_context_pack(
    revision_id: uuid.UUID,
    workspace_id: uuid.UUID,
    data: Optional[ContextPackCreate] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    pack = svc.create_context_pack(revision_id)
    return _serialize_context_pack(pack, db)


@router.put("/context-packs/{context_pack_id}")
def update_context_pack(
    context_pack_id: uuid.UUID,
    workspace_id: uuid.UUID,
    data: ContextPackUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    pack = svc.update_context_pack(
        context_pack_id,
        business_context=data.description,
        internal_resources=data.industry,
    )
    if not pack:
        raise HTTPException(status_code=404, detail="Context Pack not found")
    return _serialize_context_pack(pack, db)


@router.post("/context-packs/{context_pack_id}/evidence")
def link_evidence_to_context_pack(
    context_pack_id: uuid.UUID,
    workspace_id: uuid.UUID,
    data: EvidenceLinkRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    pack = svc.link_evidence(context_pack_id, data.evidence_ids)
    if not pack:
        raise HTTPException(status_code=404, detail="Context Pack not found")
    return _serialize_context_pack(pack, db)


@router.post("/context-packs/{context_pack_id}/approve")
def approve_context_pack(
    context_pack_id: uuid.UUID,
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    pack = svc.approve_context_pack(context_pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Context Pack not found")
    return _serialize_context_pack(pack, db)


@router.post("/evidence")
def create_evidence(
    workspace_id: uuid.UUID,
    data: EvidenceCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    item = svc.create_evidence(
        title=data.title,
        summary=data.content,
        source_type=data.source_type,
        source_url_or_vault_uri=data.source_url,
        tags=data.tags,
    )
    return _serialize_evidence(item)


@router.get("/evidence")
def list_evidence(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    items = svc.list_evidence()
    return {"evidence": [_serialize_evidence(i) for i in items]}
