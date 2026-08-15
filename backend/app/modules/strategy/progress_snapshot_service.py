"""Progress Snapshot and N-Week Timeline Service.

Constructs versioned, tenancy-scoped progress payloads across
cycles, OKRs, tasks, blockers, and verified metrics.
"""

from datetime import datetime, timezone, date
import logging
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.modules.strategy.models import TwelveWeekCycle, OkrCycle, OkrObjective, KeyResult
from app.modules.tasks.models import Task
from app.modules.company_runtime.models import Blocker
from app.agents.proposals.models import AgentProposal

logger = logging.getLogger(__name__)


class ProgressSnapshotService:
    """Aggregates and formats business execution status for Chat, Voice, and Reporting."""

    @staticmethod
    def calculate_current_week(start_date: Optional[Any], duration_weeks: int = 13) -> int:
        """Dynamically deduces current week index from start_date and clamps in [1, duration_weeks]."""
        if not start_date or not isinstance(start_date, (date, datetime)):
            return 1
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        today = datetime.now(timezone.utc).date()
        if today < start_date:
            return 1
        delta_days = (today - start_date).days
        week_idx = (delta_days // 7) + 1
        duration = duration_weeks if isinstance(duration_weeks, int) and duration_weeks > 0 else 13
        return max(1, min(duration, week_idx))

    @staticmethod
    def generate_snapshot(
        db: Session,
        workspace_id: int,
        cycle_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Constructs a deterministic, tenancy-scoped progress snapshot."""
        now = datetime.now(timezone.utc)
        
        # 1. Fetch active cycle (TwelveWeekCycle or OkrCycle)
        cycle_query = db.query(TwelveWeekCycle).filter(
            TwelveWeekCycle.workspace_id == workspace_id
        )
        if cycle_id:
            cycle_query = cycle_query.filter(TwelveWeekCycle.id == cycle_id)
        else:
            cycle_query = cycle_query.filter(TwelveWeekCycle.status == "active").order_by(TwelveWeekCycle.created_at.desc())
        
        cycle = cycle_query.first()
        raw_duration = getattr(cycle, "duration_weeks", 13) if cycle else 13
        duration_weeks = raw_duration if isinstance(raw_duration, int) and raw_duration > 0 else 13
        start_date = getattr(cycle, "start_date", None) if cycle else None
        current_week = ProgressSnapshotService.calculate_current_week(start_date, duration_weeks)

        # 2. OKRs & Key Results
        objectives = []
        okr_cycle = db.query(OkrCycle).filter(
            OkrCycle.workspace_id == workspace_id,
            OkrCycle.status == "active"
        ).order_by(OkrCycle.created_at.desc()).first()

        if okr_cycle:
            objs = db.query(OkrObjective).filter(
                OkrObjective.cycle_id == okr_cycle.id,
                OkrObjective.workspace_id == workspace_id
            ).all()
            for obj in objs:
                krs = db.query(KeyResult).filter(
                    KeyResult.objective_id == obj.id,
                    KeyResult.workspace_id == workspace_id
                ).all()
                objectives.append({
                    "id": str(obj.id),
                    "title": obj.title,
                    "progress_percentage": obj.progress_percentage if hasattr(obj, "progress_percentage") else 0.0,
                    "key_results": [
                        {
                            "id": str(kr.id),
                            "title": kr.title,
                            "target_value": kr.target_value if hasattr(kr, "target_value") else 100.0,
                            "current_value": kr.current_value if hasattr(kr, "current_value") else 0.0,
                        }
                        for kr in krs
                    ]
                })

        # 3. Tasks & Commitments
        total_tasks = db.query(func.count(Task.id)).filter(Task.workspace_id == workspace_id).scalar() or 0
        completed_tasks = db.query(func.count(Task.id)).filter(
            Task.workspace_id == workspace_id,
            Task.status.in_(["done", "completed"])
        ).scalar() or 0
        in_progress_tasks = db.query(func.count(Task.id)).filter(
            Task.workspace_id == workspace_id,
            Task.status == "in_progress"
        ).scalar() or 0

        # 4. Structured Blockers & Pending Approvals
        blockers = []
        active_blockers = db.query(Blocker).filter(
            Blocker.workspace_id == workspace_id,
            Blocker.status == "OPEN"
        ).all()
        for b in active_blockers:
            blockers.append({
                "id": str(b.id),
                "title": b.title if hasattr(b, "title") else "Blocker",
                "severity": b.severity if hasattr(b, "severity") else "MEDIUM",
            })

        pending_proposals_count = db.query(func.count(AgentProposal.id)).filter(
            AgentProposal.workspace_id == workspace_id,
            AgentProposal.status == "pending"
        ).scalar() or 0

        # 5. Timeline array
        timeline = []
        for w in range(1, duration_weeks + 1):
            status_w = "completed" if w < current_week else ("active" if w == current_week else "upcoming")
            timeline.append({
                "week_index": w,
                "focus": f"Tuần {w}: {'Đánh giá & Chuyển giao' if w == duration_weeks else 'Thực thi mục tiêu'}",
                "status": status_w,
                "is_current": w == current_week,
            })

        return {
            "snapshot_version": "1.0",
            "workspace_id": str(workspace_id),
            "generated_at": now.isoformat(),
            "cycle": {
                "id": str(cycle.id) if cycle else None,
                "title": cycle.title if cycle else "Chu kỳ N-Tuần",
                "duration_weeks": duration_weeks,
                "current_week": current_week,
                "status": cycle.status if cycle else "active",
                "overall_progress": round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0,
            },
            "timeline": timeline,
            "okrs": objectives,
            "tasks_summary": {
                "total": total_tasks,
                "completed": completed_tasks,
                "in_progress": in_progress_tasks,
                "pending": total_tasks - completed_tasks - in_progress_tasks,
            },
            "blockers": blockers,
            "pending_proposals_count": pending_proposals_count,
        }
