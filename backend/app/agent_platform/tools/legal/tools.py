from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agent_platform.identity.context import ExecutionContext
from app.modules.legal.models import LegalChecklistItem, LegalObligation


async def legal_compliance_check_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R1: Đánh giá tuân thủ pháp lý theo danh mục checklist."""
    stmt = select(LegalChecklistItem).where(LegalChecklistItem.workspace_id == context.workspace_id)
    res = await db.execute(stmt)
    items = res.scalars().all()

    return {
        "status": "success",
        "total_checks": len(items),
        "compliant_count": sum(1 for i in items if getattr(i, "status", "") == "compliant"),
        "pending_count": sum(1 for i in items if getattr(i, "status", "") != "compliant"),
        "summary": "Đã rà soát danh mục tuân thủ pháp lý doanh nghiệp."
    }


async def legal_obligation_list_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R0: Xem các nghĩa vụ pháp lý và thời hạn thực hiện."""
    stmt = select(LegalObligation).where(LegalObligation.workspace_id == context.workspace_id)
    res = await db.execute(stmt)
    obligations = res.scalars().all()

    return {
        "status": "success",
        "total_obligations": len(obligations),
        "obligations": [
            {
                "id": str(o.id),
                "title": getattr(o, "title", "Nghĩa vụ pháp lý"),
                "due_date": str(getattr(o, "due_date", "")),
                "status": getattr(o, "status", "pending"),
            }
            for o in obligations[:10]
        ]
    }
