from typing import Dict, Any, Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.workforce.models import (
    AgentDefinition, AgentHeartbeat, ApprovalRequest,
    AgentBudget, CostLedger, AgentRoutine, RoutineExecution,
    WorkProduct, DecisionRecord
)
from app.workforce.governance.cost_ledger_service import USD_TO_VND_RATE


class ControlPlaneDashboardService:
    """Tổng hợp toàn bộ chỉ số thời gian thực của COSA AI Workforce Control Plane."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_summary(self, workspace_id: Optional[int] = None) -> Dict[str, Any]:
        # 1. Workforce Metrics
        agents_stmt = select(AgentDefinition)
        if workspace_id is not None:
            agents_stmt = agents_stmt.where(AgentDefinition.workspace_id == workspace_id)
        agents_res = await self.db.execute(agents_stmt)
        all_agents = list(agents_res.scalars().all())

        department_counts: Dict[str, int] = {}
        for a in all_agents:
            dept = a.department or "executive"
            department_counts[dept] = department_counts.get(dept, 0) + 1

        # Heartbeat health counts
        hb_stmt = select(AgentHeartbeat)
        if workspace_id is not None:
            hb_stmt = hb_stmt.where(AgentHeartbeat.workspace_id == workspace_id)
        hb_res = await self.db.execute(hb_stmt)
        all_hb = list(hb_res.scalars().all())
        health_summary = {"HEALTHY": 0, "DEGRADED": 0, "STALLED": 0, "OFFLINE": 0}
        for h in all_hb:
            if h.status in health_summary:
                health_summary[h.status] += 1

        # 2. Financial Accountability
        ledger_stmt = select(CostLedger)
        if workspace_id is not None:
            ledger_stmt = ledger_stmt.where(CostLedger.workspace_id == workspace_id)
        ledger_res = await self.db.execute(ledger_stmt)
        entries = list(ledger_res.scalars().all())

        total_usd = sum(e.cost_usd for e in entries)
        total_vnd = sum(e.cost_vnd for e in entries)
        total_tokens = sum(e.total_tokens for e in entries)

        # Budgets overview
        b_stmt = select(AgentBudget)
        if workspace_id is not None:
            b_stmt = b_stmt.where(AgentBudget.workspace_id == workspace_id)
        b_res = await self.db.execute(b_stmt)
        all_budgets = list(b_res.scalars().all())
        total_budget_limit = sum(b.limit_usd for b in all_budgets)
        total_budget_spent = sum(b.spent_usd for b in all_budgets)

        # 3. Governance & Approval Inbox
        appr_stmt = select(ApprovalRequest).where(ApprovalRequest.status == "PENDING")
        if workspace_id is not None:
            appr_stmt = appr_stmt.where(ApprovalRequest.workspace_id == workspace_id)
        appr_res = await self.db.execute(appr_stmt)
        pending_approvals = list(appr_res.scalars().all())
        critical_count = sum(1 for a in pending_approvals if a.risk_level == "CRITICAL")
        high_count = sum(1 for a in pending_approvals if a.risk_level == "HIGH")

        # 4. 12-Week Year Routines
        r_stmt = select(AgentRoutine)
        if workspace_id is not None:
            r_stmt = r_stmt.where(AgentRoutine.workspace_id == workspace_id)
        r_res = await self.db.execute(r_stmt)
        all_routines = list(r_res.scalars().all())

        rx_stmt = select(RoutineExecution)
        if workspace_id is not None:
            rx_stmt = rx_stmt.where(RoutineExecution.workspace_id == workspace_id)
        rx_res = await self.db.execute(rx_stmt)
        all_routine_execs = list(rx_res.scalars().all())

        # 5. Work Products & Decision Records
        wp_stmt = select(WorkProduct)
        if workspace_id is not None:
            wp_stmt = wp_stmt.where(WorkProduct.workspace_id == workspace_id)
        wp_res = await self.db.execute(wp_stmt)
        all_wp = list(wp_res.scalars().all())

        wp_status_counts = {
            "DRAFT": sum(1 for w in all_wp if w.status == "DRAFT"),
            "ACCEPTED": sum(1 for w in all_wp if w.status == "ACCEPTED"),
            "REVISION_REQUESTED": sum(1 for w in all_wp if w.status == "REVISION_REQUESTED"),
            "REJECTED": sum(1 for w in all_wp if w.status == "REJECTED"),
        }

        dr_stmt = select(DecisionRecord)
        if workspace_id is not None:
            dr_stmt = dr_stmt.where(DecisionRecord.workspace_id == workspace_id)
        dr_res = await self.db.execute(dr_stmt)
        all_dr = list(dr_res.scalars().all())

        return {
            "workforce": {
                "total_agents": len(all_agents),
                "by_department": department_counts,
                "health_summary": health_summary,
            },
            "financial": {
                "total_spent_usd": round(total_usd, 4),
                "total_spent_vnd": round(total_vnd, 0),
                "total_tokens_consumed": total_tokens,
                "exchange_rate": USD_TO_VND_RATE,
                "total_budget_limit_usd": round(total_budget_limit, 2),
                "total_budget_spent_usd": round(total_budget_spent, 2),
                "budget_utilization_percent": round((total_budget_spent / total_budget_limit * 100), 1) if total_budget_limit > 0 else 0.0,
            },
            "governance": {
                "pending_approvals_total": len(pending_approvals),
                "critical_risk_tickets": critical_count,
                "high_risk_tickets": high_count,
            },
            "orchestration": {
                "routines_count": len(all_routines),
                "total_routine_executions": len(all_routine_execs),
            },
            "work_products": {
                "total_products": len(all_wp),
                "status_breakdown": wp_status_counts,
                "decision_records_count": len(all_dr),
            },
        }
