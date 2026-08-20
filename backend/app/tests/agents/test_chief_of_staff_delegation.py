from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.feature_flags import (
    FLAG_AGENT_DELEGATION,
    FLAG_AGENT_DELEGATION_CHIEF_OF_STAFF,
)
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import RunStep
from app.platform.auth.models import User, Workspace
from app.platform.core.models import FeatureFlag
from app.workforce.agents.delegation.manager import DelegationProviderManager
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.delegation.provider import DelegationProvider
from app.workforce.agents.delegation.types import ProviderHealth
from app.workforce.agents.orchestration.chief_of_staff import (
    ChiefOfStaffOrchestrator,
    SPECIALIST_REGISTRY,
)
from app.workforce.agents.governance.models import AgentEventRecord
from app.workforce.agents.runtime.adapters.mock import MockRuntime


class HealthyInProcessProvider(DelegationProvider):
    @property
    def provider_name(self):
        return "in_process"

    async def delegate(self, request, idempotency_key):  # pragma: no cover - worker contract
        raise AssertionError("queue-path test must not execute provider I/O")

    async def poll(self, handle):  # pragma: no cover - worker contract
        raise AssertionError("queue-path test must not poll provider I/O")

    async def cancel(self, handle):
        return True

    async def health(self):
        return ProviderHealth(provider_name=self.provider_name, available=True)


@pytest.fixture
def chief_delegation_db(monkeypatch):
    from app.workforce.agents.delegation.task_board import TaskBoardService

    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db.add(User(id=user_id, email=f"chief-delegation-{user_id}@example.invalid"))
    db.add(Workspace(id=workspace_id, name=f"Chief Delegation {workspace_id}"))
    for key in (FLAG_AGENT_DELEGATION, FLAG_AGENT_DELEGATION_CHIEF_OF_STAFF):
        db.add(
            FeatureFlag(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                key=key,
                enabled=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
    db.commit()
    manager = DelegationProviderManager()
    manager.register(HealthyInProcessProvider())
    monkeypatch.setattr(TaskBoardService, "provider_manager", manager)
    try:
        yield db, workspace_id, user_id
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.mark.asyncio
async def test_chief_of_staff_queues_governed_specialists_and_resumes_once(
    chief_delegation_db,
):
    db, workspace_id, user_id = chief_delegation_db
    assert SPECIALIST_REGISTRY["sales"].delegate_via_profile_id == "sales"

    queued = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        goal="Review the operating position",
        runtime=MockRuntime(),
    )

    assert queued.status == "delegating"
    jobs = db.query(DelegationJob).filter(DelegationJob.workspace_id == workspace_id).all()
    assert len(jobs) == 2
    steps = db.query(RunStep).filter(
        RunStep.id.in_([job.run_step_id for job in jobs])
    ).all()
    assert {step.inputs_jsonb["report_key"] for step in steps} == {"sales", "finance"}

    for step in steps:
        step.status = "completed"
        if step.inputs_jsonb["report_key"] == "sales":
            step.result_jsonb = {"status": "success", "metrics": {"qualified_leads": 0}}
        else:
            step.result_jsonb = {"status": "success", "runway_months": 12}
    db.commit()

    first = await ChiefOfStaffOrchestrator.resume_after_delegation(
        db, int(queued.mission_id), runtime=MockRuntime()
    )
    second = await ChiefOfStaffOrchestrator.resume_after_delegation(
        db, int(queued.mission_id), runtime=MockRuntime()
    )

    assert second.model_dump() == first.model_dump()
    synthesis_events = db.query(AgentEventRecord).filter_by(
        run_id=int(queued.mission_id), event_type="synthesis_completed"
    ).all()
    assert len(synthesis_events) == 1
