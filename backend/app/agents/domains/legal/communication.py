from typing import Any, Dict, List, Optional
from app.agents.domains.legal.reasoning import LEGAL_DISCLAIMER


class LegalCommunicationCapability:
    """Communication capability for drafting counsel briefing memos (draft-only, human-in-the-loop)."""

    @classmethod
    def draft_counsel_memo(
        cls,
        subject: str,
        background: str,
        citations: List[str],
    ) -> Dict[str, Any]:
        if not citations:
            raise ValueError("Legal communication validation failure: Evidence citations required.")
        return {
            "status": "success",
            "memo_subject": f"LEGAL BRIEF: {subject}",
            "memo_body": f"Background:\n{background}\n\nKey Inquiries for Counsel:\n1. Risk evaluation\n2. Filing requirements",
            "citations": citations,
            "disclaimer": LEGAL_DISCLAIMER,
            "policy_restriction": "L2_DRAFT_ONLY",
            "summary": f"Drafted counsel memo for '{subject}'.",
        }
