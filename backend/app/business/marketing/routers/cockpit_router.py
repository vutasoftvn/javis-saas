from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.db.session import get_db
from app.db.models import Brain, WorkspaceMember
from app.business.marketing.models import (
    MarketingContext, MarketingObjective, MarketingCampaign,
    MarketingMetric, MarketingExperiment, MarketingLearning,
    PendingApproval, MarketingLoop, MarketingDecision, MarketingRecommendation
)
from app.business.marketing.models_validation import (
    Assumption, Evidence, CustomerInterview, CanvasRevision, AssumptionStatus
)
from app.business.marketing.services.analytics_engine import AnalyticsEngine
from app.business.marketing.services.context_adapter import ContextAdapter
from app.business.marketing.services.funnel_engine import FunnelEngine
from app.business.marketing.services.scorecard_service import ScorecardService
from app.business.marketing.schemas import (
    MarketingContextCreate,
    CustomerResearchUpdate,
    ProductMarketingUpdate,
    OfferArchitectureUpdate,
    Plan12WUpdate,
    MarketingLoopCreate,
    MarketingLoopUpdate,
    AttributionCalculateRequest,
    DecisionCreate,
    DecisionUpdate,
    RecommendationCreate,
)

router = APIRouter()


def resolve_brain_id(db: Session, workspace_id: int, brain_id: Optional[int]) -> int:
    if brain_id:
        brain = db.query(Brain).filter(
            Brain.id == brain_id,
            Brain.workspace_id == workspace_id,
        ).first()
        if not brain:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brain not found")
        return brain.id

    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).order_by(Brain.created_at).first()
    if not brain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace chưa có Brain nào - hãy tạo Brain trước khi dùng Marketing OS",
        )
    return brain.id


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def serialize_context(ctx: Optional[MarketingContext]) -> Optional[Dict[str, Any]]:
    if not ctx:
        return None
    return {
        "id": str(ctx.id),
        "strategy_revision_id": str(ctx.strategy_revision_id) if ctx.strategy_revision_id else None,
        "market": ctx.market or {},
        "category": ctx.category or "",
        "icp": ctx.icp or {},
        "personas": ctx.personas or [],
        "jobs_to_be_done": ctx.jobs_to_be_done or [],
        "positioning": ctx.positioning or {},
        "value_proposition": ctx.value_proposition or {},
        "brand_voice": ctx.brand_voice or {},
        "competitors": ctx.competitors or [],
        "pricing": ctx.pricing or {},
        "constraints": ctx.constraints or [],
        "customer_research": ctx.customer_research or {},
        "product_marketing": ctx.product_marketing or {},
        "offer_architecture": ctx.offer_architecture or {},
        "marketing_plan_12w": ctx.marketing_plan_12w or {},
        "proofs": ctx.proofs or [],
        "channels": ctx.channels or [],
        "updated_at": _iso(ctx.updated_at),
    }


def serialize_loop(loop: MarketingLoop) -> Dict[str, Any]:
    return {
        "id": str(loop.id),
        "loop_type": loop.loop_type,
        "name": loop.name,
        "description": loop.description,
        "status": loop.status,
        "current_step": loop.current_step,
        "loop_config": loop.loop_config or {},
        "metrics_summary": loop.metrics_summary or {},
        "last_run_at": _iso(loop.last_run_at),
        "created_at": _iso(loop.created_at),
        "updated_at": _iso(loop.updated_at),
    }


def serialize_decision(dec: MarketingDecision) -> Dict[str, Any]:
    return {
        "id": str(dec.id),
        "campaign_id": str(dec.campaign_id) if dec.campaign_id else None,
        "title": dec.title,
        "context_summary": dec.context_summary,
        "decision": dec.decision,
        "reason": dec.reason,
        "alternatives": dec.alternatives or [],
        "expected_outcome": dec.expected_outcome,
        "review_date": _iso(dec.review_date),
        "actual_outcome": dec.actual_outcome,
        "learning": dec.learning,
        "created_at": _iso(dec.created_at),
        "updated_at": _iso(dec.updated_at),
    }


