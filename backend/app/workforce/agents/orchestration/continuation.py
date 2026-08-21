# backend/app/workforce/agents/orchestration/continuation.py
from sqlalchemy.orm import Session

from app.founder_os.outcomes.models import OutcomeRun
from app.workforce.agents.orchestration.adk.nodes.specialist_delegation_node import interrupt_id_for_step
from app.workforce.agents.orchestration.mission_resume_service import MissionResumeJobService


async def maybe_resume_mission(
    db: Session,
    outcome_run_id: int,
    *,
    run_step_id: int,
) -> bool:
    """Enqueue 1 MissionResumeJob ngay khi 1 RunStep specialist chuyển terminal.

    Trả True khi 1 job resume thật sự được enqueue (hoặc đã tồn tại - idempotent
    theo (mission_run_id, checkpoint_key), xem Task 5/17). MissionResumeJobService
    (Task 18) + worker loop riêng (mission_resume_loop, Task 28 Step 5) đảm bảo
    đúng 1 lần gọi AdkCofounderWorkflow.resume cho mỗi checkpoint — KHÔNG còn
    chờ "tất cả step terminal" ở tầng này, JoinNode trong graph (Task 23) tự lo
    việc chờ tất cả specialist.
    """
    outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == outcome_run_id).one_or_none()
    if outcome_run is None or outcome_run.agent_run_id is None:
        return False

    workspace_id = _workspace_id_for_outcome_run(db, outcome_run)
    MissionResumeJobService.enqueue_resume(
        db,
        workspace_id=workspace_id,
        mission_run_id=outcome_run.agent_run_id,
        workflow_session_id=None,
        checkpoint_key=interrupt_id_for_step(run_step_id),
        reason="specialist_delegation_completed",
    )
    return True


def _workspace_id_for_outcome_run(db: Session, outcome_run: OutcomeRun) -> int:
    from app.founder_os.outcomes.models import Outcome

    return db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id).one().workspace_id
