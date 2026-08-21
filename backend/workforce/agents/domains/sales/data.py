from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from core.snowflake import generate_snowflake_id
from business.sales.domain.funnel import FunnelMetricsService
from business.sales.models import SalesLead, SalesActivity, SalesOpportunity


class SalesDataCapability:
    """Capability for querying pipeline state and updating internal CRM records in PostgreSQL."""

    @classmethod
    def read_pipeline(cls, db: Session, workspace_id: int) -> Dict[str, Any]:
        metrics = FunnelMetricsService.get_funnel_metrics(db, workspace_id)
        leads = db.query(SalesLead).filter(SalesLead.workspace_id == workspace_id).limit(20).all()

        return {
            "status": "success",
            "workspace_id": str(workspace_id),
            "funnel_metrics": metrics,
            "leads_sample": [
                {
                    "id": str(l.id),
                    "name": l.name,
                    "company": l.company,
                    "stage": l.stage,
                    "fit_score": l.fit_score,
                }
                for l in leads
            ],
        }

    @classmethod
    def update_crm_stage(
        cls,
        db: Session,
        workspace_id: int,
        lead_id: Optional[int] = None,
        new_stage: str = "contacted",
        activity_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        updated_count = 0
        if lead_id:
            lead = db.query(SalesLead).filter(SalesLead.id == lead_id, SalesLead.workspace_id == workspace_id).first()
            if lead:
                lead.stage = new_stage
                updated_count = 1
                
                # Record Activity
                act = SalesActivity(
                    id=generate_snowflake_id(),
                    workspace_id=workspace_id,
                    lead_id=lead.id,
                    type="outreach",
                    subject=activity_title or f"Outbound campaign dispatched - stage changed to {new_stage}",
                )
                db.add(act)
                db.commit()

        return {
            "status": "success",
            "records_updated": updated_count,
            "stage": new_stage,
            "summary": f"CRM state updated: stage set to '{new_stage}'.",
        }