def serialize_recommendation(rec: MarketingRecommendation) -> Dict[str, Any]:
    return {
        "id": str(rec.id),
        "approval_id": str(rec.approval_id) if rec.approval_id else None,
        "title": rec.title,
        "problem": rec.problem,
        "evidence": rec.evidence or {},
        "hypothesis": rec.hypothesis,
        "recommended_action": rec.recommended_action,
        "expected_impact": rec.expected_impact,
        "confidence": rec.confidence,
        "estimated_cost": rec.estimated_cost,
        "risk_level": rec.risk_level,
        "status": rec.status,
        "created_at": _iso(rec.created_at),
    }


def serialize_metric(metric: MarketingMetric) -> Dict[str, Any]:
    return {
        "id": str(metric.id),
        "campaign_id": str(metric.campaign_id) if metric.campaign_id else None,
        "category": metric.category,
        "metric_name": metric.metric_name,
        "current_value": metric.current_value,
        "previous_value": metric.previous_value,
        "change_pct": metric.change_pct,
        "unit": metric.unit,
        "period": metric.period,
        "updated_at": _iso(metric.updated_at),
    }


@router.get("/cockpit-summary")
def get_cockpit_summary(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)

    objectives_count = db.query(MarketingObjective).filter(
        MarketingObjective.workspace_id == workspace_id,
        MarketingObjective.brain_id == b_id,
    ).count()
    active_campaigns_count = db.query(MarketingCampaign).filter(
        MarketingCampaign.workspace_id == workspace_id,
        MarketingCampaign.brain_id == b_id,
        MarketingCampaign.status == "active",
    ).count()
    pending_approvals_count = db.query(PendingApproval).filter(
        PendingApproval.workspace_id == workspace_id,
        PendingApproval.brain_id == b_id,
        PendingApproval.status == "pending",
    ).count()
    running_experiments_count = db.query(MarketingExperiment).filter(
        MarketingExperiment.workspace_id == workspace_id,
        MarketingExperiment.brain_id == b_id,
        MarketingExperiment.status == "running",
    ).count()
    learnings_count = db.query(MarketingLearning).filter(
        MarketingLearning.workspace_id == workspace_id,
        MarketingLearning.brain_id == b_id,
    ).count()

    # Validation Engine Summary Stats (§46 - §48 in E3.md)
    assumptions_all = db.query(Assumption).filter(
        Assumption.workspace_id == workspace_id,
        Assumption.brain_id == b_id,
    ).all()
    total_assumptions = len(assumptions_all)
    untested_count = sum(1 for a in assumptions_all if a.status == AssumptionStatus.UNTESTED.value)
    supported_count = sum(1 for a in assumptions_all if a.status == AssumptionStatus.SUPPORTED.value)
    contradicted_count = sum(1 for a in assumptions_all if a.status == AssumptionStatus.CONTRADICTED.value)
    critical_untested_count = sum(1 for a in assumptions_all if a.status == AssumptionStatus.UNTESTED.value and a.criticality >= 15)

    evidence_count = db.query(Evidence).filter(
        Evidence.workspace_id == workspace_id,
        Evidence.brain_id == b_id,
    ).count()
    interviews_count = db.query(CustomerInterview).filter(
        CustomerInterview.workspace_id == workspace_id,
        CustomerInterview.brain_id == b_id,
    ).count()
    pending_revisions_count = db.query(CanvasRevision).filter(
        CanvasRevision.workspace_id == workspace_id,
        CanvasRevision.brain_id == b_id,
        CanvasRevision.status == "pending_review",
    ).count()

    scorecard = ScorecardService.build(db, workspace_id, b_id)

    return {
        "summary": {
            "brain_id": str(b_id),
            "marketing_objectives_count": objectives_count,
            "active_campaigns_count": active_campaigns_count,
            "pending_approvals_count": pending_approvals_count,
            "running_experiments_count": running_experiments_count,
            "learnings_count": learnings_count,
            "validation": {
                "total_assumptions": total_assumptions,
                "untested_assumptions": untested_count,
                "supported_assumptions": supported_count,
                "contradicted_assumptions": contradicted_count,
                "critical_untested_warnings": critical_untested_count,
                "evidence_count": evidence_count,
                "interviews_count": interviews_count,
                "pending_canvas_revisions_count": pending_revisions_count,
            },
            **scorecard,
        }
    }


