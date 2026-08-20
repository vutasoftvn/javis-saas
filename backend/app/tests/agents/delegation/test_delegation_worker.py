from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.platform.auth.models import User, Workspace
from app.workforce.agents.delegation.manager import DelegationProviderManager
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.delegation.provider import DelegationProvider
from app.workforce.agents.delegation.types import (
    DelegationHandle,
    DelegationRequest,
    DelegationResult,
    DelegationStatus,
    ProviderHealth,
)
from app.workforce.agents.governance.approval_service import ApprovalService


@pytest.fixture
def transactional_sessions():
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


class CountingProvider(DelegationProvider):
    def __init__(self, result_status=DelegationStatus.SUCCEEDED):
        self.start_calls = 0
        self.poll_calls = 0
        self.cancel_calls = 0
        self.result_status = result_status

    @property
    def provider_name(self):
        return "counting"

    async def delegate(self, request: DelegationRequest, idempotency_key: str):
        self.start_calls += 1
        return DelegationHandle(provider_name=self.provider_name, external_id=idempotency_key)

    async def poll(self, handle: DelegationHandle):
        self.poll_calls += 1
        return DelegationResult(
            status=self.result_status,
            structured_result={"source": "poll"},
        )

    async def cancel(self, handle: DelegationHandle):
        self.cancel_calls += 1
        return True

    async def health(self):
        return ProviderHealth(provider_name=self.provider_name, available=True)


def _job(db, *, status="queued", handle=None):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db.add(User(id=user_id, email=f"worker-{user_id}@example.invalid"))
    db.add(Workspace(id=workspace_id, name=f"Worker {workspace_id}"))
    db.flush()
    outcome = Outcome(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        function="marketing",
        title="Worker mission",
        desired_result="Process durable delegation",
        requested_by=user_id,
        status="running",
    )
    db.add(outcome)
    db.flush()
    outcome_run = OutcomeRun(
        id=generate_snowflake_id(),
        outcome_id=outcome.id,
        status="running",
        verification_status="UNKNOWN",
    )
    db.add(outcome_run)
    db.flush()
    root = AgentRun(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        company_id=workspace_id,
        user_id=user_id,
        outcome_run_id=outcome_run.id,
        agent_key="chief_of_staff",
        runtime="mock",
        status="running",
        permission_profile="l3_execute",
        budget_jsonb={
            "max_steps": 10,
            "max_tool_calls": 10,
            "max_api_cost_usd": 5,
            "max_wall_time_seconds": 300,
        },
        started_at=datetime.now(timezone.utc),
    )
    db.add(root)
    db.flush()
    outcome_run.agent_run_id = root.id
    step = RunStep(
        id=generate_snowflake_id(),
        run_id=outcome_run.id,
        type="agent",
        inputs_jsonb={"task": "Analyze acquisition", "user_id": user_id},
        risk_level="R0",
        status="running" if status == "running" else "pending",
        assigned_agent_profile_id="marketing",
        assigned_runtime="mock",
    )
    db.add(step)
    db.flush()
    job = DelegationJob(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        run_step_id=step.id,
        root_agent_run_id=root.id,
        parent_agent_run_id=root.id,
        attempt_no=1,
        provider_kind="test",
        provider_name="counting",
        profile_id="marketing",
        runtime_name="mock",
        status=status,
        provider_handle_jsonb=handle,
        idempotency_key=f"worker:{step.id}:1",
        available_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
    )
    db.add(job)
    db.commit()
    return job


def test_claim_due_job_sets_unique_lease(transactional_sessions):
    from app.workforce.agents.delegation.worker import claim_due_job

    db, _factory = transactional_sessions
    job = _job(db)

    assert claim_due_job(db, "worker-a", datetime.now(timezone.utc)) == job.id
    db.refresh(job)
    assert job.status == "claimed"
    assert job.claimed_by == "worker-a"
    assert job.lease_token
    assert job.lease_expires_at > datetime.now(timezone.utc)


