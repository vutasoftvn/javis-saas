from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.platform.license.models import Handoff


class LearningResearchCapability:
    """Research capability for auditing cross-domain handoffs and execution anomalies."""

    @classmethod
    def audit_recent_handoffs(
        cls,
        db: Session,
        workspace_id: int,
    ) -> Dict[str, Any]:
        handoffs = (
            db.query(Handoff)
            .filter(Handoff.workspace_id == workspace_id)
            .order_by(Handoff.created_at.desc())
            .limit(10)
            .all()
        )
        return {
            "status": "success",
            "workspace_id": str(workspace_id),
            "handoffs_audited": len(handoffs),
            "findings": [
                {
                    "handoff_id": str(h.id),
                    "from_role": h.from_function,
                    "to_role": h.to_function,
                    "status": h.status,
                }
                for h in handoffs
            ],
            "summary": f"Audited {len(handoffs)} recent cross-functional handoffs.",
        }
