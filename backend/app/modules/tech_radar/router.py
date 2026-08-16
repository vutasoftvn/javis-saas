"""FastAPI Router for Technology Radar (Spec §104, §P5)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.iam.models import User
from app.core.auth import get_current_user
from app.modules.tech_radar.service import TechRadarService
from app.modules.tech_radar.models import TechnologyRadarItem

router = APIRouter(prefix="/api/v1/tech-radar", tags=["tech-radar"])


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
