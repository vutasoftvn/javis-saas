import pytest

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import RunStep
from app.platform.auth.models import Workspace
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.delegation.task_board import TaskBoardError, TaskBoardService
from app.workforce.agents.delegation.types import DelegationResult, DelegationStatus


def test_cross_workspace_child_run_is_rejected(transactional_sessions):
    db, _factory, workspace_a, parent, step = transactional_sessions
    workspace_b = generate_snowflake_id()
    db.add(Workspace(id=workspace_b, name="Foreign child workspace"))
    db.flush()
    foreign_child = AgentRun(
        id=generate_snowflake_id(),
        workspace_id=workspace_b,
        company_id=workspace_b,
        user_id=parent.user_id,
        parent_run_id=parent.id,
        agent_key="marketing",
        runtime="mock",
        status="running",
    )
    db.add(foreign_child)
    step.status = "running"
    job = DelegationJob(
        id=generate_snowflake_id(),
        workspace_id=workspace_a,
        run_step_id=step.id,
        root_agent_run_id=parent.id,
        parent_agent_run_id=parent.id,
        child_agent_run_id=foreign_child.id,
        attempt_no=1,
        provider_kind="agent_runtime",
        provider_name="in_process",
        profile_id="marketing",
        runtime_name="mock",
        status="running",
        idempotency_key=f"tenant:{step.id}:1",
    )
    db.add(job)
    db.commit()

    with pytest.raises(TaskBoardError, match="cross-workspace"):
        TaskBoardService.complete_job(
            db,
            workspace_a,
            job.id,
            DelegationResult(status=DelegationStatus.SUCCEEDED),
        )

    assert db.get(RunStep, step.id).status == "running"
    assert db.get(DelegationJob, job.id).status == "running"
