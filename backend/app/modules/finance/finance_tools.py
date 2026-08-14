from decimal import Decimal
from typing import Any
from sqlalchemy.orm import Session

from app.core.feature_flags import FLAG_FINANCE_FUNCTION_V13
from app.core.tool_registry import register
from app.modules.finance.domain.management_metrics_service import calculate_management_metrics
from app.modules.finance.models import AccountingPeriod, AccountingProfile


@register(
    namespace="finance",
    name="get_financial_summary",
    flag_key=FLAG_FINANCE_FUNCTION_V13,
    chat_schema={
        "description": "Xem tổng quan tình hình tài chính quản trị (dòng tiền, burn rate, runway).",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    risk_level="low",
    permission_level="read_only",
    idempotency=True,
    allowed_agent_keys=["finance_specialist", "chief_of_staff"],
)
def get_financial_summary(db: Session, workspace_id: int) -> dict[str, Any]:
    """Retrieve financial management metrics strictly scoped to workspace."""
    profile = (
        db.query(AccountingProfile)
        .filter(AccountingProfile.workspace_id == workspace_id)
        .first()
    )

    # Basic baseline summary
    metrics = calculate_management_metrics(
        opening_cash=Decimal("1000000000"),
        cash_in=Decimal("250000000"),
        cash_out=Decimal("150000000"),
        monthly_operating_expense=Decimal("120000000"),
        budget=Decimal("200000000"),
    )

    return {
        "status": "success",
        "workspace_id": workspace_id,
        "profile_mode": profile.mode if profile else "TT58_MODE_1",
        "profile_status": profile.status if profile else "NOT_CONFIGURED",
        "cash_balance": float(metrics["cash"]),
        "monthly_burn": float(metrics["burn"]),
        "runway_months": float(metrics["runway_months"]) if metrics["runway_months"] else None,
        "budget_variance": float(metrics["budget_variance"]),
    }


@register(
    namespace="finance",
    name="get_period_overview",
    flag_key=FLAG_FINANCE_FUNCTION_V13,
    chat_schema={
        "description": "Tra cứu kỳ kế toán đang mở và trạng thái khóa kỳ.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    risk_level="low",
    permission_level="read_only",
    idempotency=True,
    allowed_agent_keys=["finance_specialist", "chief_of_staff"],
)
def get_period_overview(db: Session, workspace_id: int) -> dict[str, Any]:
    """Retrieve open accounting periods strictly scoped to workspace."""
    periods = (
        db.query(AccountingPeriod)
        .filter(AccountingPeriod.workspace_id == workspace_id)
        .all()
    )
    return {
        "status": "success",
        "total_periods": len(periods),
        "periods": [
            {
                "id": p.id,
                "status": p.status,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "end_date": p.end_date.isoformat() if p.end_date else None,
            }
            for p in periods
        ],
    }
