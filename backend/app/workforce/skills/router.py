"""FastAPI Router for Global Skill Registry & Lifecycle Management (Spec §61, §62, §P5)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.platform.auth.models import User
from app.core.auth import get_current_user
from app.workforce.skills.service import SkillLifecycleService
from app.workforce.skills.models import SkillRegistryItem

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


# Schemas
class CreateSkillCandidateRequest(BaseModel):
    workspace_id: int
    name: str
    domain: str
    instructions: str
    description: str = ""
    scope: List[str] = Field(default_factory=list)
    tool_permissions: List[str] = Field(default_factory=list)
    required_context: List[str] = Field(default_factory=list)
    created_by_agent: Optional[str] = None


class TrajectoryCandidateRequest(BaseModel):
    workspace_id: int
    domain: str
    proposed_name: str
    extracted_sop: str
    mission_id: Optional[str] = None
    run_id: Optional[int] = None
    tools_used: List[str] = Field(default_factory=list)


class EvaluateSkillRequest(BaseModel):
    eval_score: float = Field(ge=0.0, le=1.0)
    eval_details: Optional[Dict[str, Any]] = None


class DeprecateSkillRequest(BaseModel):
    reason: Optional[str] = None


class SkillFeedbackRequest(BaseModel):
    success: bool
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class SkillItemResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    domain: str
    version: str
    status: str
    description: str
    instructions: str
    scope: List[str]
    tool_permissions: List[str]
    required_context: List[str]
    success_rate: float
    usage_count: int
    positive_feedback: int
    negative_feedback: int
    created_by_agent: Optional[str]
    approved_by_user_id: Optional[str]
    approved_at: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_orm_model(cls, item: SkillRegistryItem) -> "SkillItemResponse":
        return cls(
            id=str(item.id),
            workspace_id=str(item.workspace_id),
            name=item.name,
            domain=item.domain,
            version=item.version,
            status=item.status,
            description=item.description or "",
            instructions=item.instructions or "",
            scope=item.scope or [],
            tool_permissions=item.tool_permissions or [],
            required_context=item.required_context or [],
            success_rate=item.success_rate,
            usage_count=item.usage_count,
            positive_feedback=item.positive_feedback,
            negative_feedback=item.negative_feedback,
            created_by_agent=item.created_by_agent,
            approved_by_user_id=str(item.approved_by_user_id) if item.approved_by_user_id else None,
            approved_at=item.approved_at.isoformat() if item.approved_at else None,
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat(),
        )


@router.get("", response_model=List[SkillItemResponse])
def list_skills(
    workspace_id: int = Query(...),
    domain: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List skills for workspace with optional domain and status filters."""
    items = SkillLifecycleService.list_skills(db, workspace_id, domain, status)
    return [SkillItemResponse.from_orm_model(item) for item in items]


@router.get("/{skill_id}", response_model=SkillItemResponse)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single skill by ID."""
    item = db.query(SkillRegistryItem).filter(SkillRegistryItem.id == skill_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Skill not found")
    return SkillItemResponse.from_orm_model(item)


@router.post("/candidates", response_model=SkillItemResponse, status_code=status.HTTP_201_CREATED)
def create_skill_candidate(
    req: CreateSkillCandidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new skill candidate."""
    try:
        item = SkillLifecycleService.register_skill_candidate(
            db=db,
            workspace_id=req.workspace_id,
            name=req.name,
            domain=req.domain,
            instructions=req.instructions,
            description=req.description,
            scope=req.scope,
            tool_permissions=req.tool_permissions,
            required_context=req.required_context,
            created_by_agent=req.created_by_agent,
        )
        return SkillItemResponse.from_orm_model(item)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/trajectory-candidate")
def create_from_trajectory(
    req: TrajectoryCandidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract and scan learning candidate from completed mission trajectory."""
    cand = SkillLifecycleService.create_candidate_from_trajectory(
        db=db,
        workspace_id=req.workspace_id,
        domain=req.domain,
        proposed_name=req.proposed_name,
        extracted_sop=req.extracted_sop,
        mission_id=req.mission_id,
        run_id=req.run_id,
        tools_used=req.tools_used,
    )
    return {
        "id": str(cand.id),
        "domain": cand.domain,
        "proposed_name": cand.proposed_name,
        "pii_scan_passed": cand.pii_scan_passed,
        "secret_scan_passed": cand.secret_scan_passed,
        "safety_notes": cand.safety_notes,
        "status": cand.status,
    }


@router.post("/{skill_id}/evaluate", response_model=SkillItemResponse)
def evaluate_skill(
    skill_id: int,
    req: EvaluateSkillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record evaluation score for a skill candidate."""
    try:
        item = SkillLifecycleService.evaluate_skill(db, skill_id, req.eval_score, req.eval_details)
        return SkillItemResponse.from_orm_model(item)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{skill_id}/promote", response_model=SkillItemResponse)
def promote_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Promote an evaluated skill to active production status.
    
    INVARIANT ENFORCEMENT:
    NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS.
    Only authenticated human users can promote.
    """
    try:
        item = SkillLifecycleService.promote_skill(
            db=db,
            skill_id=skill_id,
            approved_by_user_id=current_user.id,
        )
        return SkillItemResponse.from_orm_model(item)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{skill_id}/deprecate", response_model=SkillItemResponse)
def deprecate_skill(
    skill_id: int,
    req: DeprecateSkillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deprecate a skill."""
    try:
        item = SkillLifecycleService.deprecate_skill(db, skill_id, current_user.id, req.reason)
        return SkillItemResponse.from_orm_model(item)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{skill_id}/feedback", response_model=SkillItemResponse)
def record_skill_feedback(
    skill_id: int,
    req: SkillFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record runtime feedback/rating for a skill run."""
    try:
        item = SkillLifecycleService.record_usage(db, skill_id, req.success, req.rating)
        return SkillItemResponse.from_orm_model(item)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
