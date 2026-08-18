from typing import Any, Dict
from sqlalchemy.orm import Session

from app.business.finance.finance_tools import get_financial_summary


class FinanceDataCapability:
    """Capability for querying verified accounting ledgers and cash position in PostgreSQL."""

    @classmethod
    def read_financial_position(cls, db: Session, workspace_id: int) -> Dict[str, Any]:
        summary = get_financial_summary(db=db, workspace_id=workspace_id)
        return {
            "status": "success",
            "workspace_id": str(workspace_id),
            "financial_summary": summary,
            "summary": "Retrieved verified TT58 accounting snapshot and cash position.",
        }
