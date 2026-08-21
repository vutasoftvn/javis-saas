from core.snowflake import generate_snowflake_id
from core.feature_flags import (
    FLAG_AGENT_DELEGATION,
    FLAG_AGENT_DELEGATION_CHIEF_OF_STAFF,
    FLAG_AGENT_DELEGATION_DEVICE_EXECUTORS,
    FLAG_AGENT_DELEGATION_N8N,
    FLAG_AGENT_DELEGATION_SANDBOX,
)
from db.session import SessionLocal
from founder_os.outcomes.models import RunEvent
from workforce.agents.delegation.models import DelegationJob
from workforce.agents.delegation.task_board import TaskBoardService
from workforce.agents.delegation.types import DelegationResult, DelegationStatus
from platform_core.core.models import FeatureFlag


def test_all_phase_c_rollout_flags_are_explicitly_disabled_at_migration_head():
    db = SessionLocal()
    try:
        keys = {
            FLAG_AGENT_DELEGATION,
            FLAG_AGENT_DELEGATION_CHIEF_OF_STAFF,
            FLAG_AGENT_DELEGATION_DEVICE_EXECUTORS,
            FLAG_AGENT_DELEGATION_N8N,
            FLAG_AGENT_DELEGATION_SANDBOX,
        }
        flags = db.query(FeatureFlag).filter(
            FeatureFlag.workspace_id.is_(None),
            FeatureFlag.key.in_(keys),
        ).all()
        assert {flag.key for flag in flags} == keys
        assert all(flag.enabled is False for flag in flags)
    finally:
        db.close()


def test_terminal_result_updates_job_step_event_and_report_atomically(
    transactional_sessions,
):
    db, _factory, workspace_id, parent, step = transactional_sessions
    step.status = "running"
    step.assigned_agent_profile_id = "marketing"
    step.assigned_runtime = "mock"
    job = DelegationJob(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        run_step_id=step.id,
        root_agent_run_id=parent.id,
        parent_agent_run_id=parent.id,
        attempt_no=1,
        provider_kind="agent_runtime",
        provider_name="in_process",
        profile_id="marketing",
        runtime_name="mock",
        status="running",
        idempotency_key=f"e2e:{step.id}:1",
    )
    db.add(job)
    db.commit()

    TaskBoardService.complete_job(
        db,
        workspace_id,
        job.id,
        DelegationResult(
            status=DelegationStatus.SUCCEEDED,
            structured_result={"cac": 40, "conversion_rate": 0.04},
        ),
    )

    db.refresh(step)
    db.refresh(job)
    event = db.query(RunEvent).filter(
        RunEvent.run_id == step.run_id,
        RunEvent.event_type == "step.delegation_succeeded",
    ).one()
    assert job.status == "succeeded"
    assert step.status == "completed"
    assert event.payload_jsonb["delegation_job_id"] == str(job.id)
    assert TaskBoardService.report_result(db, workspace_id, step.run_id) == {
        "marketing": {"cac": 40, "conversion_rate": 0.04}
    }
