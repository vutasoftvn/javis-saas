from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agent_platform.identity.context import ExecutionContext
from app.modules.strategy.models import Project, OkrObjective, StrategyCanvas


async def project_read_portfolio_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R0: Đọc danh mục dự án trong doanh nghiệp."""
    stmt = select(Project).where(Project.brain_id == context.workspace_id)
    res = await db.execute(stmt)
    projects = res.scalars().all()

    return {
        "status": "success",
        "total_projects": len(projects),
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "status": getattr(p, "status", "active"),
                "stage": getattr(p, "stage", "mvp"),
            }
            for p in projects[:10]
        ]
    }


async def okr_read_overview_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R0: Xem tổng quan mục tiêu OKR và tiến độ."""
    stmt = select(OkrObjective)
    res = await db.execute(stmt)
    okrs = res.scalars().all()

    return {
        "status": "success",
        "total_okrs": len(okrs),
        "okrs": [
            {
                "id": str(o.id),
                "title": getattr(o, "title", "Mục tiêu chiến lược"),
                "progress": float(getattr(o, "progress", 0.0) or 0.0),
            }
            for o in okrs[:10]
        ]
    }


async def strategy_read_canvas_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R0: Đọc Canvas chiến lược của Founder."""
    stmt = select(StrategyCanvas).where(StrategyCanvas.workspace_id == context.workspace_id)
    res = await db.execute(stmt)
    canvas = res.scalars().first()

    return {
        "status": "success",
        "has_canvas": canvas is not None,
        "vision": getattr(canvas, "vision", "") if canvas else "",
        "mission": getattr(canvas, "mission", "") if canvas else "",
    }
