from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.business.marketing.services.funnel_engine import FunnelEngine
from app.business.marketing.services.scorecard_service import ScorecardService


class MarketingDataCapability:
    """Capability for querying marketing scorecard, funnels, and performance data."""

    @classmethod
    def read_marketing_overview(
        cls,
        db: Session,
        workspace_id: int,
    ) -> Dict[str, Any]:
        funnel = FunnelEngine.build_funnel(db, workspace_id)
        scorecard = ScorecardService.build(db, workspace_id)

        return {
            "status": "success",
            "workspace_id": str(workspace_id),
            "funnel": funnel,
            "scorecard": scorecard,
            "summary": "Marketing funnel and scorecard data retrieved successfully.",
        }
