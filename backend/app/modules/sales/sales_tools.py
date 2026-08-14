from typing import Any, Optional
from sqlalchemy.orm import Session

from app.core.feature_flags import FLAG_SALES_CRM_CORE_V13_2
from app.core.tool_registry import register
from app.modules.sales.domain.funnel import FunnelMetricsService
from app.modules.sales.models import SalesActivity, SalesLead, SalesOpportunity


@register(
    namespace="sales",
    name="get_pipeline_summary",
    flag_key=FLAG_SALES_CRM_CORE_V13_2,
    chat_schema={
        "description": "Xem tổng hợp pipeline bán hàng, số lượng lead, cơ hội và giá trị dự kiến theo stage.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    risk_level="low",
    permission_level="read_only",
    idempotency=True,
    allowed_agent_keys=["sales_specialist", "chief_of_staff"],
)
def get_pipeline_summary(db: Session, workspace_id: int) -> dict[str, Any]:
    """Retrieve high-level sales pipeline metrics strictly scoped to workspace."""
    metrics = FunnelMetricsService.get_funnel_metrics(db, workspace_id)
    return {
        "status": "success",
        "workspace_id": workspace_id,
        "metrics": metrics,
    }


@register(
    namespace="sales",
    name="get_lead_details",
    flag_key=FLAG_SALES_CRM_CORE_V13_2,
    chat_schema={
        "description": "Tra cứu thông tin chi tiết của một lead/khách hàng tiềm năng theo lead_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "integer",
                    "description": "ID định danh của lead",
                }
            },
            "required": ["lead_id"],
        },
    },
    risk_level="low",
    permission_level="read_only",
    idempotency=True,
    allowed_agent_keys=["sales_specialist", "chief_of_staff"],
)
def get_lead_details(db: Session, workspace_id: int, lead_id: int) -> dict[str, Any]:
    """Retrieve details for a specific lead strictly scoped to workspace."""
    lead = (
        db.query(SalesLead)
        .filter(SalesLead.id == lead_id, SalesLead.workspace_id == workspace_id)
        .first()
    )
    if not lead:
        return {
            "status": "not_found",
            "message": f"Lead with id {lead_id} does not exist in workspace {workspace_id}",
        }

    return {
        "status": "success",
        "lead": {
            "id": lead.id,
            "name": lead.name,
            "company": lead.company,
            "stage": lead.stage,
            "qualification_status": lead.qualification_status,
            "fit_score": lead.fit_score,
            "value": float(lead.value) if lead.value else None,
            "source": lead.source,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
        },
    }


@register(
    namespace="sales",
    name="list_active_opportunities",
    flag_key=FLAG_SALES_CRM_CORE_V13_2,
    chat_schema={
        "description": "Danh sách các cơ hội bán hàng đang mở (chưa WON/LOST).",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Số lượng tối đa kết quả cần lấy (mặc định 20)",
                }
            },
            "required": [],
        },
    },
    risk_level="low",
    permission_level="read_only",
    idempotency=True,
    allowed_agent_keys=["sales_specialist", "chief_of_staff"],
)
def list_active_opportunities(
    db: Session, workspace_id: int, limit: int = 20
) -> dict[str, Any]:
    """List open opportunities strictly scoped to workspace."""
    opps = (
        db.query(SalesOpportunity)
        .filter(
            SalesOpportunity.workspace_id == workspace_id,
            SalesOpportunity.stage.notin_(["WON", "LOST"]),
        )
        .limit(limit)
        .all()
    )
    return {
        "status": "success",
        "total": len(opps),
        "opportunities": [
            {
                "id": o.id,
                "product": o.product,
                "stage": o.stage,
                "estimated_value": float(o.estimated_value) if o.estimated_value else 0.0,
                "currency": o.currency,
                "expected_close_date": o.expected_close_date.isoformat() if o.expected_close_date else None,
            }
            for o in opps
        ],
    }


@register(
    namespace="sales",
    name="create_activity",
    flag_key=FLAG_SALES_CRM_CORE_V13_2,
    chat_schema={
        "description": "Ghi nhận một hoạt động tương tác (cuộc gọi, email follow-up, ghi chú) cho lead hoặc opportunity.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Loại đối tượng (lead, opportunity, account, contact)",
                },
                "entity_id": {
                    "type": "integer",
                    "description": "ID của đối tượng",
                },
                "activity_type": {
                    "type": "string",
                    "description": "Loại tương tác (RESEARCH, EMAIL, MESSAGE, CALL, MEETING, DEMO, PROPOSAL, FOLLOW_UP, NOTE)",
                },
                "summary": {
                    "type": "string",
                    "description": "Nội dung tóm tắt tương tác",
                },
                "outcome": {
                    "type": "string",
                    "description": "Kết quả tương tác",
                },
                "next_action": {
                    "type": "string",
                    "description": "Hành động tiếp theo",
                },
            },
            "required": ["entity_type", "entity_id", "activity_type", "summary"],
        },
    },
    risk_level="low",
    permission_level="scoped_write",
    requires_approval=False,
    idempotency=False,
    allowed_agent_keys=["sales_specialist", "chief_of_staff"],
)
def create_activity(
    db: Session,
    workspace_id: int,
    entity_type: str,
    entity_id: int,
    activity_type: str,
    summary: str,
    outcome: Optional[str] = None,
    next_action: Optional[str] = None,
    actor_id: Optional[int] = None,
) -> dict[str, Any]:
    """Create a sales activity log strictly scoped to workspace."""
    from app.core.snowflake import generate_snowflake_id
    from datetime import datetime, timezone

    activity = SalesActivity(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        entity_type=entity_type.lower(),
        entity_id=entity_id,
        activity_type=activity_type.upper(),
        summary=summary,
        outcome=outcome,
        next_action=next_action,
        actor_id=actor_id,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)

    return {
        "status": "success",
        "activity_id": activity.id,
        "entity_type": activity.entity_type,
        "entity_id": activity.entity_id,
        "activity_type": activity.activity_type,
        "summary": activity.summary,
    }
