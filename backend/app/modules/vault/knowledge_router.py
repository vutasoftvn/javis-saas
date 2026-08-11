from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember, Brain
from app.modules.vault import knowledge_service

router = APIRouter()


class KnowledgeObjectCreate(BaseModel):
    title: str
    content: Optional[str] = None
    object_type: Optional[str] = "note"
    status: Optional[str] = "capture"
    vault_document_id: Optional[int] = None


class KnowledgePromoteRequest(BaseModel):
    target_status: Optional[str] = "approved"


def _verify_brain_workspace(db: Session, brain_id: int, workspace_id: int) -> Brain:
    brain = db.query(Brain).filter(Brain.id == brain_id, Brain.workspace_id == workspace_id).first()
    if not brain:
        raise HTTPException(status_code=404, detail="Brain not found or access denied")
    return brain


@router.post("/{brain_id}/knowledge", status_code=status.HTTP_201_CREATED)
def create_knowledge_item(
    brain_id: int,
    workspace_id: int,
    data: KnowledgeObjectCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    _verify_brain_workspace(db=db, brain_id=brain_id, workspace_id=workspace_id)

    obj = knowledge_service.create_knowledge_object(
        db=db,
        workspace_id=workspace_id,
        brain_id=brain_id,
        title=data.title,
        content=data.content,
        object_type=data.object_type or "note",
        status=data.status or "capture",
        vault_document_id=data.vault_document_id,
        generated_by=member.user_id,
    )
    return {
        "id": str(obj.id),
        "brain_id": str(obj.brain_id),
        "title": obj.title,
        "object_type": obj.object_type,
        "status": obj.status,
        "created_at": obj.created_at.isoformat(),
    }


@router.get("/{brain_id}/knowledge")
def list_knowledge_items(
    brain_id: int,
    workspace_id: int,
    type_filter: Optional[str] = Query(None, alias="type"),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = 50,
    offset: int = 0,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    _verify_brain_workspace(db=db, brain_id=brain_id, workspace_id=workspace_id)

    l = int(limit) if isinstance(limit, (int, str)) and str(limit).isdigit() else 50
    o = int(offset) if isinstance(offset, (int, str)) and str(offset).isdigit() else 0

    items = knowledge_service.list_knowledge_objects(
        db=db,
        brain_id=brain_id,
        workspace_id=workspace_id,
        object_type=type_filter,
        status=status_filter,
        limit=l,
        offset=o,
    )
    return {
        "total": len(items),
        "items": [
            {
                "id": str(i.id),
                "title": i.title,
                "object_type": i.object_type,
                "status": i.status,
                "created_at": i.created_at.isoformat(),
            }
            for i in items
        ],
    }


@router.get("/{brain_id}/knowledge/{object_id}")
def get_knowledge_item(
    brain_id: int,
    object_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    _verify_brain_workspace(db=db, brain_id=brain_id, workspace_id=workspace_id)

    obj = knowledge_service.get_knowledge_object(
        db=db,
        object_id=object_id,
        brain_id=brain_id,
        workspace_id=workspace_id,
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Knowledge object not found")

    return {
        "id": str(obj.id),
        "brain_id": str(obj.brain_id),
        "title": obj.title,
        "content": obj.content,
        "object_type": obj.object_type,
        "status": obj.status,
        "confidence": obj.confidence,
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
    }


@router.get("/{brain_id}/knowledge/{object_id}/backlinks")
def get_knowledge_backlinks(
    brain_id: int,
    object_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    _verify_brain_workspace(db=db, brain_id=brain_id, workspace_id=workspace_id)

    backlinks = knowledge_service.get_backlinks(
        db=db,
        object_id=object_id,
        brain_id=brain_id,
        workspace_id=workspace_id,
    )
    return {
        "total": len(backlinks),
        "backlinks": backlinks,
    }


@router.post("/{brain_id}/knowledge/{object_id}/promote")
def promote_knowledge_item(
    brain_id: int,
    object_id: int,
    workspace_id: int,
    data: Optional[KnowledgePromoteRequest] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    _verify_brain_workspace(db=db, brain_id=brain_id, workspace_id=workspace_id)

    try:
        obj = knowledge_service.promote_knowledge_object(
            db=db,
            object_id=object_id,
            brain_id=brain_id,
            workspace_id=workspace_id,
            user_id=member.user_id,
            target_status=data.target_status if data and data.target_status else "approved",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "status": "promoted",
        "object_id": str(obj.id),
        "new_status": obj.status,
    }
