from datetime import datetime, timezone

import pytest

from agent_runtime.sessions.models import AgentRun
from app.core.feature_flags import FLAG_AGENT_DELEGATION
from app.core.snowflake import generate_snowflake_id
from app.db.session import SessionLocal
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunEvent, RunStep
from app.platform.auth.models import User, Workspace
from app.platform.core.models import FeatureFlag
from app.workforce.agents.delegation.manager import DelegationProviderManager
from app.workforce.agents.delegation.provider import DelegationProvider
from app.workforce.agents.delegation.types import (
    DelegationHandle,
    DelegationRequest,
    DelegationResult,
    DelegationStatus,
    ProviderHealth,
)


class HealthyProvider(DelegationProvider):
    def __init__(self, name: str = "in_process") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    async def delegate(self, request: DelegationRequest, idempotency_key: str):
        return DelegationHandle(provider_name=self._name, external_id=idempotency_key)

    async def poll(self, handle: DelegationHandle):
        return DelegationResult(status=DelegationStatus.RUNNING)

    async def cancel(self, handle: DelegationHandle):
        return True

    async def health(self):
        return ProviderHealth(provider_name=self._name, available=True)


def _state(db, *, risk_level="R0", depends_on=None, flag_enabled=True):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db.add(User(id=user_id, email=f"board-{user_id}@example.invalid"))
    db.add(Workspace(id=workspace_id, name=f"Board {workspace_id}"))
    db.flush()
    db.add(
        FeatureFlag(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key=FLAG_AGENT_DELEGATION,
            enabled=flag_enabled,
        )
    )
    outcome = Outcome(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        function="marketing",
        title="Delegation board",
        desired_result="Analyze acquisition",
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

    dependency = None
    dependency_ids = []
    if depends_on is not None:
        dependency = RunStep(
            id=generate_snowflake_id(),
            run_id=outcome_run.id,
            type="research",
            status=depends_on,
        )
        db.add(dependency)
        db.flush()
        dependency_ids = [dependency.id]

    step = RunStep(
        id=generate_snowflake_id(),
        run_id=outcome_run.id,
        type="agent",
        inputs_jsonb={"task": "Analyze acquisition"},
        expected_output="Structured marketing report",
        risk_level=risk_level,
        depends_on_step_ids=dependency_ids,
        status="pending",
    )
    db.add(step)
    db.flush()
    return workspace_id, outcome_run, root, dependency, step


def _configure_board(monkeypatch, *providers):
    from app.workforce.agents.delegation.task_board import TaskBoardService

    manager = DelegationProviderManager()
    for provider in providers or (HealthyProvider(),):
        manager.register(provider)
    monkeypatch.setattr(TaskBoardService, "provider_manager", manager)
    return TaskBoardService


@pytest.mark.asyncio
async def test_assign_step_waits_for_dependencies(monkeypatch):
    from app.workforce.agents.delegation.task_board import DependencyNotReady

    db = SessionLocal()
    try:
        workspace_id, _run, _root, _dependency, step = _state(
            db, depends_on="pending"
        )
        service = _configure_board(monkeypatch)

        with pytest.raises(DependencyNotReady):
            await service.assign_step(
                db,
                workspace_id,
                step.id,
                "marketing",
                "mock",
                "in_process",
                "chief_of_staff",
            )
    finally:
        db.rollback()
        db.close()


@pytest.mark.asyncio
async def test_assign_step_is_idempotent_and_appends_ordered_events(monkeypatch):
    db = SessionLocal()
    try:
        workspace_id, outcome_run, root, _dependency, step = _state(db)
        service = _configure_board(monkeypatch)

        first = await service.assign_step(
            db, workspace_id, step.id, "marketing", "mock", "in_process", "chief_of_staff"
        )
        second = await service.assign_step(
            db, workspace_id, step.id, "marketing", "mock", "in_process", "chief_of_staff"
        )

        assert second.id == first.id
        assert first.root_agent_run_id == root.id
        assert first.status == "queued"
        assert step.assigned_agent_profile_id == "marketing"
        events = (
            db.query(RunEvent)
            .filter(RunEvent.run_id == outcome_run.id)
            .order_by(RunEvent.sequence)
            .all()
        )
        assert [event.event_type for event in events] == [
            "step.assigned",
            "step.delegation_queued",
        ]
        assert [event.sequence for event in events] == [1, 2]
    finally:
        db.rollback()
        db.close()


@pytest.mark.asyncio
async def test_coding_assignment_creates_exact_approval_in_same_transaction(monkeypatch):
    from agent_runtime.permissions.models import AgentApproval

    db = SessionLocal()
    try:
        workspace_id, _run, _root, _dependency, step = _state(db, risk_level="R1")
        service = _configure_board(monkeypatch, HealthyProvider("codex_device"))

        job = await service.assign_step(
            db, workspace_id, step.id, "marketing", "mock", "codex_device", "chief_of_staff"
        )

        approval = db.query(AgentApproval).filter(AgentApproval.run_id == job.parent_agent_run_id).one()
        assert job.status == "waiting_approval"
        assert step.status == "waiting_approval"
        assert approval.capability == "agent.delegate"
        assert approval.resource_type == "run_step"
        assert approval.resource_id == str(step.id)
        assert approval.idempotency_key == job.idempotency_key
    finally:
        db.rollback()
        db.close()


@pytest.mark.asyncio
async def test_assign_step_fails_closed_for_workspace_and_kill_switch(monkeypatch):
    from app.workforce.agents.delegation.task_board import (
        DelegationDisabled,
        TaskBoardAccessDenied,
    )

    db = SessionLocal()
    try:
        workspace_id, _run, _root, _dependency, step = _state(db, flag_enabled=False)
        service = _configure_board(monkeypatch)

        with pytest.raises(TaskBoardAccessDenied):
            await service.assign_step(
                db, workspace_id + 1, step.id, "marketing", "mock", "in_process", "chief_of_staff"
            )
        with pytest.raises(DelegationDisabled):
            await service.assign_step(
                db, workspace_id, step.id, "marketing", "mock", "in_process", "chief_of_staff"
            )
    finally:
        db.rollback()
        db.close()


@pytest.mark.asyncio
async def test_policy_denial_is_durable_and_never_queued(monkeypatch):
    db = SessionLocal()
    try:
        workspace_id, outcome_run, root, _dependency, step = _state(
            db, risk_level="R2"
        )
        root.permission_profile = "read_only"
        db.flush()
        service = _configure_board(monkeypatch)

        job = await service.assign_step(
            db, workspace_id, step.id, "marketing", "mock", "in_process", "chief_of_staff"
        )

        assert job.status == "denied"
        assert job.error_code == "DELEGATION_POLICY_DENIED"
        assert step.status == "failed"
        event_types = [
            row.event_type
            for row in db.query(RunEvent)
            .filter(RunEvent.run_id == outcome_run.id)
            .order_by(RunEvent.sequence)
            .all()
        ]
        assert event_types == ["step.assigned", "step.delegation_denied"]
    finally:
        db.rollback()
        db.close()


def test_complete_and_report_result_preserve_specialist_shape(monkeypatch):
    db = SessionLocal()
    try:
        workspace_id, outcome_run, _root, _dependency, step = _state(db)
        service = _configure_board(monkeypatch)
        # Assignment is async; construct its durable result directly for this
        # synchronous completion/report contract.
        from app.workforce.agents.delegation.models import DelegationJob

        step.assigned_agent_profile_id = "marketing"
        step.assigned_runtime = "mock"
        step.status = "running"
        job = DelegationJob(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            run_step_id=step.id,
            root_agent_run_id=outcome_run.agent_run_id,
            parent_agent_run_id=outcome_run.agent_run_id,
            attempt_no=1,
            provider_kind="agent_runtime",
            provider_name="in_process",
            profile_id="marketing",
            runtime_name="mock",
            status="running",
            idempotency_key=f"delegation:{step.id}:1",
        )
        db.add(job)
        db.flush()

        service.complete_job(
            db,
            workspace_id,
            job.id,
            DelegationResult(
                status=DelegationStatus.SUCCEEDED,
                structured_result={"qualified_leads": 8},
            ),
        )

        assert step.status == "completed"
        assert service.report_result(db, workspace_id, outcome_run.id) == {
            "marketing": {"qualified_leads": 8}
        }
    finally:
        db.rollback()
        db.close()
