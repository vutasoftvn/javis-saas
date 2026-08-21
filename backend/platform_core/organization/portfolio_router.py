from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from core.auth import get_current_workspace_member
from db.models import WorkspaceMember
from core.authz import authorize
from platform_core.organization import portfolio_service
from platform_core.organization.portfolio_schemas import OperatingUnitCreate, OfferingCreate

router = APIRouter()

@router.post("/operating-units", status_code=status.HTTP_201_CREATED)
def create_operating_unit(
    workspace_id: int,
    data: OperatingUnitCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    authorize(member, "organization.manage")
    
    unit = portfolio_service.create_operating_unit(db, workspace_id, data)
    return {"id": str(unit.id), "slug": unit.slug, "name": unit.name}

@router.post("/offerings", status_code=status.HTTP_201_CREATED)
def create_offering(
    workspace_id: int,
    data: OfferingCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    authorize(member, "organization.manage")
    
    try:
        offering = portfolio_service.create_offering(db, workspace_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": str(offering.id), "slug": offering.slug, "name": offering.name}

@router.get("/scope-options")
def get_scope_options(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    try:
        return portfolio_service.get_scope_options(db, workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
