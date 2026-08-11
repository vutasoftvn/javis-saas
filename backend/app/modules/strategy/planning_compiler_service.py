import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.core.tenancy import get_cycle_scoped

from app.modules.strategy.models import (
    TwelveWeekCycle,
    WeeklyPlan,
    WeeklyCommitment,
    Milestone,
    Project,
)
from app.modules.tasks.models import Task
from app.modules.outcomes.models import Outcome

logger = logging.getLogger(__name__)


class PlanningCompilerService:
    """Planning Compiler (mCOSA V12 Spec §52 & Sprint 4).

    Biên dịch các cam kết tuần (WeeklyCommitment) và sản phẩm bàn giao của cột mốc (Milestone required_artifacts)
    thành các thực thể thực thi V10 runtime (Task & Outcome).
    Đảm bảo tính Idempotent và tuân thủ nguyên tắc: Không tạo Task/Outcome khi chu kỳ chưa được kích hoạt (Active).
    """

    def __init__(self, db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    def compile_cycle(self, cycle_id: uuid.UUID) -> Dict[str, Any]:
        cycle = get_cycle_scoped(self.db, cycle_id, self.workspace_id)

        # Enforce activation gate (Spec §11)
        if cycle.status != "active":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Không thể biên dịch chu kỳ ở trạng thái '{cycle.status}'. Chu kỳ 12 tuần phải ở trạng thái 'active' (đã được CEO phê duyệt/kích hoạt).",
            )

        # 1. Compile Weekly Commitments -> Tasks
        plans = (
            self.db.query(WeeklyPlan)
            .filter(
                WeeklyPlan.cycle_id == cycle_id,
                WeeklyPlan.workspace_id == self.workspace_id,
            )
            .all()
        )

        plan_ids = [p.id for p in plans]
        commitments = (
            self.db.query(WeeklyCommitment)
            .filter(
                WeeklyCommitment.weekly_plan_id.in_(plan_ids),
                WeeklyCommitment.workspace_id == self.workspace_id,
            )
            .all()
            if plan_ids
            else []
        )

        tasks_created = 0
        tasks_existing = 0

        for commitment in commitments:
            existing_task = (
                self.db.query(Task)
                .filter(
                    Task.weekly_commitment_id == commitment.id,
                    Task.workspace_id == self.workspace_id,
                )
                .first()
            )
            if existing_task:
                tasks_existing += 1
                continue

            # Determine execution_mode
            exec_mode = "HUMAN"
            if commitment.execution_mode == "AUTONOMOUS" or commitment.commitment_owner_type == "AI_AGENT":
                exec_mode = "AGENT"
            elif commitment.execution_mode == "AI_ASSISTED":
                exec_mode = "HYBRID"

            new_task = Task(
                id=uuid.UUID(int=generate_snowflake_id()),
                workspace_id=self.workspace_id,
                title=commitment.title,
                idempotency_key=f"cycle_compile_{commitment.id}",
                status="todo",
                priority="medium",
                weekly_commitment_id=commitment.id,
                initiative_id=commitment.initiative_id,
                execution_mode=exec_mode,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(new_task)
            tasks_created += 1

        # 2. Compile Milestones -> Skeleton Outcomes
        milestones = (
            self.db.query(Milestone)
            .filter(
                Milestone.cycle_id == cycle_id,
                Milestone.workspace_id == self.workspace_id,
            )
            .all()
        )

        outcomes_created = 0
        outcomes_existing = 0

        for ms in milestones:
            required_artifacts = ms.required_artifacts or {}
            artifact_names = []
            if isinstance(required_artifacts, list):
                artifact_names = [str(x) for x in required_artifacts]
            elif isinstance(required_artifacts, dict):
                if "artifacts" in required_artifacts and isinstance(required_artifacts["artifacts"], list):
                    artifact_names = [str(x) for x in required_artifacts["artifacts"]]
                else:
                    artifact_names = list(required_artifacts.keys())

            # If no explicit artifact list, create at least 1 outcome representing the milestone deliverable
            if not artifact_names:
                artifact_names = [f"{ms.name} Deliverable"]

            for art_name in artifact_names:
                outcome_title = f"Artifact: {art_name} [{ms.name}]"
                existing_outcome = (
                    self.db.query(Outcome)
                    .filter(
                        Outcome.workspace_id == self.workspace_id,
                        Outcome.title == outcome_title,
                    )
                    .first()
                )
                if existing_outcome:
                    outcomes_existing += 1
                    continue

                new_outcome = Outcome(
                    id=uuid.UUID(int=generate_snowflake_id()),
                    workspace_id=self.workspace_id,
                    project_id=ms.project_id,
                    title=outcome_title,
                    desired_result=f"Bàn giao sản phẩm '{art_name}' đạt tiêu chuẩn nghiệm thu của cột mốc '{ms.name}' (Tuần {ms.due_week or 'TBD'}).",
                    acceptance_criteria={"criteria": ms.acceptance_criteria} if ms.acceptance_criteria else {},
                    requested_by=self.user_id,
                    status="draft",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self.db.add(new_outcome)
                outcomes_created += 1

        self.db.commit()

        return {
            "cycle_id": str(cycle_id),
            "status": "compiled",
            "tasks_created": tasks_created,
            "tasks_existing": tasks_existing,
            "total_commitments": len(commitments),
            "outcomes_created": outcomes_created,
            "outcomes_existing": outcomes_existing,
            "total_milestones": len(milestones),
        }

    def compile_weekly_plan(self, plan_id: uuid.UUID) -> Dict[str, Any]:
        plan = (
            self.db.query(WeeklyPlan)
            .filter(
                WeeklyPlan.id == plan_id,
                WeeklyPlan.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WeeklyPlan not found")

        cycle = get_cycle_scoped(self.db, plan.cycle_id, self.workspace_id)
        if cycle.status != "active":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Không thể biên dịch tuần khi chu kỳ ở trạng thái '{cycle.status}'. Chu kỳ 12 tuần phải ở trạng thái 'active'.",
            )

        commitments = (
            self.db.query(WeeklyCommitment)
            .filter(
                WeeklyCommitment.weekly_plan_id == plan.id,
                WeeklyCommitment.workspace_id == self.workspace_id,
            )
            .all()
        )

        tasks_created = 0
        tasks_existing = 0

        for commitment in commitments:
            existing_task = (
                self.db.query(Task)
                .filter(
                    Task.weekly_commitment_id == commitment.id,
                    Task.workspace_id == self.workspace_id,
                )
                .first()
            )
            if existing_task:
                tasks_existing += 1
                continue

            exec_mode = "HUMAN"
            if commitment.execution_mode == "AUTONOMOUS" or commitment.commitment_owner_type == "AI_AGENT":
                exec_mode = "AGENT"
            elif commitment.execution_mode == "AI_ASSISTED":
                exec_mode = "HYBRID"

            new_task = Task(
                id=uuid.UUID(int=generate_snowflake_id()),
                workspace_id=self.workspace_id,
                title=commitment.title,
                idempotency_key=f"plan_compile_{commitment.id}",
                status="todo",
                priority="medium",
                weekly_commitment_id=commitment.id,
                initiative_id=commitment.initiative_id,
                execution_mode=exec_mode,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(new_task)
            tasks_created += 1

        self.db.commit()

        return {
            "plan_id": str(plan_id),
            "week_no": plan.week_no,
            "status": "compiled",
            "tasks_created": tasks_created,
            "tasks_existing": tasks_existing,
            "total_commitments": len(commitments),
        }

    def get_compilation_status(self, cycle_id: uuid.UUID) -> Dict[str, Any]:
        cycle = get_cycle_scoped(self.db, cycle_id, self.workspace_id)
        plans = (
            self.db.query(WeeklyPlan)
            .filter(
                WeeklyPlan.cycle_id == cycle_id,
                WeeklyPlan.workspace_id == self.workspace_id,
            )
            .all()
        )
        plan_ids = [p.id for p in plans]

        commitments = (
            self.db.query(WeeklyCommitment)
            .filter(
                WeeklyCommitment.weekly_plan_id.in_(plan_ids),
                WeeklyCommitment.workspace_id == self.workspace_id,
            )
            .all()
            if plan_ids
            else []
        )
        commitment_ids = [c.id for c in commitments]

        compiled_tasks_count = (
            self.db.query(Task)
            .filter(
                Task.weekly_commitment_id.in_(commitment_ids),
                Task.workspace_id == self.workspace_id,
            )
            .count()
            if commitment_ids
            else 0
        )

        milestones_count = (
            self.db.query(Milestone)
            .filter(
                Milestone.cycle_id == cycle_id,
                Milestone.workspace_id == self.workspace_id,
            )
            .count()
        )

        return {
            "cycle_id": str(cycle_id),
            "cycle_status": cycle.status,
            "is_active": cycle.status == "active",
            "total_commitments": len(commitments),
            "compiled_tasks_count": compiled_tasks_count,
            "uncompiled_commitments_count": max(0, len(commitments) - compiled_tasks_count),
            "total_milestones": milestones_count,
        }
