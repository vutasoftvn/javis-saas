from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.workforce.identity.context import ExecutionContext
from app.business.finance.models import FinanceManagementSnapshot, AccountingProfile, FinancialTransaction
from app.core.snowflake import generate_snowflake_id


async def finance_read_summary_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R0: Đọc tổng quan tình hình tài chính quản trị (dòng tiền, doanh thu, chi phí)."""
    stmt = select(FinanceManagementSnapshot).where(
        FinanceManagementSnapshot.workspace_id == context.workspace_id
    ).order_by(desc(FinanceManagementSnapshot.as_of))
    res = await db.execute(stmt)
    snapshot = res.scalars().first()

    if not snapshot:
        return {
            "status": "empty",
            "workspace_id": context.workspace_id,
            "message": "Chưa có snapshot dữ liệu tài chính cho workspace này.",
            "data": {"cash": 0.0, "revenue": 0.0, "cost": 0.0, "profit": 0.0}
        }

    return {
        "status": "success",
        "workspace_id": context.workspace_id,
        "as_of": snapshot.as_of.isoformat() if hasattr(snapshot.as_of, 'isoformat') else str(snapshot.as_of),
        "data": {
            "cash": float(snapshot.cash or 0.0),
            "revenue": float(snapshot.revenue or 0.0),
            "cost": float(snapshot.cost or 0.0),
            "profit": float(snapshot.net_profit or 0.0),
        }
    }


async def finance_post_entry_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R4: Ghi nhận nghiệp vụ kế toán mới (Cần Human Approval)."""
    amount = float(args.get("amount", 0.0))
    category = args.get("category", "EXPENSE")
    description = args.get("description", "Agent-generated transaction")

    tx = FinancialTransaction(
        id=generate_snowflake_id(),
        workspace_id=context.workspace_id,
        amount=amount,
        tx_type=category,
        description=description,
    )
    db.add(tx)
    await db.flush()

    return {
        "status": "success",
        "transaction_id": str(tx.id),
        "amount": amount,
        "category": category,
        "message": "Ghi nhận nghiệp vụ tài chính thành công."
    }
