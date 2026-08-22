from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from workforce.models import AgentBudget
from core.snowflake import generate_snowflake_id


class BudgetExceededError(Exception):
    pass


class BudgetingEngine:
    """Quản trị hạn mức ngân sách Token & USD, tự động ngắt (Circuit Breaker) khi cạn quota."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_agent_budget(
        self,
        agent_key: str,
        workspace_id: Optional[int] = None,
        default_limit_usd: float = 50.0,
    ) -> AgentBudget:
        stmt = select(AgentBudget).where(AgentBudget.agent_key == agent_key)
        if workspace_id is not None:
            stmt = stmt.where(AgentBudget.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        budget = res.scalars().first()

        if not budget:
            budget = AgentBudget(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                agent_key=agent_key,
                cycle_type="12_WEEK_YEAR",
                limit_usd=default_limit_usd,
                spent_usd=0.0,
                soft_limit_percent=0.8,
                is_blocked=False,
                period_start=datetime.utcnow(),
            )
            self.db.add(budget)
            await self.db.flush()

        return budget

    async def check_budget_quota(
        self,
        agent_key: str,
        workspace_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Kiểm tra xem Agent có đủ ngân sách chạy tiếp hay không."""
        budget = await self.get_or_create_agent_budget(agent_key, workspace_id)

        limit_usd = float(budget.limit_usd) if budget.limit_usd is not None else 50.0
        spent_usd = float(budget.spent_usd) if budget.spent_usd is not None else 0.0
        soft_limit = float(budget.soft_limit_percent) if budget.soft_limit_percent is not None else 0.8

        if budget.is_blocked or (limit_usd > 0 and spent_usd >= limit_usd):
            raise BudgetExceededError(
                f"Agent '{agent_key}' has exceeded its budget quota ({spent_usd:.2f}/{limit_usd:.2f} USD). Execution blocked."
            )

        usage_ratio = spent_usd / limit_usd if limit_usd > 0 else 0.0
        is_warning = usage_ratio >= soft_limit

        return {
            "agent_key": agent_key,
            "limit_usd": limit_usd,
            "spent_usd": spent_usd,
            "remaining_usd": max(0.0, limit_usd - spent_usd),
            "usage_percent": round(usage_ratio * 100, 1),
            "is_warning": is_warning,
            "is_blocked": bool(budget.is_blocked),
        }

    async def record_spend(
        self,
        agent_key: str,
        amount_usd: float,
        workspace_id: Optional[int] = None,
    ) -> AgentBudget:
        budget = await self.get_or_create_agent_budget(agent_key, workspace_id)
        budget.spent_usd = (budget.spent_usd or 0.0) + amount_usd
        if budget.limit_usd is not None and budget.spent_usd >= budget.limit_usd:
            budget.is_blocked = True
        await self.db.flush()
        return budget

    async def set_budget_limit(
        self,
        agent_key: str,
        limit_usd: float,
        workspace_id: Optional[int] = None,
        cycle_type: str = "12_WEEK_YEAR",
    ) -> AgentBudget:
        budget = await self.get_or_create_agent_budget(agent_key, workspace_id, default_limit_usd=limit_usd)
        budget.limit_usd = limit_usd
        budget.cycle_type = cycle_type
        if budget.spent_usd < budget.limit_usd:
            budget.is_blocked = False
        await self.db.flush()
        return budget
