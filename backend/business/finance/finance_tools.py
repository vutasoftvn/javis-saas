from typing import Any, Optional
from sqlalchemy.orm import Session

from core.feature_flags import FLAG_FINANCE_FUNCTION_V13
from core.tool_registry import register
from business.finance.models import AccountingPeriod, AccountingProfile, FinanceManagementSnapshot


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
    """Retrieve the latest real financial management snapshot strictly scoped to workspace.

    Reads `FinanceManagementSnapshot` - the same table `reports_router.py` serves to the
    UI - instead of computing placeholder numbers, so an agent never treats fabricated
    figures as evidence.
    """
    profile = (
        db.query(AccountingProfile)
        .filter(AccountingProfile.workspace_id == workspace_id)
        .first()
    )
    snapshot = (
        db.query(FinanceManagementSnapshot)
        .filter(FinanceManagementSnapshot.workspace_id == workspace_id)
        .order_by(FinanceManagementSnapshot.as_of.desc())
        .first()
    )

    if snapshot is None:
        return {
            "status": "not_configured",
            "workspace_id": workspace_id,
            "profile_mode": profile.mode if profile else "TT58_MODE_1",
            "profile_status": profile.status if profile else "NOT_CONFIGURED",
            "message": "No financial management snapshot has been generated for this workspace yet",
        }

    return {
        "status": "success",
        "workspace_id": workspace_id,
        "profile_mode": profile.mode if profile else "TT58_MODE_1",
        "profile_status": profile.status if profile else "NOT_CONFIGURED",
        "as_of": snapshot.as_of.isoformat(),
        "cash_balance": float(snapshot.cash),
        "monthly_burn": float(snapshot.burn),
        "runway_months": float(snapshot.runway_months) if snapshot.runway_months is not None else None,
        "budget_variance": float(snapshot.budget_variance) if snapshot.budget_variance is not None else None,
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


@register(
    namespace="finance",
    name="analyze_financial_data",
    flag_key=FLAG_FINANCE_FUNCTION_V13,
    chat_schema=None,
    risk_level="medium",
    permission_level="scoped_write",
    idempotency=False,
    allowed_agent_keys=["finance_specialist", "finance_data_agent", "chief_of_staff"],
)
def analyze_financial_data(
    db: Session,
    workspace_id: int,
    user_id: int,
    csv_content: str,
    agent_run_id: Optional[int] = None,
) -> dict[str, Any]:
    """Enqueue an isolated finance CSV data analysis job in sandbox."""
    from workforce.agents.execution.analysis_service import DomainAnalysisService

    job = DomainAnalysisService.create_finance_analysis_job(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        csv_content=csv_content,
        agent_run_id=agent_run_id,
    )
    return {
        "status": "queued",
        "job_id": str(job.id),
        "workspace_id": workspace_id,
    }
