# All models moved to core/marketing/models_validation.py (COSA Structure.md §49
# Business Core migration). Re-exported here for backward compatibility with
# existing `from business.marketing.models_validation import ...` call sites.
from business_core.marketing.models_validation import (  # noqa: F401
    EpistemicStatus,
    KnowledgeOrigin,
    ConfidenceLevel,
    AssumptionCategory,
    AssumptionStatus,
    EvidenceSourceType,
    EvidenceStrength,
    KnowledgeStatement,
    Assumption,
    Evidence,
    CanvasRevision,
    CustomerInterview,
    MarketingAttribution,
)
