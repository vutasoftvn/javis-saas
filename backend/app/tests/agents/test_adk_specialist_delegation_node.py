# backend/app/tests/agents/test_adk_specialist_delegation_node.py
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from google.adk.events.request_input import RequestInput
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.feature_flags import FLAG_AGENT_DELEGATION
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.platform.auth.models import User, Workspace
from app.platform.core.models import FeatureFlag
from app.workforce.agents.delegation.manager import DelegationProviderManager
from app.workforce.agents.delegation.provider import DelegationProvider
from app.workforce.agents.delegation.task_board import TaskBoardService
from app.workforce.agents.delegation.types import DelegationHandle, DelegationResult, DelegationStatus, ProviderHealth
from app.workforce.agents.orchestration.adk.nodes import specialist_delegation_node as node_module
from app.workforce.agents.orchestration.adk.nodes.specialist_delegation_node import (
    build_specialist_delegation_fn,
    build_specialist_delegation_node,
)


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
async def test_specialist_delegation_fn_yields_request_input(db_session, monkeypatch):
    manager = DelegationProviderManager()
    manager.register(HealthyProvider())
    monkeypatch.setattr(TaskBoardService, "provider_manager", manager)
    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"sdn-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"SDN {workspace_id}"))
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

    ctx = SimpleNamespace(
        state={
            "outcome_run_id": outcome_run.id,
            "workspace_id": workspace_id,
            "active_domains": ["finance"],
            "specialist_runtime_name": "mock",
        }
    )

    fn = build_specialist_delegation_fn("finance")
    items = [item async for item in fn(ctx)]

    assert len(items) == 1
    assert isinstance(items[0], RequestInput)
    step_id = ctx.state["specialist_step_ids"]["finance"]
    assert items[0].interrupt_id == f"delegation_step:{step_id}"


@pytest.mark.asyncio
async def test_specialist_delegation_fn_skips_inactive_domain():
    ctx = SimpleNamespace(
        state={
            "active_domains": ["finance"],
            "workspace_id": 123,
        }
    )
    fn = build_specialist_delegation_fn("sales")
    items = [item async for item in fn(ctx)]
    assert items == [{"skipped": True, "domain": "sales"}]


def test_build_specialist_delegation_node_shape():
    node = build_specialist_delegation_node("sales")
    assert node.name == "specialist_delegation_sales_node"
    assert node.rerun_on_resume is False
