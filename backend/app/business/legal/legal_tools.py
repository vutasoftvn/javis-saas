from typing import Any
from sqlalchemy.orm import Session

from app.core.feature_flags import FLAG_LEGAL_FUNCTION_V13
from app.core.tool_registry import register
from app.workforce.agents.domains.legal.data import LegalDataCapability


@register(
    namespace="legal",
    name="get_legal_posture_summary",
    flag_key=FLAG_LEGAL_FUNCTION_V13,
    chat_schema={
        "description": "Xem tổng quan tình trạng pháp lý: checklist tuân thủ đang mở và các nghĩa vụ pháp lý sắp đến hạn.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    risk_level="low",
    permission_level="read_only",
    idempotency=True,
    allowed_agent_keys=["legal_specialist", "chief_of_staff"],
)
def get_legal_posture_summary(db: Session, workspace_id: int) -> dict[str, Any]:
    """Retrieve real legal checklist/obligation posture strictly scoped to workspace.

    Thin registered-tool wrapper around LegalDataCapability.read_legal_posture,
    mirroring the get_pipeline_summary/get_financial_summary pattern (real DB
    query, no fabricated data) so ChiefOfStaffOrchestrator's specialist
    registry (G3 §1A) can dispatch a legal delegation the same way it
    dispatches sales/finance.
    """
    return LegalDataCapability.read_legal_posture(db, workspace_id)
