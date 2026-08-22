"""FastAPI Router for Technology Radar (Spec §104, §P5)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.session import get_db
from platform_core.auth.models import User
from core.auth import get_current_user
from platform_core.tech_radar.service import TechRadarService
from platform_core.tech_radar.models import TechnologyRadarItem

router = APIRouter()


class CreateRadarItemRequest(BaseModel):
    workspace_id: int
    name: str
    category: str
    status: str = "WATCH"
    maturity: str = "experimental"
    potential: str = "high"
    cosa_use: str = "pattern"
    integration: str = "no"
    description: Optional[str] = None
    last_reviewed: Optional[str] = None


class UpdateRadarItemRequest(BaseModel):
    status: Optional[str] = None
    maturity: Optional[str] = None
    potential: Optional[str] = None
    cosa_use: Optional[str] = None
    integration: Optional[str] = None
    description: Optional[str] = None
    last_reviewed: Optional[str] = None


class RadarItemResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    category: str
    status: str
    maturity: str
    potential: str
    cosa_use: str
    integration: str
    description: Optional[str]
    last_reviewed: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_orm_model(cls, item: TechnologyRadarItem) -> "RadarItemResponse":
        return cls(
            id=str(item.id),
            workspace_id=str(item.workspace_id),
            name=item.name,
            category=item.category,
            status=item.status,
            maturity=item.maturity,
            potential=item.potential,
            cosa_use=item.cosa_use,
            integration=item.integration,
            description=item.description,
            last_reviewed=item.last_reviewed,
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat(),
        )


@router.get("", response_model=List[RadarItemResponse])
def list_radar_items(
    workspace_id: int = Query(...),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Technology Radar items by workspace with optional category and ring status filter."""
    items = TechRadarService.list_items(db, workspace_id, category, status)
    return [RadarItemResponse.from_orm_model(item) for item in items]


@router.post("", response_model=RadarItemResponse, status_code=status.HTTP_201_CREATED)
def create_radar_item(
    req: CreateRadarItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new technology radar item."""
    item = TechRadarService.create_item(
        db=db,
        workspace_id=req.workspace_id,
        name=req.name,
        category=req.category,
        status=req.status,
        maturity=req.maturity,
        potential=req.potential,
        cosa_use=req.cosa_use,
        integration=req.integration,
        description=req.description,
        last_reviewed=req.last_reviewed,
    )
    return RadarItemResponse.from_orm_model(item)


@router.patch("/{item_id}", response_model=RadarItemResponse)
def update_radar_item(
    item_id: int,
    req: UpdateRadarItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update status, maturity, or assessment details of a technology radar item."""
    try:
        item = TechRadarService.update_item(
            db=db,
            item_id=item_id,
            status=req.status,
            maturity=req.maturity,
            potential=req.potential,
            cosa_use=req.cosa_use,
            integration=req.integration,
            description=req.description,
            last_reviewed=req.last_reviewed,
        )
        return RadarItemResponse.from_orm_model(item)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/seed", response_model=List[RadarItemResponse])
def seed_default_radar(
    workspace_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed standard technology radar items from Spec §104 into workspace."""
    created = TechRadarService.seed_defaults(db, workspace_id)
    return [RadarItemResponse.from_orm_model(item) for item in created]

from sqlalchemy import func
from core.auth import get_current_workspace_member
from core.feature_flags import FLAG_TECH_FUNCTION_V13, require_flag
from db.models import WorkspaceMember
from integrations.devices.models import DeveloperJob
from founder_os.tasks.models import Task
from founder_os.outcomes.models import Outcome

@router.get("/status")
def get_tech_status(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Lấy thống kê trạng thái các Jobs, Tasks, Outcomes thuộc Function Kỹ thuật (TECH)."""
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_TECH_FUNCTION_V13, workspace_id)
    jobs = db.query(DeveloperJob.status, func.count(DeveloperJob.id)).filter(DeveloperJob.workspace_id == workspace_id).group_by(DeveloperJob.status).all()
    return {
        "function": "TECH",
        "jobs": {status: count for status, count in jobs},
        "tasks": db.query(Task).filter(Task.workspace_id == workspace_id, Task.function == "TECH").count(),
        "outcomes": db.query(Outcome).filter(Outcome.workspace_id == workspace_id, Outcome.function == "TECH").count(),
    }
