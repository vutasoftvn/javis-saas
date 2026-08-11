from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from pydantic import BaseModel

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember, WorkspaceDomain

router = APIRouter()

class DomainCreate(BaseModel):
    domain: str

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_domain(
    workspace_id: uuid.UUID,
    data: DomainCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    if member.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    existing = db.query(WorkspaceDomain).filter(WorkspaceDomain.domain == data.domain).first()
    if existing:
        raise HTTPException(status_code=400, detail="Domain already exists")
        
    domain_record = WorkspaceDomain(
        workspace_id=workspace_id,
        domain=data.domain,
        status="pending"
    )
    db.add(domain_record)
    db.commit()
    db.refresh(domain_record)
    
    return {
        "id": str(domain_record.id),
        "domain": domain_record.domain,
        "status": domain_record.status
    }

@router.get("/status")
def get_domain_status(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    domains = db.query(WorkspaceDomain).filter(WorkspaceDomain.workspace_id == workspace_id).all()
    return {
        "domains": [
            {
                "id": str(d.id),
                "domain": d.domain,
                "status": d.status
            } for d in domains
        ]
    }
