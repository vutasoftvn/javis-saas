from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from business.legal.models import LegalChecklistItem, LegalObligation
from workforce.agents.domains.legal.reasoning import LEGAL_DISCLAIMER


class LegalResearchCapability:
    """Research capability for auditing compliance obligations and checklist status."""

    @classmethod
    def audit_obligations(
        cls,
        db: Session,
        workspace_id: int,
    ) -> Dict[str, Any]:
        obligations = db.query(LegalObligation).filter(LegalObligation.workspace_id == workspace_id).all()
        return {
            "status": "success",
            "workspace_id": str(workspace_id),
            "obligations_count": len(obligations),
            "citations": [f"db.legal_obligations:{o.id}" for o in obligations] if obligations else ["db.legal_obligations:empty"],
            "disclaimer": LEGAL_DISCLAIMER,
            "policy_restriction": "L0_READ_ONLY",
            "summary": f"Audited {len(obligations)} legal obligation(s).",
        }