def test_lease_token_prevents_stale_worker_completion(transactional_sessions):
    from app.workforce.agents.delegation.worker import LeaseLost, persist_provider_result

    db, _factory = transactional_sessions
    job = _job(db)
    from app.workforce.agents.delegation.worker import claim_due_job

    claim_due_job(db, "worker-a", datetime.now(timezone.utc))

    with pytest.raises(LeaseLost):
        persist_provider_result(
            db,
            job.id,
            "stale-token",
            DelegationResult(
                status=DelegationStatus.SUCCEEDED,
                structured_result={"unsafe": True},
            ),
        )


@pytest.mark.asyncio
async def test_expired_job_with_handle_is_polled_not_started_again(
    transactional_sessions, monkeypatch
):
    from app.workforce.agents.delegation import worker

    db, factory = transactional_sessions
    handle = DelegationHandle(
        provider_name="counting",
        external_id="native-1",
    )
    job = _job(db, status="running", handle=handle.model_dump(mode="json"))
    job.claimed_by = "dead-worker"
    job.lease_token = "dead-token"
    job.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    manager = DelegationProviderManager()
    provider = CountingProvider()
    manager.register(provider)
    monkeypatch.setattr(worker, "delegation_provider_manager", manager)

    assert worker.reconcile_expired_jobs(db, datetime.now(timezone.utc)) == 1
    assert worker.claim_due_job(db, "worker-b", datetime.now(timezone.utc)) == job.id
    await worker.process_delegation_job(job.id, "worker-b", session_factory=factory)

    assert provider.start_calls == 0
    assert provider.poll_calls == 1
    db.expire_all()
    assert db.get(DelegationJob, job.id).status == "succeeded"


def test_reconcile_requeues_pre_handle_but_never_terminal_job(transactional_sessions):
    from app.workforce.agents.delegation.worker import reconcile_expired_jobs

    db, _factory = transactional_sessions
    expired = _job(db, status="claimed")
    expired.claimed_by = "dead-worker"
    expired.lease_token = "dead-token"
    expired.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    terminal = _job(db, status="succeeded")
    terminal.claimed_by = "old-worker"
    terminal.lease_token = "terminal-token"
    terminal.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    assert reconcile_expired_jobs(db, datetime.now(timezone.utc)) == 1
    db.refresh(expired)
    db.refresh(terminal)
    assert expired.status == "queued"
    assert expired.lease_token is None
    assert terminal.status == "succeeded"
    assert terminal.lease_token == "terminal-token"


@pytest.mark.asyncio
async def test_fresh_claim_starts_once_persists_handle_and_completes(
    transactional_sessions, monkeypatch
):
    from app.workforce.agents.delegation import worker

    db, factory = transactional_sessions
    job = _job(db)
    manager = DelegationProviderManager()
    provider = CountingProvider()
    manager.register(provider)
    monkeypatch.setattr(worker, "delegation_provider_manager", manager)

    assert worker.claim_due_job(db, "worker-a", datetime.now(timezone.utc)) == job.id
    await worker.process_delegation_job(job.id, "worker-a", session_factory=factory)

    db.expire_all()
    completed = db.get(DelegationJob, job.id)
    assert provider.start_calls == 1
    assert provider.poll_calls == 1
    assert completed.status == "succeeded"
    assert completed.provider_handle_jsonb["external_id"] == completed.idempotency_key
    assert completed.child_agent_run_id is not None
    assert completed.lease_token is None


def test_exact_approved_delegation_is_promoted_and_claimed(transactional_sessions):
    from app.workforce.agents.delegation.worker import claim_due_job

    db, _factory = transactional_sessions
    job = _job(db, status="waiting_approval")
    job.available_at = datetime(1900, 1, 1, tzinfo=timezone.utc)
    step = db.get(RunStep, job.run_step_id)
    step.status = "waiting_approval"
    approval = ApprovalService.create_approval(
        db,
        workspace_id=job.workspace_id,
        agent_key="chief_of_staff",
        action_type="delegation.assign",
        tool_name=f"delegation.{job.provider_name}",
        run_id=job.parent_agent_run_id,
        capability="agent.delegate",
        resource_type="run_step",
        resource_id=str(step.id),
        idempotency_key=job.idempotency_key,
        commit=False,
    )
    approval.status = "approved"
    db.commit()

    assert claim_due_job(db, "worker-a", datetime.now(timezone.utc)) == job.id
    db.refresh(job)
    db.refresh(step)
    assert job.status == "claimed"
    assert step.status == "pending"
