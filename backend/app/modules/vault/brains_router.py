from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, field_validator

from app.db.session import get_db
from app.db.models import Brain, WorkspaceMember
from app.core.auth import get_current_workspace_member

router = APIRouter()

class BrainCreateRequest(BaseModel):
    name: str
    slug: Optional[str] = None

class BrainUpdateRequest(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None

class BrainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    name: str
    slug: Optional[str] = None
    archived_at: Optional[datetime] = None
    created_at: datetime
    
    @field_validator("id", "workspace_id", mode="before")
    @classmethod
    def serialize_snowflake_id(cls, value: int | str) -> str:
        return str(value)

def get_brain_scoped(db: Session, brain_id: int, workspace_id: int) -> Brain:
    brain = db.query(Brain).filter(
        Brain.id == brain_id,
        Brain.workspace_id == workspace_id
    ).first()
    if not brain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brain not found")
    return brain

@router.get("", response_model=List[BrainResponse])
def list_brains(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    brains = db.query(Brain).filter(
        Brain.workspace_id == workspace_id,
        Brain.archived_at.is_(None)
    ).all()
    return brains

@router.post("", response_model=BrainResponse)
def create_brain(
    payload: BrainCreateRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    if member.role not in ["admin", "owner"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create brains")
        
    if payload.slug:
        existing = db.query(Brain).filter(
            Brain.workspace_id == workspace_id,
            Brain.slug == payload.slug
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already exists")

    brain = Brain(
        workspace_id=workspace_id,
        name=payload.name,
        slug=payload.slug
    )
    db.add(brain)
    db.commit()
    db.refresh(brain)
    return brain

@router.patch("/{brain_id}", response_model=BrainResponse)
def update_brain(
    brain_id: int,
    payload: BrainUpdateRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    if member.role not in ["admin", "owner"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        
    brain = get_brain_scoped(db, brain_id, workspace_id)
    
    if payload.name is not None:
        brain.name = payload.name
    if payload.slug is not None:
        existing = db.query(Brain).filter(
            Brain.workspace_id == workspace_id,
            Brain.slug == payload.slug,
            Brain.id != brain_id
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already exists")
        brain.slug = payload.slug
        
    db.commit()
    db.refresh(brain)
    return brain

@router.delete("/{brain_id}")
def archive_brain(
    brain_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    if member.role not in ["admin", "owner"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        
    brain = get_brain_scoped(db, brain_id, workspace_id)
    brain.archived_at = datetime.utcnow()
    db.commit()
    
    return {"status": "archived"}
