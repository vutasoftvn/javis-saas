from typing import Any, Dict, List
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.sales.models import SalesLead, SalesOpportunity


STAGE_PROBABILITY_DEFAULTS = {
    "DISCOVERY": 0.1,
    "QUALIFIED": 0.25,
    "SOLUTION": 0.4,
    "PROPOSAL": 0.6,
    "NEGOTIATION": 0.8,
    "WON": 1.0,
    "LOST": 0.0,
}


class FunnelMetricsService:
    @staticmethod
    def get_funnel_metrics(db: Session, workspace_id: int) -> Dict[str, Any]:
        # 1. Lead counts
        total_leads = db.query(func.count(SalesLead.id)).filter(SalesLead.workspace_id == workspace_id).scalar() or 0
        qualified_leads = (
            db.query(func.count(SalesLead.id))
            .filter(SalesLead.workspace_id == workspace_id, SalesLead.qualification_status == "QUALIFIED")
            .scalar()
            or 0
        )
        converted_leads = (
            db.query(func.count(SalesLead.id))
            .filter(SalesLead.workspace_id == workspace_id, SalesLead.stage == "CONVERTED")
            .scalar()
            or 0
        )

        # 2. Opportunity counts & values
        total_opps = (
            db.query(func.count(SalesOpportunity.id))
            .filter(SalesOpportunity.workspace_id == workspace_id)
            .scalar()
            or 0
        )
        won_opps = (
            db.query(func.count(SalesOpportunity.id))
            .filter(SalesOpportunity.workspace_id == workspace_id, SalesOpportunity.stage == "WON")
            .scalar()
            or 0
        )

        open_opps = (
            db.query(SalesOpportunity)
            .filter(SalesOpportunity.workspace_id == workspace_id, SalesOpportunity.stage.notin_(["WON", "LOST"]))
            .all()
        )

        pipeline_value = 0.0
        weighted_pipeline = 0.0
        opp_breakdown = []

        for opp in open_opps:
            val = opp.estimated_value or 0.0
            pipeline_value += val

            if opp.probability is not None:
                prob = opp.probability
                prob_source = "manual"
            else:
                prob = STAGE_PROBABILITY_DEFAULTS.get(opp.stage.upper(), 0.1)
                prob_source = "stage-default"

            weighted_val = val * prob
            weighted_pipeline += weighted_val

            opp_breakdown.append(
                {
                    "opportunity_id": str(opp.id),
                    "product": opp.product,
                    "stage": opp.stage,
                    "estimated_value": val,
                    "probability": prob,
                    "probability_source": prob_source,
                    "weighted_value": weighted_val,
                }
            )

        # 3. Compute Ratios
        lead_to_qualified_rate = (qualified_leads / total_leads) if total_leads > 0 else 0.0
        qualified_to_opportunity_rate = (converted_leads / qualified_leads) if qualified_leads > 0 else 0.0
        opportunity_to_won_rate = (won_opps / total_opps) if total_opps > 0 else 0.0

        return {
            "total_leads": total_leads,
            "qualified_leads": qualified_leads,
            "converted_leads": converted_leads,
            "total_opportunities": total_opps,
            "won_opportunities": won_opps,
            "lead_to_qualified_rate": round(lead_to_qualified_rate, 4),
            "qualified_to_opportunity_rate": round(qualified_to_opportunity_rate, 4),
            "opportunity_to_won_rate": round(opportunity_to_won_rate, 4),
            "pipeline_value": round(pipeline_value, 2),
            "weighted_pipeline": round(weighted_pipeline, 2),
            "open_opportunities": opp_breakdown,
        }
