from sqlalchemy.orm import Session

from app.founder_os.outcomes.models import OutcomeRun, RunStep
from app.workforce.agents.runtime.base import AgentRuntime


async def maybe_resume_mission(
    db: Session,
    outcome_run_id: int,
    runtime: AgentRuntime | None = None,
) -> bool:
    """Resume a CoS mission only when its complete required step set is terminal.

    Returns True when this call observed a resumable mission.  The orchestrator's
    advisory lock and materialized completion event provide cross-worker exactly-
    once synthesis; callers may therefore invoke this after every terminal job.
    """
    outcome_run = (
        db.query(OutcomeRun).filter(OutcomeRun.id == outcome_run_id).one_or_none()
    )
    if outcome_run is None or outcome_run.agent_run_id is None:
        return False
    steps = db.query(RunStep).filter(RunStep.run_id == outcome_run_id).all()
    delegation_steps = [
        step
        for step in steps
        if isinstance(step.inputs_jsonb, dict)
        and step.inputs_jsonb.get("mission_kind") == "chief_of_staff_specialist"
    ]
    if not delegation_steps or any(
        step.status not in {"completed", "failed", "cancelled", "skipped"}
        for step in delegation_steps
    ):
        return False

    from app.workforce.agents.orchestration.chief_of_staff import (
        ChiefOfStaffOrchestrator,
    )

    await ChiefOfStaffOrchestrator.resume_after_delegation(
        db,
        outcome_run.agent_run_id,
        runtime=runtime,
    )
    return True
