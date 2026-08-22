# backend/app/tests/agents/test_orchestration_service_seam.py
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
from workforce.agents.orchestration import service as orchestration_service
from workforce.agents.orchestration.adk.nodes.specialist_delegation_node import interrupt_id_for_step
from workforce.agents.orchestration.runtime_session_models import RuntimeSession


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


@pytest.mark.asyncio
async def test_orchestrate_then_resume_mission_reaches_terminal_status(monkeypatch):
    manager = DelegationProviderManager()
    manager.register(HealthyProvider())
    monkeypatch.setattr(TaskBoardService, "provider_manager", manager)

    from db.session import SessionLocal

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"seam-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Seam {workspace_id}"))
        db.add(FeatureFlag(id=generate_snowflake_id(), workspace_id=workspace_id, key=FLAG_AGENT_DELEGATION, enabled=True))
        db.commit()

        goal = f"Seam test — {generate_snowflake_id()}"
        result = await orchestration_service.orchestrate_mission(
            db, workspace_id=workspace_id, user_id=user_id, goal=goal, domains=["finance"],
        )
        assert result.status == "delegating"

        runtime_session = db.query(RuntimeSession).filter(RuntimeSession.mission_run_id == int(result.mission_id)).one()
        assert runtime_session.runtime_type == "ADK"
        assert runtime_session.external_session_id

        outcome = db.query(Outcome).filter(Outcome.desired_result == goal).one()
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.outcome_id == outcome.id).one()
        step = db.query(RunStep).filter(RunStep.run_id == outcome_run.id).one()
        job = db.query(DelegationJob).filter(DelegationJob.run_step_id == step.id).one()

        step.status = "running"
        job.status = "running"
        db.commit()

        TaskBoardService.complete_job(
            db, workspace_id, job.id,
            DelegationResult(status=DelegationStatus.SUCCEEDED, structured_result={"status": "success", "runway_months": 9}),
        )

        resumed = await orchestration_service.resume_mission(
            db, mission_run_id=int(result.mission_id),
            interrupt_id=interrupt_id_for_step(step.id),
            resume_payload={"step_id": step.id, "status": "completed"},
        )
        assert resumed.status in ("completed", "failed", "partial")
        assert resumed.mission_id == result.mission_id
    finally:
        db.close()
