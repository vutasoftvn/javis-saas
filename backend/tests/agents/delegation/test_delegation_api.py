from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from core.auth import get_current_workspace_member
from core.feature_flags import FLAG_AGENT_DELEGATION
from core.snowflake import generate_snowflake_id
from db.session import engine, get_db
from founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from main import app
from platform_core.auth.models import User, Workspace, WorkspaceMember
from platform_core.core.models import FeatureFlag
from workforce.agents.delegation.models import DelegationJob


@pytest.fixture
def delegation_api_state():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    user_id = generate_snowflake_id()
    workspace_a = generate_snowflake_id()
    workspace_b = generate_snowflake_id()
    db.add(User(id=user_id, email=f"delegation-api-{user_id}@example.invalid"))
    db.add_all(
        [
            Workspace(id=workspace_a, name="Delegation API A"),
            Workspace(id=workspace_b, name="Delegation API B"),
        ]
    )
    db.flush()
    db.add(
        FeatureFlag(
            id=generate_snowflake_id(),
            workspace_id=workspace_a,
            key=FLAG_AGENT_DELEGATION,
            enabled=True,
        )
    )

    def create_job(workspace_id: int, status: str) -> DelegationJob:
        outcome = Outcome(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            function="test",
            title="Delegation API",
            desired_result="Test operations",
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
            started_at=datetime.now(timezone.utc),
        )
        db.add(root)
        db.flush()
        outcome_run.agent_run_id = root.id
        step = RunStep(
            id=generate_snowflake_id(),
            run_id=outcome_run.id,
            type="agent",
            inputs_jsonb={"task": "Inspect operations"},
            risk_level="R0",
            status="failed" if status == "failed" else "running",
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
            provider_kind="agent_runtime",
            provider_name="in_process",
            profile_id="marketing",
            runtime_name="mock",
            status=status,
            idempotency_key=f"delegation:{step.id}:attempt:1",
        )
        db.add(job)
        db.flush()
        return job

    job_a = create_job(workspace_a, "failed")
    job_b = create_job(workspace_b, "running")
    db.commit()
    member_a = WorkspaceMember(
        id=generate_snowflake_id(), workspace_id=workspace_a, user_id=user_id, role="admin"
    )
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_workspace_member] = lambda: member_a
    try:
        yield TestClient(app), db, job_a, job_b
    finally:
        app.dependency_overrides.clear()
        db.close()
        transaction.rollback()
        connection.close()


def test_delegation_api_is_workspace_scoped_and_retry_is_append_only(
    delegation_api_state,
):
    client, db, job_a, job_b = delegation_api_state

    own = client.get(f"/api/v1/agents/delegations/{job_a.id}")
    foreign = client.get(f"/api/v1/agents/delegations/{job_b.id}")
    retried = client.post(f"/api/v1/agents/delegations/{job_a.id}/retry")
    replayed_retry = client.post(f"/api/v1/agents/delegations/{job_a.id}/retry")

    assert own.status_code == 200
    assert foreign.status_code == 404
    assert retried.status_code == 201
    assert replayed_retry.status_code == 201
    assert replayed_retry.json()["id"] == retried.json()["id"]
    new_job = db.query(DelegationJob).filter(
        DelegationJob.run_step_id == job_a.run_step_id,
        DelegationJob.attempt_no == 2,
    ).one()
    assert new_job.id != job_a.id
    assert new_job.idempotency_key.endswith(":attempt:2")
    assert job_a.status == "failed"

    from workforce.agents.delegation.metrics import delegation_metrics_snapshot

    metrics = delegation_metrics_snapshot(db)
    assert metrics["retry_attempts"] == 1
    assert metrics["dead_letters"] == 1
    assert "oldest_queue_age_seconds" in metrics
