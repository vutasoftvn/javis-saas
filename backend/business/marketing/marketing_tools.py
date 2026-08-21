from typing import Any
from sqlalchemy.orm import Session

from core.feature_flags import FLAG_MARKETING_FUNCTION_V13
from core.tool_registry import register
from workforce.agents.domains.marketing.data import MarketingDataCapability


@register(
    namespace="marketing",
    name="get_marketing_overview",
    flag_key=FLAG_MARKETING_FUNCTION_V13,
    chat_schema={
        "description": "Xem tổng quan funnel và scorecard marketing (acquisition, conversion, revenue, retention).",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    risk_level="low",
    permission_level="read_only",
    idempotency=True,
    allowed_agent_keys=["marketing_specialist", "chief_of_staff"],
)
def get_marketing_overview(db: Session, workspace_id: int) -> dict[str, Any]:
    """Retrieve high-level marketing funnel/scorecard metrics strictly scoped to workspace."""
    return MarketingDataCapability.read_marketing_overview(db, workspace_id)
