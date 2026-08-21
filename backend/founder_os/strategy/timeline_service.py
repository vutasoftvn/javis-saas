import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from core.tenancy import get_cycle_scoped
from founder_os.strategy.models import (
    TwelveWeekCycle,
    WeeklyPlan,
    WeeklyCommitment,
    Project,
)
from founder_os.tasks.models import Task
from founder_os.outcomes.models import Outcome

logger = logging.getLogger(__name__)


class StrategicTimelineService:
    """Service to aggregate, build and serialize the Interactive Strategic Timeline for Hologram Hub & Dashboard."""

    def __init__(self, db: Session, workspace_id: int, user_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    def get_cycle_timeline(self, cycle_id: int) -> Dict[str, Any]:
        """Aggregate cycle, weekly plans, commitments, tasks & outcomes into a structured Timeline Card."""
        cycle = get_cycle_scoped(self.db, cycle_id, self.workspace_id)

        # 1. Resolve project info
        project = None
        if cycle.project_id:
            project = (
                self.db.query(Project)
                .filter(Project.id == cycle.project_id, Project.workspace_id == self.workspace_id)
                .first()
            )

        # 2. Get WeeklyPlans
        plans = (
            self.db.query(WeeklyPlan)
            .filter(WeeklyPlan.cycle_id == cycle_id, WeeklyPlan.workspace_id == self.workspace_id)
            .order_by(WeeklyPlan.week_no.asc())
            .all()
        )

        plan_ids = [p.id for p in plans]
        commitments = (
            self.db.query(WeeklyCommitment)
            .filter(WeeklyCommitment.weekly_plan_id.in_(plan_ids), WeeklyCommitment.workspace_id == self.workspace_id)
            .all()
            if plan_ids
            else []
        )

        commitments_by_plan: Dict[int, List[WeeklyCommitment]] = {}
        for c in commitments:
            commitments_by_plan.setdefault(c.weekly_plan_id, []).append(c)

        commitment_ids = [c.id for c in commitments]
        tasks = (
            self.db.query(Task)
            .filter(Task.weekly_commitment_id.in_(commitment_ids), Task.workspace_id == self.workspace_id)
            .all()
            if commitment_ids
            else []
        )

        task_ids = [t.id for t in tasks]
        outcomes = (
            self.db.query(Outcome)
            .filter(Outcome.task_id.in_(task_ids), Outcome.workspace_id == self.workspace_id)
            .all()
            if task_ids
            else []
        )

        tasks_by_commitment: Dict[int, List[Task]] = {}
        for t in tasks:
            if t.weekly_commitment_id:
                tasks_by_commitment.setdefault(t.weekly_commitment_id, []).append(t)

        outcomes_by_task: Dict[int, List[Outcome]] = {}
        for o in outcomes:
            if o.task_id:
                outcomes_by_task.setdefault(o.task_id, []).append(o)

        # 3. Build Timeline Steps for each week or grouped phases
        timeline_steps = []
        total_weeks = cycle.duration_weeks or len(plans) or 13

        for plan in plans:
            plan_commitments = commitments_by_plan.get(plan.id, [])
            plan_tasks: List[Task] = []
            for c in plan_commitments:
                plan_tasks.extend(tasks_by_commitment.get(c.id, []))

            plan_outcomes: List[Outcome] = []
            for t in plan_tasks:
                plan_outcomes.extend(outcomes_by_task.get(t.id, []))

            # Active AI functions involved in this week
            functions = list({t.function for t in plan_tasks if t.function})
            if not functions:
                functions = ["CHIEF_OF_STAFF"]

            # Compute progress
            total_tasks = len(plan_tasks)
            done_tasks = sum(1 for t in plan_tasks if t.status in ("completed", "done"))
            total_outcomes = len(plan_outcomes)
            done_outcomes = sum(1 for o in plan_outcomes if o.status in ("approved", "delivered", "done"))

            if total_tasks == 0 and total_outcomes == 0:
                step_status = "pending"
                progress_pct = 0.0
            elif (total_tasks > 0 and done_tasks == total_tasks) and (total_outcomes == 0 or done_outcomes == total_outcomes):
                step_status = "completed"
                progress_pct = 100.0
            elif done_tasks > 0 or done_outcomes > 0 or any(t.status == "in_progress" for t in plan_tasks):
                step_status = "in_progress"
                task_ratio = done_tasks / max(total_tasks, 1)
                outcome_ratio = done_outcomes / max(total_outcomes, 1)
                progress_pct = round(((task_ratio + outcome_ratio) / 2) * 100.0, 1)
            else:
                step_status = "pending"
                progress_pct = 0.0

            # Is this the final transition week?
            is_final_week = plan.week_no == total_weeks
            default_title = "Tổng kết, Đánh giá & Transition" if is_final_week else f"Thực thi Trọng tâm Tuần {plan.week_no}"

            timeline_steps.append({
                "step_no": plan.week_no,
                "week_no": plan.week_no,
                "week_range": f"Tuần {plan.week_no}",
                "title": plan.focus or plan.mission or default_title,
                "mission": plan.mission,
                "owner_functions": functions,
                "status": step_status,
                "progress_percent": progress_pct,
                "tasks_count": total_tasks,
                "tasks_done": done_tasks,
                "outcomes_count": total_outcomes,
                "outcomes_done": done_outcomes,
                "is_transition_week": is_final_week,
            })

        return {
            "type": "STRATEGIC_TIMELINE_CARD",
            "data": {
                "cycle_id": str(cycle.id),
                "project_id": str(project.id) if project else None,
                "project_name": project.title if project else (cycle.theme or "Chiến lược Không tên"),
                "theme": cycle.theme,
                "total_weeks": total_weeks,
                "current_week": min(1, total_weeks),
                "status": cycle.status,
                "commitment_level": cycle.commitment_level,
                "timeline_steps": timeline_steps,
            }
        }
