from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.integrations.devices.models import Device, DeveloperJob
from app.integrations.devices.service import (
    claim_job,
    renew_job_lease,
    submit_job_results,
)
from app.platform.auth.models import User, Workspace
from app.workforce.agents.execution.long_running.types import (
    WorkContext,
    WorkRequest,
    WorkState,
)


@pytest.fixture
def device_db():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db, factory
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def _identity(db):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db.add(User(id=user_id, email=f"device-executor-{user_id}@example.invalid"))
    db.add(Workspace(id=workspace_id, name=f"Device executor {workspace_id}"))
    db.flush()
    run = AgentRun(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        company_id=workspace_id,
        user_id=user_id,
        agent_key="chief_of_staff",
        runtime="mock",
        status="running",
    )
    db.add(run)
    db.flush()
    return user_id, workspace_id, run


def test_device_without_codex_capability_cannot_claim_codex_job(device_db):
    db, _factory = device_db
    _user_id, workspace_id, _run = _identity(db)
    device = Device(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        name="Python only",
        platform="linux",
        capabilities=["python"],
        trust_level="standard",
        status="online",
    )
    job = DeveloperJob(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        title="Codex task",
        executor_kind="codex",
        required_capabilities=["codex", "git"],
        status="QUEUED",
    )
    db.add_all([device, job])
    db.commit()

    with pytest.raises(PermissionError, match="capabilities"):
        claim_job(db, device.id, job.id, workspace_id, "worker-1")


def test_expired_lease_cannot_submit_and_active_lease_can_renew(device_db):
    db, _factory = device_db
    _user_id, workspace_id, _run = _identity(db)
    device = Device(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        name="Codex node",
        platform="macos",
        capabilities=["codex", "git"],
        trust_level="standard",
        status="online",
    )
    job = DeveloperJob(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        title="Codex task",
        executor_kind="codex",
        required_capabilities=["codex", "git"],
        status="QUEUED",
    )
    db.add_all([device, job])
    db.commit()

    claimed, lease = claim_job(db, device.id, job.id, workspace_id, "worker-1")
    raw_token = lease.lease_token
    renewed = renew_job_lease(
        db, claimed.id, workspace_id, device.id, raw_token, lease_duration_minutes=20
    )
    assert renewed.renewed_at is not None
    lease.lease_until = datetime.utcnow() - timedelta(seconds=1)
    db.commit()

    with pytest.raises(PermissionError, match="lease"):
        submit_job_results(
            db,
            claimed.id,
            workspace_id,
            device.id,
            lease_token=raw_token,
            status="SUCCEEDED",
        )


@pytest.mark.asyncio
async def test_codex_provider_start_is_idempotent_and_poll_maps_job(device_db):
    from app.workforce.agents.execution.long_running.providers.codex_device import (
        CodexDeviceExecutor,
    )

    db, factory = device_db
    user_id, workspace_id, run = _identity(db)
    outcome = Outcome(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        function="tech",
        title="Device provider",
        desired_result="Fix tests",
        requested_by=user_id,
        status="running",
    )
    db.add(outcome)
    db.flush()
    outcome_run = OutcomeRun(
        id=generate_snowflake_id(),
        outcome_id=outcome.id,
        agent_run_id=run.id,
        status="running",
        verification_status="UNKNOWN",
    )
    db.add(outcome_run)
    db.flush()
    step = RunStep(
        id=generate_snowflake_id(),
        run_id=outcome_run.id,
        type="agent",
        status="running",
    )
    db.add(step)
    db.flush()
    provider = CodexDeviceExecutor(session_factory=factory)
    context = WorkContext(
        workspace_id=workspace_id,
        outcome_run_id=outcome_run.id,
        run_step_id=step.id,
        root_agent_run_id=run.id,
        parent_agent_run_id=run.id,
        profile_id="tech",
    )
    request = WorkRequest(task="Fix the tests", permission_profile="l3_execute")

    first = await provider.start(context, request, "same-key")
    second = await provider.start(context, request, "same-key")
    assert first.external_id == second.external_id

    job = db.get(DeveloperJob, int(first.external_id))
    job.status = "SUCCEEDED"
    job.result_jsonb = {"summary": "fixed"}
    db.commit()
    status = await provider.poll(context, first)
    assert status.state == WorkState.SUCCEEDED
    assert status.structured_result == {"summary": "fixed"}
