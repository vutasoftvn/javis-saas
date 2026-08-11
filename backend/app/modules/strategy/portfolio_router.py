from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.core.feature_flags import (
    require_flag,
    FLAG_PORTFOLIO_V12,
    FLAG_SHARED_PESTEL_V12,
    FLAG_PORTFOLIO_SWOT_TOWS_V12,
    FLAG_CAPACITY_PLANNER_V12,
    FLAG_FOUNDER_ATTENTION_V12,
    FLAG_PORTFOLIO_CYCLE_V12,
)
from app.db.models import WorkspaceMember
from app.modules.strategy.portfolio_service import (
    PortfolioService,
    PortfolioDetectorService,
)
from app.modules.strategy.portfolio_advanced_service import PortfolioAdvancedService
from app.modules.strategy.portfolio_cycle_service import PortfolioCycleService



router = APIRouter()


class PortfolioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    strategic_focus: Optional[str] = None
    brain_id: Optional[int] = None


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    strategic_focus: Optional[str] = None
    status: Optional[str] = None


class PortfolioProjectAdd(BaseModel):
    project_id: int
    strategic_priority: Optional[str] = "core"
    capacity_allocation: Optional[float] = 0.0
    founder_attention_hours: Optional[float] = 0.0


class PortfolioPestelItemCreate(BaseModel):
    factor: str
    statement: str
    impact: Optional[str] = "medium"
    horizon: Optional[str] = "medium"
    confidence: Optional[str] = "medium"
    evidence_status: Optional[str] = "hypothesis"


class ProjectPestelImpactSet(BaseModel):
    pestel_item_id: int
    impact_type: Optional[str] = "POSITIVE"
    impact_magnitude: Optional[str] = "MEDIUM"
    impact_analysis: Optional[str] = None
    mitigation_or_leverage: Optional[str] = None


# ------------------------------------------------------------------
# Portfolio Detector (Spec §22)
# ------------------------------------------------------------------

@router.get("/portfolios/detect")
def detect_portfolio_necessity(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_V12, workspace_id)
    detector = PortfolioDetectorService(db, workspace_id)
    return detector.detect()


# ------------------------------------------------------------------
# Portfolio CRUD (Spec §21)
# ------------------------------------------------------------------

