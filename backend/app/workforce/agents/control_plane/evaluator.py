from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.workforce.agents.governance.models import AgentEventRecord
from app.workforce.agents.control_plane.models import AgentPlan, AgentPlanStep


class StepEvaluationResult(BaseModel):
    step_id: str
    status: str  # completed, waiting_approval, failed, skipped
    success: bool
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    lessons: list[str] = Field(default_factory=list)


class PlanEvaluationResult(BaseModel):
    plan_id: str
    overall_status: str  # in_progress, waiting_approval, completed, failed
    completed_steps: int
    total_steps: int
    pending_approvals: list[str] = Field(default_factory=list)
    next_recommended_actions: list[str] = Field(default_factory=list)


class PlanEvaluator:
    """Evaluates the execution state of PlanSteps and overall AgentPlan progress."""

    @classmethod
    def record_step_event(
        cls,
        db: Session,
        plan: AgentPlan,
        step: AgentPlanStep,
        event_type: str,
        payload: dict[str, Any],
        run_id: Optional[int] = None,
    ) -> None:
        event = AgentEventRecord(
            id=generate_snowflake_id(),
            run_id=run_id,
            plan_id=plan.id,
            step_id=step.id,
            company_id=plan.company_id,
            actor_type="domain_agent",
            actor_id=f"{step.domain}_{step.capability}",
            tool_id=step.tool_id,
            status=step.status,
            sequence=step.sequence_order,
            agent_key=f"{step.domain}_{step.capability}",
            event_type=event_type,
            event_time=datetime.now(timezone.utc),
            payload_jsonb={
                "goal_id": str(plan.goal_id),
                "plan_id": str(plan.id),
                "step_id": str(step.id),
                "domain": step.domain,
                "capability": step.capability,
                "tool_id": step.tool_id,
                "policy_level": step.policy_level,
                **payload,
            },
        )
        db.add(event)
        db.commit()

    @classmethod
    def evaluate_plan(cls, db: Session, plan_id: int) -> PlanEvaluationResult:
        plan = db.query(AgentPlan).filter(AgentPlan.id == plan_id).first()
        if not plan:
            return PlanEvaluationResult(
                plan_id=str(plan_id),
                overall_status="failed",
                completed_steps=0,
                total_steps=0,
                next_recommended_actions=["Plan not found"],
            )

        steps = plan.steps
        total = len(steps)
        completed = sum(1 for s in steps if s.status == "completed")
        waiting = [str(s.id) for s in steps if s.status == "waiting_approval"]
        failed = [str(s.id) for s in steps if s.status == "failed"]

        if failed:
            status = "failed"
        elif waiting:
            status = "waiting_approval"
        elif completed == total and total > 0:
            status = "completed"
        else:
            status = "in_progress"

        recommendations = []
        if status == "waiting_approval":
            recommendations.append("Review and approve pending L3A action in Approval Inbox.")
        elif status == "completed":
            recommendations.append("Plan achieved successfully. Review outcome metrics and archive goal.")
        elif status == "in_progress":
            recommendations.append("Execute next sequential step in plan.")

        return PlanEvaluationResult(
            plan_id=str(plan_id),
            overall_status=status,
            completed_steps=completed,
            total_steps=total,
            pending_approvals=waiting,
            next_recommended_actions=recommendations,
        )
