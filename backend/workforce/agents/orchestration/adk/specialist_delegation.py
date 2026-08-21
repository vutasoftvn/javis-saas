# backend/app/workforce/agents/orchestration/adk/specialist_delegation.py
"""Trích từ ChiefOfStaffOrchestrator._queue_specialist_delegations — chuyển từ
"1 lần cho tất cả domains" sang "1 lần cho đúng 1 domain" vì mỗi domain giờ là 1
FunctionNode riêng trong graph (Task 16), không phải 1 vòng lặp Python."""
from sqlalchemy.orm import Session

from core.snowflake import generate_snowflake_id
from founder_os.outcomes.models import OutcomeRun, RunStep
from workforce.agents.delegation.task_board import TaskBoardService
from workforce.agents.orchestration.specialist_registry import SpecialistSpec


async def queue_specialist_delegation(
    db: Session,
    *,
    workspace_id: int,
    outcome_run: OutcomeRun,
    domain: str,
    spec: SpecialistSpec,
    runtime_name: str,
    actor_agent_key: str = "adk_cofounder_workflow",
) -> RunStep:
    existing_steps = db.query(RunStep).filter(RunStep.run_id == outcome_run.id).all()
    step = next(
        (
            s for s in existing_steps
            if isinstance(s.inputs_jsonb, dict)
            and s.inputs_jsonb.get("mission_kind") == "chief_of_staff_specialist"
            and s.inputs_jsonb.get("report_key") == domain
        ),
        None,
    )
    if step is None:
        step = RunStep(
            id=generate_snowflake_id(),
            run_id=outcome_run.id,
            type="agent",
            inputs_jsonb={
                "mission_kind": "chief_of_staff_specialist",
                "report_key": domain,
                "task": spec.task,
                "required": True,
                "failure_policy": "fail_mission",
            },
            expected_output=f"Structured {domain} specialist report",
            risk_level=spec.risk_level,
            depends_on_step_ids=[],
            status="pending",
        )
        db.add(step)
        db.flush()

    await TaskBoardService.assign_step(
        db=db,
        workspace_id=workspace_id,
        step_id=step.id,
        profile_id=spec.delegate_via_profile_id,
        runtime_name=runtime_name,
        provider_name="in_process",
        actor_agent_key=actor_agent_key,
    )
    return step