@router.get("/portfolios")
def list_portfolios(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return {"portfolios": service.list_portfolios()}


@router.post("/portfolios", status_code=status.HTTP_201_CREATED)
def create_portfolio(
    workspace_id: int,
    data: PortfolioCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return service.create_portfolio(
        name=data.name,
        description=data.description,
        strategic_focus=data.strategic_focus,
        brain_id=data.brain_id,
    )


@router.get("/portfolios/{portfolio_id}")
def get_portfolio(
    portfolio_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return service.get_portfolio(portfolio_id)


@router.put("/portfolios/{portfolio_id}")
def update_portfolio(
    portfolio_id: int,
    workspace_id: int,
    data: PortfolioUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return service.update_portfolio(
        portfolio_id,
        name=data.name,
        description=data.description,
        strategic_focus=data.strategic_focus,
        status_val=data.status,
    )


@router.delete("/portfolios/{portfolio_id}")
def delete_portfolio(
    portfolio_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return service.delete_portfolio(portfolio_id)


# ------------------------------------------------------------------
# Portfolio Projects (Spec §23, §57, §62.8)
# ------------------------------------------------------------------

@router.get("/portfolios/{portfolio_id}/projects")
def list_portfolio_projects(
    portfolio_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return {"projects": service.list_portfolio_projects(portfolio_id)}


@router.post("/portfolios/{portfolio_id}/projects")
def add_project_to_portfolio(
    portfolio_id: int,
    workspace_id: int,
    data: PortfolioProjectAdd,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return service.add_project_to_portfolio(
        portfolio_id,
        project_id=data.project_id,
        strategic_priority=data.strategic_priority or "core",
        capacity_allocation=data.capacity_allocation or 0.0,
        founder_attention_hours=data.founder_attention_hours or 0.0,
    )


@router.delete("/portfolios/{portfolio_id}/projects/{project_id}")
def remove_project_from_portfolio(
    portfolio_id: int,
    project_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return service.remove_project_from_portfolio(portfolio_id, project_id)


# ------------------------------------------------------------------
# Shared PESTEL & Impact Matrix (Spec §24)
# ------------------------------------------------------------------

@router.get("/portfolios/{portfolio_id}/pestel")
def get_portfolio_pestel(
    portfolio_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_SHARED_PESTEL_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return {"pestel_items": service.get_portfolio_pestel(portfolio_id)}


@router.post("/portfolios/{portfolio_id}/pestel")
def add_portfolio_pestel_item(
    portfolio_id: int,
    workspace_id: int,
    data: PortfolioPestelItemCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_SHARED_PESTEL_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return service.add_portfolio_pestel_item(
        portfolio_id,
        factor=data.factor,
        statement=data.statement,
        impact=data.impact or "medium",
        horizon=data.horizon or "medium",
        confidence=data.confidence or "medium",
        evidence_status=data.evidence_status or "hypothesis",
    )


@router.get("/portfolios/{portfolio_id}/impact-matrix")
def get_portfolio_impact_matrix(
    portfolio_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_SHARED_PESTEL_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return service.get_portfolio_impact_matrix(portfolio_id)


@router.post("/projects/{project_id}/pestel-impacts")
def set_project_pestel_impact(
    project_id: int,
    workspace_id: int,
    data: ProjectPestelImpactSet,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_SHARED_PESTEL_V12, workspace_id)
    service = PortfolioService(db, workspace_id, member.user_id)
    return service.set_project_pestel_impact(
        project_id,
        pestel_item_id=data.pestel_item_id,
        impact_type=data.impact_type or "POSITIVE",
        impact_magnitude=data.impact_magnitude or "MEDIUM",
        impact_analysis=data.impact_analysis,
        mitigation_or_leverage=data.mitigation_or_leverage,
    )


# ==========================================
# mCOSA V12 — Portfolio SWOT, Options & Synergies (Sprint 7)
# ==========================================

class PortfolioSwotItemCreate(BaseModel):
    category: str
    statement: str
    impact: Optional[str] = "medium"
    likelihood: Optional[str] = "medium"
    confidence: Optional[str] = "medium"
    evidence_status: Optional[str] = "hypothesis"


class PortfolioTowsOptionCreate(BaseModel):
    quadrant: str
    title: str
    tradeoffs: Optional[str] = ""
    expected_impact: Optional[str] = "medium"
    confidence: Optional[str] = "medium"
    status: Optional[str] = "draft"


class PortfolioSynergyCreate(BaseModel):
    source_project_id: int
    target_project_id: int
    synergy_type: Optional[str] = "SHARED_CAPABILITY"
    description: str
    estimated_value: Optional[float] = None
    status: Optional[str] = "identified"


class PortfolioDependencyCreate(BaseModel):
    predecessor_project_id: int
    successor_project_id: int
    dependency_type: Optional[str] = "BLOCKS"
    description: Optional[str] = None


class PortfolioOptionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    tows_option_id: Optional[int] = None
    strategic_fit_score: Optional[float] = 0.8
    feasibility_score: Optional[float] = 0.7
    risk_level: Optional[str] = "MEDIUM"
    status: Optional[str] = "draft"


class PortfolioOptionUpdate(BaseModel):
    status: Optional[str] = None
    strategic_fit_score: Optional[float] = None
    feasibility_score: Optional[float] = None


@router.get("/portfolios/{portfolio_id}/swot")
def get_portfolio_swot(
    portfolio_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return {"swot_items": service.get_portfolio_swot(portfolio_id)}


@router.post("/portfolios/{portfolio_id}/swot")
def add_portfolio_swot_item(
    portfolio_id: int,
    workspace_id: int,
    data: PortfolioSwotItemCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return service.add_portfolio_swot_item(
        portfolio_id,
        category=data.category,
        statement=data.statement,
        impact=data.impact or "medium",
        likelihood=data.likelihood or "medium",
        confidence=data.confidence or "medium",
        evidence_status=data.evidence_status or "hypothesis",
    )


@router.get("/portfolios/{portfolio_id}/tows")
def get_portfolio_tows(
    portfolio_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return {"tows_options": service.get_portfolio_tows(portfolio_id)}


@router.post("/portfolios/{portfolio_id}/tows")
def add_portfolio_tows_option(
    portfolio_id: int,
    workspace_id: int,
    data: PortfolioTowsOptionCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return service.add_portfolio_tows_option(
        portfolio_id,
        quadrant=data.quadrant,
        title=data.title,
        tradeoffs=data.tradeoffs or "",
        expected_impact=data.expected_impact or "medium",
        confidence=data.confidence or "medium",
        status_val=data.status or "draft",
    )


@router.get("/portfolios/{portfolio_id}/synergies")
def list_portfolio_synergies(
    portfolio_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return {"synergies": service.list_portfolio_synergies(portfolio_id)}


@router.post("/portfolios/{portfolio_id}/synergies")
def add_portfolio_synergy(
    portfolio_id: int,
    workspace_id: int,
    data: PortfolioSynergyCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return service.add_portfolio_synergy(
        portfolio_id,
        source_project_id=data.source_project_id,
        target_project_id=data.target_project_id,
        synergy_type=data.synergy_type or "SHARED_CAPABILITY",
        description=data.description,
        estimated_value=data.estimated_value,
        status_val=data.status or "identified",
    )


@router.delete("/portfolios/{portfolio_id}/synergies/{synergy_id}")
def delete_portfolio_synergy(
    portfolio_id: int,
    synergy_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return service.delete_portfolio_synergy(synergy_id)


@router.get("/portfolios/{portfolio_id}/dependencies")
def list_portfolio_dependencies(
    portfolio_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return {"dependencies": service.list_portfolio_dependencies(portfolio_id)}


@router.post("/portfolios/{portfolio_id}/dependencies")
def add_portfolio_dependency(
    portfolio_id: int,
    workspace_id: int,
    data: PortfolioDependencyCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return service.add_portfolio_dependency(
        portfolio_id,
        predecessor_project_id=data.predecessor_project_id,
        successor_project_id=data.successor_project_id,
        dependency_type=data.dependency_type or "BLOCKS",
        description=data.description,
    )


@router.delete("/portfolios/{portfolio_id}/dependencies/{dependency_id}")
def delete_portfolio_dependency(
    portfolio_id: int,
    dependency_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return service.delete_portfolio_dependency(dependency_id)


@router.get("/portfolios/{portfolio_id}/options")
def list_portfolio_options(
    portfolio_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return {"options": service.list_portfolio_options(portfolio_id)}


@router.post("/portfolios/{portfolio_id}/options")
def create_portfolio_option(
    portfolio_id: int,
    workspace_id: int,
    data: PortfolioOptionCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return service.create_portfolio_option(
        portfolio_id,
        title=data.title,
        description=data.description,
        tows_option_id=data.tows_option_id,
        strategic_fit_score=data.strategic_fit_score or 0.8,
        feasibility_score=data.feasibility_score or 0.7,
        risk_level=data.risk_level or "MEDIUM",
        status_val=data.status or "draft",
    )


@router.put("/portfolios/{portfolio_id}/options/{option_id}")
def update_portfolio_option(
    portfolio_id: int,
    option_id: int,
    workspace_id: int,
    data: PortfolioOptionUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_SWOT_TOWS_V12, workspace_id)
    service = PortfolioAdvancedService(db, workspace_id, member.user_id)
    return service.update_portfolio_option(
        option_id,
        status_val=data.status,
        strategic_fit_score=data.strategic_fit_score,
        feasibility_score=data.feasibility_score,
    )


# ==========================================
# mCOSA V12 — Portfolio Cycles, WIP Limit & Capacity (Sprint 8)
# ==========================================

class FounderProfileUpdate(BaseModel):
    weekly_capacity_hours: Optional[float] = None
    max_active_strategic_projects: Optional[int] = None


class PortfolioCycleCreate(BaseModel):
    title: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CapacityAllocationSet(BaseModel):
    project_id: int
    allocated_percentage: float


class FounderAttentionAllocationSet(BaseModel):
    project_id: int
    allocated_hours_per_week: float


@router.get("/founder-profile")
def get_founder_profile(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_FOUNDER_ATTENTION_V12, workspace_id)
    service = PortfolioCycleService(db, workspace_id, member.user_id)
    profile = service.get_or_create_founder_profile()
    return service._serialize_founder_profile(profile)


@router.put("/founder-profile")
def update_founder_profile(
    workspace_id: int,
    data: FounderProfileUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_FOUNDER_ATTENTION_V12, workspace_id)
    service = PortfolioCycleService(db, workspace_id, member.user_id)
    return service.update_founder_profile(
        weekly_capacity_hours=data.weekly_capacity_hours,
        max_active_strategic_projects=data.max_active_strategic_projects,
    )


@router.get("/portfolios/{portfolio_id}/cycles")
def list_portfolio_cycles(
    portfolio_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_CYCLE_V12, workspace_id)
    service = PortfolioCycleService(db, workspace_id, member.user_id)
    return {"cycles": service.list_portfolio_cycles(portfolio_id)}


@router.post("/portfolios/{portfolio_id}/cycles")
def create_portfolio_cycle(
    portfolio_id: int,
    workspace_id: int,
    data: PortfolioCycleCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_CYCLE_V12, workspace_id)
    service = PortfolioCycleService(db, workspace_id, member.user_id)
    return service.create_portfolio_cycle(
        portfolio_id,
        title=data.title,
        start_date=data.start_date,
        end_date=data.end_date,
    )


@router.post("/portfolio-cycles/{cycle_id}/activate")
def activate_portfolio_cycle(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_CYCLE_V12, workspace_id)
    service = PortfolioCycleService(db, workspace_id, member.user_id)
    return service.activate_portfolio_cycle(cycle_id)


@router.get("/portfolio-cycles/{cycle_id}/allocations")
def get_cycle_allocations(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PORTFOLIO_CYCLE_V12, workspace_id)
    service = PortfolioCycleService(db, workspace_id, member.user_id)
    return service.get_cycle_allocations(cycle_id)


@router.post("/portfolio-cycles/{cycle_id}/allocations/capacity")
def set_capacity_allocation(
    cycle_id: int,
    workspace_id: int,
    data: CapacityAllocationSet,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_CAPACITY_PLANNER_V12, workspace_id)
    service = PortfolioCycleService(db, workspace_id, member.user_id)
    return service.set_capacity_allocation(
        cycle_id,
        project_id=data.project_id,
        allocated_percentage=data.allocated_percentage,
    )


@router.post("/portfolio-cycles/{cycle_id}/allocations/founder-attention")
def set_founder_attention_allocation(
    cycle_id: int,
    workspace_id: int,
    data: FounderAttentionAllocationSet,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_FOUNDER_ATTENTION_V12, workspace_id)
    service = PortfolioCycleService(db, workspace_id, member.user_id)
    return service.set_founder_attention_allocation(
        cycle_id,
        project_id=data.project_id,
        allocated_hours_per_week=data.allocated_hours_per_week,
    )


