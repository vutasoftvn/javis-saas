# All Marketing models moved to core/marketing/models.py (COSA Structure.md §49
# Business Core migration). Re-exported here for backward compatibility with
# existing `from business.marketing.models import ...` call sites.
from business_core.marketing.models import (  # noqa: F401
    MarketingContext,
    MarketingObjective,
    MarketingCampaign,
    CampaignAsset,
    MarketingMetric,
    MetricSnapshot,
    MarketingExperiment,
    MarketingLearning,
    SkillExecution,
    SkillRegistry,
    PendingApproval,
    MarketingLoop,
    MarketingDecision,
    MarketingRecommendation,
)
