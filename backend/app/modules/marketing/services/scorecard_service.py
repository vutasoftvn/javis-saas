from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.modules.marketing.models import MarketingExperiment, MarketingObjective
from app.modules.marketing.services.analytics_engine import AnalyticsEngine
from app.modules.strategy.models import TwelveWeekCycle, WeeklyCommitment, WeeklyPlan

# Trạng thái cam kết được coi là "đã hoàn thành" trong module 12 Week Year.
DONE_STATUSES = {"done", "completed"}
# Thử nghiệm đã có kết luận (§15) - dùng để tính nhịp học.
CLOSED_EXPERIMENT_STATUSES = {"win", "lose", "inconclusive", "iterate"}


class ScorecardService:
    """Tính điểm 12 Week Year (§10) từ dữ liệu thật của module strategy.

    Trước đây cockpit trả về hằng số 85.0 cho execution score. Điểm phải đến từ
    WeeklyCommitment/WeeklyPlan của chu kỳ 12 tuần đang chạy; nếu chưa có chu kỳ nào thì
    nói rõ "chưa có dữ liệu" thay vì bịa số.
    """

    @staticmethod
    def _active_cycle(db: Session, workspace_id: int, brain_id: int) -> Optional[TwelveWeekCycle]:
        cycle = db.query(TwelveWeekCycle).filter(
            TwelveWeekCycle.workspace_id == workspace_id,
            TwelveWeekCycle.brain_id == brain_id,
            TwelveWeekCycle.status == "active",
        ).order_by(TwelveWeekCycle.created_at.desc()).first()
        if cycle:
            return cycle
        return db.query(TwelveWeekCycle).filter(
            TwelveWeekCycle.workspace_id == workspace_id,
            TwelveWeekCycle.brain_id == brain_id,
        ).order_by(TwelveWeekCycle.created_at.desc()).first()

    @staticmethod
    def _weeks_elapsed(cycle: Optional[TwelveWeekCycle], plan_count: int) -> int:
        if cycle and cycle.start_date:
            delta_days = (datetime.utcnow() - cycle.start_date).days
            if delta_days >= 0:
                return max(1, min(12, delta_days // 7 + 1))
        return max(plan_count, 1)

    @classmethod
    def build(cls, db: Session, workspace_id: int, brain_id: int) -> Dict[str, Any]:
        cycle = cls._active_cycle(db, workspace_id, brain_id)

        commitments: List[WeeklyCommitment] = []
        plans: List[WeeklyPlan] = []
        if cycle:
            plans = db.query(WeeklyPlan).filter(
                WeeklyPlan.workspace_id == workspace_id,
                WeeklyPlan.cycle_id == cycle.id,
            ).all()
            plan_ids = [p.id for p in plans]
            if plan_ids:
                commitments = db.query(WeeklyCommitment).filter(
                    WeeklyCommitment.workspace_id == workspace_id,
                    WeeklyCommitment.weekly_plan_id.in_(plan_ids),
                ).all()

        completed = len([c for c in commitments if (c.status or "").lower() in DONE_STATUSES])

        objectives = db.query(MarketingObjective).filter(
            MarketingObjective.workspace_id == workspace_id,
            MarketingObjective.brain_id == brain_id,
            MarketingObjective.status == "active",
        ).all()
        objective_progress = [
            {"current_value": o.current_value or 0.0, "target_value": o.target_value or 0.0}
            for o in objectives
        ]

        experiments_closed = db.query(MarketingExperiment).filter(
            MarketingExperiment.workspace_id == workspace_id,
            MarketingExperiment.brain_id == brain_id,
            MarketingExperiment.status.in_(CLOSED_EXPERIMENT_STATUSES),
        ).count()

        scorecard = AnalyticsEngine.build_scorecard(
            commitments_completed=completed,
            total_commitments=len(commitments),
            objectives=objective_progress,
            experiments_closed=experiments_closed,
            weeks_elapsed=cls._weeks_elapsed(cycle, len(plans)),
        )
        scorecard["cycle"] = (
            {
                "id": str(cycle.id),
                "theme": cycle.theme,
                "status": cycle.status,
                "start_date": cycle.start_date.isoformat() if cycle.start_date else None,
                "end_date": cycle.end_date.isoformat() if cycle.end_date else None,
            }
            if cycle
            else None
        )
        scorecard["experiments_closed"] = experiments_closed
        scorecard["objectives_tracked"] = len(objectives)
        return scorecard
