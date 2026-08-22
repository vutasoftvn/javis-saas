from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from workforce.models import CostLedger
from core.snowflake import generate_snowflake_id


USD_TO_VND_RATE = 25400.0


class CostLedgerService:
    """Sổ cái tài chính bất biến (Immutable Cost Ledger) ghi nhận chi phí token và tài chính."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_entry(
        self,
        agent_key: str,
        provider: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        run_id: Optional[int] = None,
        task_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        billing_cycle: str = "12WY_Q3",
        meta: Optional[Dict[str, Any]] = None,
    ) -> CostLedger:
        cost_vnd = cost_usd * USD_TO_VND_RATE
        total_tokens = prompt_tokens + completion_tokens

        entry = CostLedger(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            run_id=run_id,
            task_id=task_id,
            agent_id=agent_id,
            agent_key=agent_key,
            provider=provider,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            cost_vnd=cost_vnd,
            billing_cycle=billing_cycle,
            meta_jsonb=meta or {},
            created_at=datetime.utcnow(),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_cost_summary(
        self,
        workspace_id: Optional[int] = None,
        billing_cycle: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tổng hợp chi phí theo từng Agent và Provider."""
        stmt = select(
            CostLedger.agent_key,
            CostLedger.provider,
            func.count(CostLedger.id).label("total_runs"),
            func.sum(CostLedger.total_tokens).label("sum_tokens"),
            func.sum(CostLedger.cost_usd).label("sum_cost_usd"),
            func.sum(CostLedger.cost_vnd).label("sum_cost_vnd"),
        )
        filters = []
        if workspace_id is not None:
            filters.append(CostLedger.workspace_id == workspace_id)
        if billing_cycle:
            filters.append(CostLedger.billing_cycle == billing_cycle)
        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.group_by(CostLedger.agent_key, CostLedger.provider)
        res = await self.db.execute(stmt)
        rows = res.all()

        breakdown = []
        total_spent_usd = 0.0
        total_spent_vnd = 0.0
        total_tokens_all = 0

        for r in rows:
            spent_usd = float(r.sum_cost_usd or 0.0)
            spent_vnd = float(r.sum_cost_vnd or 0.0)
            tokens = int(r.sum_tokens or 0)
            total_spent_usd += spent_usd
            total_spent_vnd += spent_vnd
            total_tokens_all += tokens
            breakdown.append({
                "agent_key": r.agent_key,
                "provider": r.provider,
                "total_runs": r.total_runs,
                "total_tokens": tokens,
                "cost_usd": round(spent_usd, 4),
                "cost_vnd": round(spent_vnd, 0),
            })

        return {
            "total_spent_usd": round(total_spent_usd, 4),
            "total_spent_vnd": round(total_spent_vnd, 0),
            "total_tokens": total_tokens_all,
            "rate_usd_to_vnd": USD_TO_VND_RATE,
            "breakdown": breakdown,
        }

    async def list_recent_entries(
        self,
        workspace_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[CostLedger]:
        stmt = select(CostLedger).order_by(desc(CostLedger.created_at))
        if workspace_id is not None:
            stmt = stmt.where(CostLedger.workspace_id == workspace_id)
        stmt = stmt.limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
