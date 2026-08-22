# backend/app/tests/agents/test_adk_specialist_delegation.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from core.feature_flags import FLAG_AGENT_DELEGATION
from core.snowflake import generate_snowflake_id
from db.session import engine
from founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from platform_core.auth.models import User, Workspace
from platform_core.core.models import FeatureFlag
from workforce.agents.delegation.manager import DelegationProviderManager
from workforce.agents.delegation.models import DelegationJob
from workforce.agents.delegation.provider import DelegationProvider
from workforce.agents.delegation.task_board import TaskBoardService
from workforce.agents.delegation.types import DelegationHandle, DelegationResult, DelegationStatus, ProviderHealth
from workforce.agents.orchestration.adk.specialist_delegation import queue_specialist_delegation
from workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY


class HealthyProvider(DelegationProvider):
    @property
    def provider_name(self) -> str:
        return "in_process"

    async def delegate(self, request, idempotency_key):
        return DelegationHandle(provider_name="in_process", external_id=idempotency_key)

    async def poll(self, handle):
        return DelegationResult(status=DelegationStatus.RUNNING)

    async def cancel(self, handle):
        return True

    async def health(self):
        return ProviderHealth(provider_name="in_process", available=True)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.mark.asyncio
async def test_queue_specialist_delegation_creates_run_step_and_delegation_job(db_session, monkeypatch):
    manager = DelegationProviderManager()
    manager.register(HealthyProvider())
    monkeypatch.setattr(TaskBoardService, "provider_manager", manager)

    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"sd-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"SD {workspace_id}"))
    db_session.add(FeatureFlag(id=generate_snowflake_id(), workspace_id=workspace_id, key=FLAG_AGENT_DELEGATION, enabled=True))
    db_session.flush()

    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission", desired_result="goal", requested_by=user_id, status="running",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(id=generate_snowflake_id(), outcome_id=outcome.id, status="running", verification_status="UNKNOWN")
    db_session.add(outcome_run)
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="adk", status="running", started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()
    outcome_run.agent_run_id = mission_run.id
    db_session.commit()

    spec = SPECIALIST_REGISTRY["finance"]
    step = await queue_specialist_delegation(
        db_session, workspace_id=workspace_id, outcome_run=outcome_run, domain="finance",
        spec=spec, runtime_name="mock",
    )

    assert step.inputs_jsonb["mission_kind"] == "chief_of_staff_specialist"
    assert step.inputs_jsonb["report_key"] == "finance"
    jobs = db_session.query(DelegationJob).filter(DelegationJob.run_step_id == step.id).all()
    assert len(jobs) == 1

    # Idempotent: gọi lại lần 2 cho cùng domain không tạo thêm RunStep mới
    step2 = await queue_specialist_delegation(
        db_session, workspace_id=workspace_id, outcome_run=outcome_run, domain="finance",
        spec=spec, runtime_name="mock",
    )
    assert step2.id == step.id
    all_steps = db_session.query(RunStep).filter(RunStep.run_id == outcome_run.id).all()
    assert len(all_steps) == 1
