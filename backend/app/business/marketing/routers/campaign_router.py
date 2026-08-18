from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.db.session import get_db
from app.db.models import Brain, WorkspaceMember
from app.business.marketing.models import (
    MarketingObjective, MarketingCampaign, CampaignAsset,
    MarketingMetric, MetricSnapshot, MarketingExperiment, MarketingLearning,
    PendingApproval
)
from app.business.marketing.services.analytics_engine import AnalyticsEngine
from app.business.marketing.services.funnel_engine import FunnelEngine
from app.business.marketing.services.skill_router import SkillRouter
from app.business.learning.service import create_lesson as create_generic_lesson
from app.business.marketing.schemas import (
    CAMPAIGN_STATUSES,
    CAMPAIGN_STATUSES_REQUIRING_APPROVAL,
    MarketingObjectiveCreate,
    MarketingObjectiveUpdate,
    CampaignCreate,
    CampaignUpdate,
    CampaignStatusUpdate,
    CampaignAssetCreate,
    ExperimentCreate,
    ExperimentEvaluateRequest,
    ExperimentDecisionRequest,
    LearningCreate,
    MetricUpsert,
    SkillExecuteRequest,
    ApprovalReviewRequest,
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


def _get_campaign_scoped(db: Session, campaign_id: int, workspace_id: int) -> MarketingCampaign:
    campaign = db.query(MarketingCampaign).filter(
        MarketingCampaign.id == campaign_id,
        MarketingCampaign.workspace_id == workspace_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


def _get_experiment_scoped(db: Session, experiment_id: int, workspace_id: int) -> MarketingExperiment:
    experiment = db.query(MarketingExperiment).filter(
        MarketingExperiment.id == experiment_id,
        MarketingExperiment.workspace_id == workspace_id,
    ).first()
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment


def _get_objective_scoped(db: Session, objective_id: int, workspace_id: int) -> MarketingObjective:
    objective = db.query(MarketingObjective).filter(
        MarketingObjective.id == objective_id,
        MarketingObjective.workspace_id == workspace_id,
    ).first()
    if not objective:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objective not found")
    return objective


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def serialize_objective(obj: MarketingObjective) -> Dict[str, Any]:
    target = obj.target_value or 0.0
    return {
        "id": str(obj.id),
        "strategic_objective_id": str(obj.strategic_objective_id) if obj.strategic_objective_id else None,
        "title": obj.title,
        "description": obj.description,
        "target_metric": obj.target_metric,
        "target_value": target,
        "current_value": obj.current_value or 0.0,
        "progress_pct": round(min((obj.current_value or 0.0) / target, 1.0) * 100, 1) if target > 0 else 0.0,
        "unit": obj.unit,
        "status": obj.status,
        "period_weeks": obj.period_weeks,
        "created_at": _iso(obj.created_at),
    }


def serialize_campaign(camp: MarketingCampaign) -> Dict[str, Any]:
    return {
        "id": str(camp.id),
        "marketing_objective_id": str(camp.marketing_objective_id) if camp.marketing_objective_id else None,
        "name": camp.name,
        "funnel_stage": camp.funnel_stage,
        "funnel_stage_label": FunnelEngine.label_for(camp.funnel_stage),
        "channels": camp.channels or [],
        "budget": camp.budget or 0.0,
        "status": camp.status,
        "owner": camp.owner,
        "start_date": _iso(camp.start_date),
        "end_date": _iso(camp.end_date),
        "created_at": _iso(camp.created_at),
    }


def serialize_asset(asset: CampaignAsset) -> Dict[str, Any]:
    return {
        "id": str(asset.id),
        "campaign_id": str(asset.campaign_id),
        "asset_type": asset.asset_type,
        "title": asset.title,
        "content": asset.content,
        "meta_data": asset.meta_data,
        "approval_status": asset.approval_status,
        "created_at": _iso(asset.created_at),
    }


def serialize_experiment(exp: MarketingExperiment) -> Dict[str, Any]:
    return {
        "id": str(exp.id),
        "campaign_id": str(exp.campaign_id) if exp.campaign_id else None,
        "hypothesis": exp.hypothesis,
        "metric": exp.metric,
        "baseline_value": exp.baseline_value,
        "target_value": exp.target_value,
        "variant_a": exp.variant_a,
        "variant_b": exp.variant_b,
        "sample_size": exp.sample_size,
        "status": exp.status,
        "decision": exp.decision,
        "learning": exp.learning,
        "evaluation": exp.evaluation,
        "created_at": _iso(exp.created_at),
    }


def serialize_learning(item: MarketingLearning) -> Dict[str, Any]:
    return {
        "id": str(item.id),
        "experiment_id": str(item.experiment_id) if item.experiment_id else None,
        "campaign_id": str(item.campaign_id) if item.campaign_id else None,
        "observation": item.observation,
        "hypothesis": item.hypothesis,
        "action": item.action,
        "result": item.result,
        "learning": item.learning,
        "category": item.category,
        "confidence": item.confidence,
        "impact_score": item.impact_score,
        "reusable_rule": item.reusable_rule,
        "created_at": _iso(item.created_at),
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


def serialize_approval(appr: PendingApproval) -> Dict[str, Any]:
    return {
        "id": str(appr.id),
        "action_type": appr.action_type,
        "title": appr.title,
        "details": appr.details,
        "status": appr.status,
        "requested_by_agent": appr.requested_by_agent,
        "reviewed_by": str(appr.reviewed_by) if appr.reviewed_by else None,
        "reviewed_at": _iso(appr.reviewed_at),
        "review_notes": appr.review_notes,
        "created_at": _iso(appr.created_at),
    }


# ==========================================
# Objectives
# ==========================================

@router.get("/objectives")
def list_marketing_objectives(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    objectives = db.query(MarketingObjective).filter(
        MarketingObjective.workspace_id == workspace_id,
        MarketingObjective.brain_id == b_id,
    ).order_by(MarketingObjective.created_at.desc()).all()
    return {"objectives": [serialize_objective(o) for o in objectives]}


@router.post("/objectives")
def create_marketing_objective(
    payload: MarketingObjectiveCreate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    obj = MarketingObjective(
        workspace_id=workspace_id,
        brain_id=b_id,
        **payload.model_dump(),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"objective": serialize_objective(obj)}


@router.patch("/objectives/{objective_id}")
def update_marketing_objective(
    objective_id: int,
    payload: MarketingObjectiveUpdate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    obj = _get_objective_scoped(db, objective_id, workspace_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return {"objective": serialize_objective(obj)}


@router.delete("/objectives/{objective_id}")
def delete_marketing_objective(
    objective_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    obj = _get_objective_scoped(db, objective_id, workspace_id)
    db.delete(obj)
    db.commit()
    return {"deleted": str(objective_id)}


# ==========================================
# Campaigns
# ==========================================

@router.get("/campaigns")
def list_campaigns(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    funnel_stage: Optional[str] = Query(None),
    campaign_status: Optional[str] = Query(None, alias="status"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    query = db.query(MarketingCampaign).filter(
        MarketingCampaign.workspace_id == workspace_id,
        MarketingCampaign.brain_id == b_id,
    )
    if funnel_stage:
        query = query.filter(MarketingCampaign.funnel_stage == funnel_stage)
    if campaign_status:
        query = query.filter(MarketingCampaign.status == campaign_status)
    campaigns = query.order_by(MarketingCampaign.created_at.desc()).all()
    return {"campaigns": [serialize_campaign(c) for c in campaigns]}


@router.post("/campaigns")
def create_campaign(
    payload: CampaignCreate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)

    if payload.marketing_objective_id:
        _get_objective_scoped(db, payload.marketing_objective_id, workspace_id)

    camp = MarketingCampaign(
        workspace_id=workspace_id,
        brain_id=b_id,
        **payload.model_dump(),
    )
    db.add(camp)
    db.commit()
    db.refresh(camp)
    return {"campaign": serialize_campaign(camp)}


@router.get("/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    camp = _get_campaign_scoped(db, campaign_id, workspace_id)
    assets = db.query(CampaignAsset).filter(
        CampaignAsset.campaign_id == camp.id,
        CampaignAsset.workspace_id == workspace_id,
    ).order_by(CampaignAsset.created_at.desc()).all()
    experiments = db.query(MarketingExperiment).filter(
        MarketingExperiment.campaign_id == camp.id,
        MarketingExperiment.workspace_id == workspace_id,
    ).all()
    return {
        "campaign": serialize_campaign(camp),
        "assets": [serialize_asset(a) for a in assets],
        "experiments": [serialize_experiment(e) for e in experiments],
    }


@router.patch("/campaigns/{campaign_id}")
def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    camp = _get_campaign_scoped(db, campaign_id, workspace_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(camp, field, value)
    db.commit()
    db.refresh(camp)
    return {"campaign": serialize_campaign(camp)}


@router.post("/campaigns/{campaign_id}/status")
def change_campaign_status(
    campaign_id: int,
    payload: CampaignStatusUpdate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    camp = _get_campaign_scoped(db, campaign_id, workspace_id)

    if payload.status in CAMPAIGN_STATUSES_REQUIRING_APPROVAL and camp.status != payload.status:
        approval = PendingApproval(
            workspace_id=workspace_id,
            brain_id=camp.brain_id,
            action_type=f"campaign.{payload.status}",
            title=f"{'Kích hoạt' if payload.status == 'active' else 'Tạm dừng'} chiến dịch: {camp.name}",
            details={
                "campaign_id": str(camp.id),
                "campaign_name": camp.name,
                "from_status": camp.status,
                "to_status": payload.status,
                "budget": camp.budget,
            },
            status="pending",
            requested_by_agent="Marketing Director",
        )
        camp.status = "pending_approval"
        db.add(approval)
        db.commit()
        db.refresh(approval)
        db.refresh(camp)
        return {
            "status": "pending_approval",
            "campaign": serialize_campaign(camp),
            "approval": serialize_approval(approval),
            "message": "Thay đổi cần người phê duyệt trước khi có hiệu lực.",
        }

    camp.status = payload.status
    db.commit()
    db.refresh(camp)
    return {"status": "updated", "campaign": serialize_campaign(camp)}


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(
    campaign_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    camp = _get_campaign_scoped(db, campaign_id, workspace_id)
    db.delete(camp)
    db.commit()
    return {"deleted": str(campaign_id)}


@router.post("/campaigns/{campaign_id}/assets")
def create_campaign_asset(
    campaign_id: int,
    payload: CampaignAssetCreate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    camp = _get_campaign_scoped(db, campaign_id, workspace_id)
    asset = CampaignAsset(
        campaign_id=camp.id,
        workspace_id=workspace_id,
        asset_type=payload.asset_type,
        title=payload.title,
        content=payload.content,
        meta_data=payload.meta_data,
        approval_status="draft",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"asset": serialize_asset(asset)}


@router.post("/assets/{asset_id}/request-approval")
def request_asset_approval(
    asset_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    asset = db.query(CampaignAsset).filter(
        CampaignAsset.id == asset_id,
        CampaignAsset.workspace_id == workspace_id,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    campaign = _get_campaign_scoped(db, asset.campaign_id, workspace_id)
    approval = PendingApproval(
        workspace_id=workspace_id,
        brain_id=campaign.brain_id,
        action_type="asset.publish",
        title=f"Xuất bản nội dung: {asset.title}",
        details={
            "asset_id": str(asset.id),
            "campaign_id": str(campaign.id),
            "asset_type": asset.asset_type,
        },
        status="pending",
        requested_by_agent="Content Agent",
    )
    asset.approval_status = "pending_approval"
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return {"approval": serialize_approval(approval)}


# ==========================================
# Experiments & Learnings & Metrics
# ==========================================

@router.get("/experiments")
def list_experiments(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    experiments = db.query(MarketingExperiment).filter(
        MarketingExperiment.workspace_id == workspace_id,
        MarketingExperiment.brain_id == b_id,
    ).order_by(MarketingExperiment.created_at.desc()).all()
    return {"experiments": [serialize_experiment(e) for e in experiments]}


@router.post("/experiments")
def create_experiment(
    payload: ExperimentCreate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    if payload.campaign_id:
        _get_campaign_scoped(db, payload.campaign_id, workspace_id)

    exp = MarketingExperiment(
        workspace_id=workspace_id,
        brain_id=b_id,
        status="running",
        **payload.model_dump(),
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return {"experiment": serialize_experiment(exp)}


@router.post("/experiments/{experiment_id}/evaluate")
def evaluate_experiment(
    experiment_id: int,
    payload: ExperimentEvaluateRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    exp = _get_experiment_scoped(db, experiment_id, workspace_id)
    result = AnalyticsEngine.evaluate_experiment(
        baseline_cvr=payload.baseline_cvr,
        variant_cvr=payload.variant_cvr,
        baseline_sample=payload.baseline_sample,
        variant_sample=payload.variant_sample,
        confidence_threshold=payload.confidence_threshold,
    )

    exp.status = result["decision"].lower()
    exp.evaluation = result
    exp.decision = (
        f"{result['decision']} · uplift {result['uplift_pct']}% · z={result['z_score']} · p={result.get('p_value')}"
    )
    db.commit()
    db.refresh(exp)
    return {"experiment": serialize_experiment(exp), "evaluation": result}


@router.post("/experiments/{experiment_id}/decide")
def decide_experiment(
    experiment_id: int,
    payload: ExperimentDecisionRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    exp = _get_experiment_scoped(db, experiment_id, workspace_id)
    exp.status = payload.decision.lower()
    exp.learning = payload.learning

    created_learning = None
    if payload.learning:
        created_learning = MarketingLearning(
            workspace_id=workspace_id,
            brain_id=exp.brain_id,
            experiment_id=exp.id,
            campaign_id=exp.campaign_id,
            observation=f"Thử nghiệm trên chỉ số {exp.metric}",
            hypothesis=exp.hypothesis,
            action=f"So sánh {exp.variant_a} và {exp.variant_b}",
            result=exp.decision or payload.decision,
            learning=payload.learning,
            category="experiment",
            confidence="high" if payload.decision in {"WIN", "LOSE"} else "medium",
        )
        db.add(created_learning)

    db.commit()
    db.refresh(exp)
    if created_learning is not None:
        db.refresh(created_learning)

    return {
        "experiment": serialize_experiment(exp),
        "learning": serialize_learning(created_learning) if created_learning else None,
    }


@router.get("/learnings")
def list_learnings(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    learnings = db.query(MarketingLearning).filter(
        MarketingLearning.workspace_id == workspace_id,
        MarketingLearning.brain_id == b_id,
    ).order_by(MarketingLearning.created_at.desc()).all()
    return {
        "learnings": [serialize_learning(item) for item in learnings],
        "playbooks": [
            {"rule": item.reusable_rule, "confidence": item.confidence, "learning_id": str(item.id)}
            for item in learnings
            if item.reusable_rule
        ],
    }


@router.post("/learnings")
def create_learning(
    payload: LearningCreate,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    if payload.campaign_id:
        _get_campaign_scoped(db, payload.campaign_id, workspace_id)
    if payload.experiment_id:
        _get_experiment_scoped(db, payload.experiment_id, workspace_id)

    item = MarketingLearning(workspace_id=workspace_id, brain_id=b_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    create_generic_lesson(
        db,
        workspace_id=workspace_id,
        observation=item.observation,
        function="MARKETING",
        evidence_refs={"marketing_learning_id": str(item.id)},
        interpretation=item.learning,
        recommendation=item.reusable_rule,
        confidence={"high": 0.9, "medium": 0.6, "low": 0.3}.get(item.confidence.lower(), 0.5),
        created_by=member.user_id,
    )
    return {"learning": serialize_learning(item)}


@router.get("/metrics")
def list_metrics(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    metrics = db.query(MarketingMetric).filter(
        MarketingMetric.workspace_id == workspace_id,
        MarketingMetric.brain_id == b_id,
    ).order_by(MarketingMetric.metric_name).all()
    return {"metrics": [serialize_metric(m) for m in metrics]}


@router.post("/metrics")
def upsert_metric(
    payload: MetricUpsert,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    if payload.campaign_id:
        _get_campaign_scoped(db, payload.campaign_id, workspace_id)

    metric = db.query(MarketingMetric).filter(
        MarketingMetric.workspace_id == workspace_id,
        MarketingMetric.brain_id == b_id,
        MarketingMetric.metric_name == payload.metric_name,
    ).first()

    if metric:
        metric.previous_value = metric.current_value
        metric.current_value = payload.value
        metric.change_pct = AnalyticsEngine.detect_anomaly(payload.value, metric.previous_value)["change_pct"]
        metric.category = payload.category
        metric.unit = payload.unit
        metric.period = payload.period
        metric.campaign_id = payload.campaign_id
        metric.recorded_at = datetime.utcnow()
    else:
        metric = MarketingMetric(
            workspace_id=workspace_id,
            brain_id=b_id,
            campaign_id=payload.campaign_id,
            category=payload.category,
            metric_name=payload.metric_name,
            current_value=payload.value,
            previous_value=0.0,
            change_pct=0.0,
            unit=payload.unit,
            period=payload.period,
        )
        db.add(metric)

    db.flush()
    db.add(MetricSnapshot(
        workspace_id=workspace_id,
        metric_id=metric.id,
        metric_name=metric.metric_name,
        value=payload.value,
    ))
    db.commit()
    db.refresh(metric)
    return {"metric": serialize_metric(metric)}


@router.get("/metrics/{metric_name}/history")
def get_metric_history(
    metric_name: str,
    workspace_id: int,
    limit: int = Query(60, ge=1, le=365),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    snapshots = db.query(MetricSnapshot).filter(
        MetricSnapshot.workspace_id == workspace_id,
        MetricSnapshot.metric_name == metric_name,
    ).order_by(MetricSnapshot.recorded_at.desc()).limit(limit).all()
    return {
        "metric_name": metric_name,
        "points": [
            {"value": s.value, "recorded_at": _iso(s.recorded_at)}
            for s in reversed(snapshots)
        ],
    }


@router.get("/skills")
def list_skills(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    return {"skills": SkillRouter.list_capabilities(db, workspace_id)}


@router.get("/skill-executions")
def list_skill_executions(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    executions = SkillRouter.list_executions(db, workspace_id, b_id, limit=limit)
    return {
        "executions": [
            {
                "id": str(e.id),
                "capability_id": e.capability_id,
                "provider": e.provider,
                "status": e.status,
                "requested_by_agent": e.requested_by_agent,
                "output": e.output,
                "created_at": _iso(e.created_at),
            }
            for e in executions
        ]
    }


@router.post("/execute-skill")
def execute_skill(
    payload: SkillExecuteRequest,
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    status_str, result = SkillRouter.execute_or_enqueue_approval(
        db=db,
        workspace_id=workspace_id,
        brain_id=b_id,
        capability_id=payload.capability_id,
        task_input=payload.task_input,
        requested_by_agent=payload.requested_by_agent,
    )
    return {"status": status_str, "result": result}


@router.get("/approvals")
def list_approvals(
    workspace_id: int,
    brain_id: Optional[int] = Query(None),
    approval_status: str = Query("pending", alias="status"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    b_id = resolve_brain_id(db, workspace_id, brain_id)
    query = db.query(PendingApproval).filter(
        PendingApproval.workspace_id == workspace_id,
        PendingApproval.brain_id == b_id,
    )
    if approval_status != "all":
        query = query.filter(PendingApproval.status == approval_status)
    approvals = query.order_by(PendingApproval.created_at.desc()).all()
    return {"approvals": [serialize_approval(a) for a in approvals]}


@router.post("/approvals/{approval_id}/review")
def review_approval(
    approval_id: int,
    payload: ApprovalReviewRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    appr = db.query(PendingApproval).filter(
        PendingApproval.id == approval_id,
        PendingApproval.workspace_id == workspace_id,
    ).first()
    if not appr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending approval not found")
    if appr.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approval đã được xử lý trước đó")

    appr.status = "approved" if payload.approved else "rejected"
    appr.reviewed_by = member.user_id
    appr.reviewed_at = datetime.utcnow()
    appr.review_notes = payload.review_notes

    execution_result = _apply_approval_outcome(db, appr, approved=payload.approved)

    db.commit()
    db.refresh(appr)
    return {"approval": serialize_approval(appr), "execution": execution_result}


def _apply_approval_outcome(db: Session, appr: PendingApproval, approved: bool) -> Optional[Dict[str, Any]]:
    details = appr.details or {}

    if appr.action_type.startswith("campaign."):
        campaign_id = details.get("campaign_id")
        if not campaign_id:
            return None
        campaign = db.query(MarketingCampaign).filter(
            MarketingCampaign.id == int(campaign_id),
            MarketingCampaign.workspace_id == appr.workspace_id,
        ).first()
        if not campaign:
            return None
        target_status = details.get("to_status", "active")
        if approved:
            campaign.status = target_status
        else:
            campaign.status = details.get("from_status", "draft")
        return {"campaign_id": str(campaign.id), "status": campaign.status, "new_status": campaign.status}

    if appr.action_type == "asset.publish":
        asset_id = details.get("asset_id")
        if not asset_id:
            return None
        asset = db.query(CampaignAsset).filter(
            CampaignAsset.id == int(asset_id),
            CampaignAsset.workspace_id == appr.workspace_id,
        ).first()
        if not asset:
            return None
        asset.approval_status = "approved" if approved else "rejected"
        return {"asset_id": str(asset.id), "approval_status": asset.approval_status, "new_status": asset.approval_status}

    return None
