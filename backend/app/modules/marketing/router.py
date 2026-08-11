import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.db.session import get_db
from app.db.models import Brain, WorkspaceMember

# Re-export all marketing schemas for backward compatibility
from app.modules.marketing.schemas import (
    CAMPAIGN_STATUSES,
    CAMPAIGN_STATUSES_REQUIRING_APPROVAL,
    EXPERIMENT_DECISIONS,
    METRIC_CATEGORIES,
    LOOP_TYPES,
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

# Re-export handlers and helpers from sub-routers
from app.modules.marketing.routers.cockpit_router import (
    router as cockpit_router,
    resolve_brain_id,
    serialize_context,
    serialize_loop,
    serialize_decision,
    serialize_recommendation,
    serialize_metric,
    get_cockpit_summary,
    get_analytics_overview,
    get_funnel,
    get_marketing_context,
    create_or_update_marketing_context,
    get_customer_research,
    update_customer_research,
    get_product_marketing,
    update_product_marketing,
    get_offer_architecture,
    update_offer_architecture,
    get_12w_plan,
    update_12w_plan,
    list_loops,
    create_loop,
    update_loop,
    trigger_loop,
    calculate_attribution,
    list_decisions,
    create_decision,
    update_decision,
    list_recommendations,
    create_recommendation,
    update_recommendation_status,
)
from app.modules.marketing.routers.campaign_router import (
    router as campaign_router,
    serialize_objective,
    serialize_campaign,
    serialize_asset,
    serialize_experiment,
    serialize_learning,
    serialize_approval,
    list_marketing_objectives,
    create_marketing_objective,
    update_marketing_objective,
    delete_marketing_objective,
    list_campaigns,
    create_campaign,
    get_campaign,
    update_campaign,
    change_campaign_status,
    delete_campaign,
    create_campaign_asset,
    request_asset_approval,
    list_experiments,
    create_experiment,
    evaluate_experiment,
    decide_experiment,
    list_learnings,
    create_learning,
    list_metrics,
    upsert_metric,
    get_metric_history,
    list_skills,
    list_skill_executions,
    execute_skill,
    list_approvals,
    review_approval,
)

router = APIRouter()

# Include modular marketing sub-routers
router.include_router(cockpit_router)
router.include_router(campaign_router)