@router.get("/analytics/overview")
def get_analytics_overview(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    metrics = db.query(MarketingMetric).filter(
        MarketingMetric.workspace_id == workspace_id,
        MarketingMetric.brain_id == b_id,
    ).all()

    by_name = {m.metric_name: m.current_value for m in metrics}
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for m in metrics:
        grouped.setdefault(m.category, []).append(serialize_metric(m))

    spend = by_name.get("ad_spend", 0.0)
    revenue = by_name.get("revenue", 0.0)
    new_customers = by_name.get("new_customers", 0.0)
    active_customers = by_name.get("active_customers", 0.0)
    churn_pct = by_name.get("churn_rate", 0.0)
    gross_margin_pct = by_name.get("gross_margin_pct", 80.0)

    cac = AnalyticsEngine.calculate_cac(spend, new_customers)
    arpu = AnalyticsEngine.calculate_arpu(revenue, active_customers)
    ltv = AnalyticsEngine.calculate_ltv(arpu, gross_margin_pct, churn_pct)

    derived = {
        "ctr": AnalyticsEngine.calculate_ctr(by_name.get("clicks", 0.0), by_name.get("impressions", 0.0)),
        "cpc": AnalyticsEngine.calculate_cpc(spend, by_name.get("clicks", 0.0)),
        "cpl": AnalyticsEngine.calculate_cpl(spend, by_name.get("leads", 0.0)),
        "cac": cac,
        "cvr": AnalyticsEngine.calculate_conversion_rate(by_name.get("conversions", 0.0), by_name.get("sessions", 0.0)),
        "roas": AnalyticsEngine.calculate_roas(revenue, spend),
        "arpu": arpu,
        "ltv": ltv,
        "ltv_cac_ratio": AnalyticsEngine.calculate_ltv_cac_ratio(ltv, cac),
        "payback_months": AnalyticsEngine.calculate_payback_months(cac, arpu, gross_margin_pct),
    }

    anomalies = [
        {
            "metric_name": m.metric_name,
            "current_value": m.current_value,
            "previous_value": m.previous_value,
            **AnalyticsEngine.detect_anomaly(m.current_value, m.previous_value),
        }
        for m in metrics
        if AnalyticsEngine.detect_anomaly(m.current_value, m.previous_value)["is_anomaly"]
    ]

    return {
        "metrics_by_category": grouped,
        "derived": derived,
        "anomalies": anomalies,
        "has_data": bool(metrics),
        "missing_inputs": [
            name for name in ("ad_spend", "revenue", "new_customers", "active_customers", "churn_rate")
            if name not in by_name
        ],
    }


@router.get("/funnel")
def get_funnel(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    return FunnelEngine.build_funnel(db, workspace_id, b_id)


@router.get("/context")
def get_marketing_context(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id,
        MarketingContext.brain_id == b_id,
    ).order_by(MarketingContext.updated_at.desc()).first()
    return {"context": serialize_context(ctx)}


@router.post("/context")
def create_or_update_marketing_context(
    payload: MarketingContextCreate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)

    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id,
        MarketingContext.brain_id == b_id,
    ).first()

    data = payload.model_dump(exclude_unset=True)
    if not ctx:
        ctx = MarketingContext(
            workspace_id=workspace_id,
            brain_id=b_id,
            **data
        )
        db.add(ctx)
    else:
        for k, v in data.items():
            setattr(ctx, k, v)
        ctx.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(ctx)
    return {"context": serialize_context(ctx)}


@router.get("/context/customer-research")
def get_customer_research(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id,
        MarketingContext.brain_id == b_id,
    ).first()
    return {"customer_research": ctx.customer_research if ctx else {}}


@router.patch("/context/customer-research")
def update_customer_research(
    payload: CustomerResearchUpdate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id,
        MarketingContext.brain_id == b_id,
    ).first()
    if not ctx:
        ctx = MarketingContext(workspace_id=workspace_id, brain_id=b_id)
        db.add(ctx)
    ctx.customer_research = payload.customer_research
    db.commit()
    db.refresh(ctx)
    return {"customer_research": ctx.customer_research}


@router.get("/context/product-marketing")
def get_product_marketing(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id,
        MarketingContext.brain_id == b_id,
    ).first()
    return {"product_marketing": ctx.product_marketing if ctx else {}}


@router.patch("/context/product-marketing")
def update_product_marketing(
    payload: ProductMarketingUpdate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id,
        MarketingContext.brain_id == b_id,
    ).first()
    if not ctx:
        ctx = MarketingContext(workspace_id=workspace_id, brain_id=b_id)
        db.add(ctx)
    ctx.product_marketing = payload.product_marketing
    db.commit()
    db.refresh(ctx)
    return {"product_marketing": ctx.product_marketing}


@router.get("/context/offer-architecture")
def get_offer_architecture(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id,
        MarketingContext.brain_id == b_id,
    ).first()
    return {"offer_architecture": ctx.offer_architecture if ctx else {}}


@router.patch("/context/offer-architecture")
def update_offer_architecture(
    payload: OfferArchitectureUpdate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id,
        MarketingContext.brain_id == b_id,
    ).first()
    if not ctx:
        ctx = MarketingContext(workspace_id=workspace_id, brain_id=b_id)
        db.add(ctx)
    ctx.offer_architecture = payload.offer_architecture
    db.commit()
    db.refresh(ctx)
    return {"offer_architecture": ctx.offer_architecture}


@router.get("/context/12w-plan")
def get_12w_plan(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id,
        MarketingContext.brain_id == b_id,
    ).first()
    return {"marketing_plan_12w": ctx.marketing_plan_12w if ctx else {}}


@router.patch("/context/12w-plan")
def update_12w_plan(
    payload: Plan12WUpdate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id,
        MarketingContext.brain_id == b_id,
    ).first()
    if not ctx:
        ctx = MarketingContext(workspace_id=workspace_id, brain_id=b_id)
        db.add(ctx)
    ctx.marketing_plan_12w = payload.marketing_plan_12w
    db.commit()
    db.refresh(ctx)
    return {"marketing_plan_12w": ctx.marketing_plan_12w}


@router.get("/loops")
def list_loops(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    loops = db.query(MarketingLoop).filter(
        MarketingLoop.workspace_id == workspace_id,
        MarketingLoop.brain_id == b_id,
    ).order_by(MarketingLoop.created_at.desc()).all()
    return {"loops": [serialize_loop(l) for l in loops]}


@router.post("/loops")
def create_loop(
    payload: MarketingLoopCreate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    loop = MarketingLoop(
        workspace_id=workspace_id,
        brain_id=b_id,
        **payload.model_dump(),
    )
    db.add(loop)
    db.commit()
    db.refresh(loop)
    return {"loop": serialize_loop(loop)}


@router.patch("/loops/{loop_id}")
def update_loop(
    loop_id: int,
    payload: MarketingLoopUpdate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    loop = db.query(MarketingLoop).filter(
        MarketingLoop.id == loop_id,
        MarketingLoop.workspace_id == workspace_id,
    ).first()
    if not loop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loop not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(loop, k, v)
    db.commit()
    db.refresh(loop)
    return {"loop": serialize_loop(loop)}


@router.post("/loops/{loop_id}/trigger")
def trigger_loop(
    loop_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    loop = db.query(MarketingLoop).filter(
        MarketingLoop.id == loop_id,
        MarketingLoop.workspace_id == workspace_id,
    ).first()
    if not loop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loop not found")
    loop.last_run_at = datetime.utcnow()
    db.commit()
    db.refresh(loop)
    return {"loop": serialize_loop(loop), "status": "triggered", "execution_status": "triggered"}


@router.delete("/loops/{loop_id}")
def delete_loop(
    loop_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    loop = db.query(MarketingLoop).filter(
        MarketingLoop.id == loop_id,
        MarketingLoop.workspace_id == workspace_id,
    ).first()
    if not loop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loop not found")
    db.delete(loop)
    db.commit()
    return {"deleted": str(loop_id)}


@router.post("/analytics/attribution")
def calculate_attribution(
    payload: AttributionCalculateRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    result = AnalyticsEngine.calculate_attribution(
        touchpoints=payload.touchpoints,
        model_type=payload.model_type,
        conversion_value=payload.conversion_value,
    )
    return {"attribution": result}


@router.get("/decisions")
def list_decisions(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    decisions = db.query(MarketingDecision).filter(
        MarketingDecision.workspace_id == workspace_id,
        MarketingDecision.brain_id == b_id,
    ).order_by(MarketingDecision.created_at.desc()).all()
    return {"decisions": [serialize_decision(d) for d in decisions]}


@router.post("/decisions")
def create_decision(
    payload: DecisionCreate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    dec = MarketingDecision(
        workspace_id=workspace_id,
        brain_id=b_id,
        **payload.model_dump(),
    )
    db.add(dec)
    db.commit()
    db.refresh(dec)
    return {"decision": serialize_decision(dec)}


@router.patch("/decisions/{decision_id}")
def update_decision(
    decision_id: int,
    payload: DecisionUpdate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    dec = db.query(MarketingDecision).filter(
        MarketingDecision.id == decision_id,
        MarketingDecision.workspace_id == workspace_id,
    ).first()
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(dec, k, v)
    db.commit()
    db.refresh(dec)
    return {"decision": serialize_decision(dec)}


@router.delete("/decisions/{decision_id}")
def delete_decision(
    decision_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    dec = db.query(MarketingDecision).filter(
        MarketingDecision.id == decision_id,
        MarketingDecision.workspace_id == workspace_id,
    ).first()
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    db.delete(dec)
    db.commit()
    return {"deleted": str(decision_id)}


@router.get("/recommendations")
def list_recommendations(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    recs = db.query(MarketingRecommendation).filter(
        MarketingRecommendation.workspace_id == workspace_id,
        MarketingRecommendation.brain_id == b_id,
    ).order_by(MarketingRecommendation.created_at.desc()).all()
    return {"recommendations": [serialize_recommendation(r) for r in recs]}


@router.post("/recommendations")
def create_recommendation(
    payload: RecommendationCreate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    rec = MarketingRecommendation(
        workspace_id=workspace_id,
        brain_id=b_id,
        **payload.model_dump(),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"recommendation": serialize_recommendation(rec)}


@router.post("/recommendations/{recommendation_id}/status")
def update_recommendation_status(
    recommendation_id: int,
    payload: Any,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    rec = db.query(MarketingRecommendation).filter(
        MarketingRecommendation.id == recommendation_id,
        MarketingRecommendation.workspace_id == workspace_id,
    ).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    new_status = payload if isinstance(payload, str) else (payload.get("status") if isinstance(payload, dict) else str(payload))
    if new_status:
        rec.status = new_status
    db.commit()
    db.refresh(rec)
    return {"recommendation": serialize_recommendation(rec)}
