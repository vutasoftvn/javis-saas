from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.modules.legal.models import LegalChecklistItem
from app.agents.domains.legal.reasoning import LEGAL_DISCLAIMER


class LegalActionCapability:
    """Action capability for legal domain. Strictly scoped to drafting internal checklist records.
    
    Self-execution, automated signing, or government filing is STRICTLY FORBIDDEN.
    """

    @classmethod
    def record_checklist_item(
        cls,
        db: Session,
        workspace_id: int,
        title: str,
        citations: List[str],
    ) -> Dict[str, Any]:
        if not citations:
            raise ValueError("Legal action validation failure: Evidence citations required.")

        item = LegalChecklistItem(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            title=title,
            status="OPEN",
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        return {
            "status": "success",
            "checklist_item_id": str(item.id),
            "title": item.title,
            "item_status": item.status,
            "citations": citations,
            "disclaimer": LEGAL_DISCLAIMER,
            "policy_restriction": "L2_DRAFT_ONLY",
            "summary": f"Drafted internal legal checklist item '{title}' (ID: {item.id}).",
        }
