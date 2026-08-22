from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from business.legal.models import LegalChecklistItem, LegalObligation


class LegalDataCapability:
    """Capability for querying legal checklist items and obligations."""

    @classmethod
    def read_legal_posture(
        cls,
        db: Session,
        workspace_id: int,
    ) -> Dict[str, Any]:
        checklist = db.query(LegalChecklistItem).filter(LegalChecklistItem.workspace_id == workspace_id).all()
        obligations = db.query(LegalObligation).filter(LegalObligation.workspace_id == workspace_id).all()

        return {
            "status": "success",
            "workspace_id": str(workspace_id),
            "open_checklist_count": len([c for c in checklist if c.status == "OPEN"]),
            "checklist_items": [
                {"id": str(c.id), "title": c.title, "status": c.status}
                for c in checklist
            ],
            "obligations": [
                {"id": str(o.id), "title": o.title, "due_at": o.due_at.isoformat() if o.due_at else None, "status": o.status}
                for o in obligations
            ],
            "disclaimer": "COSA AI provides informational analysis, not formal legal advice. Human review is required.",
            "summary": f"Retrieved legal posture ({len(checklist)} checklist items, {len(obligations)} obligations).",
        }
