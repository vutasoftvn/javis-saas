from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from agent_runtime.sessions.models import AgentRun
from app.core.feature_flags import FLAG_AGENT_DELEGATION, is_enabled
from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.workforce.agents.delegation.events import append_run_event
from app.workforce.agents.delegation.limits import assert_can_delegate, resolve_run_chain
from app.workforce.agents.delegation.manager import (
    DelegationProviderManager,
    delegation_provider_manager,
)
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.delegation.policy import DelegationPolicyEngine
from app.workforce.agents.delegation.states import (
    transition_delegation,
    transition_step,
)
from app.workforce.agents.delegation.types import DelegationResult, DelegationStatus
from app.workforce.agents.governance.approval_service import ApprovalService
from app.workforce.agents.governance.policy_engine import PolicyAction
from app.workforce.agents.profiles.registry import (
    AgentProfileRegistry,
    agent_profile_registry,
)


class TaskBoardError(RuntimeError):
    pass


class TaskBoardAccessDenied(TaskBoardError):
    pass


class DelegationDisabled(TaskBoardError):
    pass


class DependencyNotReady(TaskBoardError):
    pass


class AgentProfileUnknown(TaskBoardError):
    pass


class AssignmentConflict(TaskBoardError):
    pass


class TaskBoardService:
    """Transactional owner of governed RunStep assignment and result state."""

    provider_manager: DelegationProviderManager = delegation_provider_manager
    profile_registry: AgentProfileRegistry = agent_profile_registry

    @classmethod
    async def assign_step(
        cls,
        db: Session,
        workspace_id: int,
        step_id: int,
        profile_id: str,
        runtime_name: str | None,
        provider_name: str,
        actor_agent_key: str,
    ) -> DelegationJob:
        step = (
            db.query(RunStep)
            .filter(RunStep.id == step_id)
            .with_for_update()
            .first()
        )
        if step is None:
            raise TaskBoardAccessDenied(f"RunStep {step_id} was not found")
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == step.run_id).first()
        outcome = (
            db.query(Outcome)
            .filter(Outcome.id == outcome_run.outcome_id)
            .first()
            if outcome_run
            else None
        )
        if outcome_run is None or outcome is None or outcome.workspace_id != workspace_id:
            raise TaskBoardAccessDenied(
                f"RunStep {step_id} does not belong to workspace {workspace_id}"
            )

        existing = (
            db.query(DelegationJob)
            .filter(
                DelegationJob.workspace_id == workspace_id,
                DelegationJob.run_step_id == step.id,
                DelegationJob.attempt_no == 1,
            )
            .first()
        )
        if existing is not None:
            if (
                existing.profile_id != profile_id
                or existing.provider_name != provider_name
                or (runtime_name is not None and existing.runtime_name != runtime_name)
            ):
                raise AssignmentConflict(
                    f"RunStep {step.id} attempt 1 is already assigned with different routing"
                )
            return existing

        if not is_enabled(db, FLAG_AGENT_DELEGATION, workspace_id=workspace_id):
            raise DelegationDisabled(
                f"Feature '{FLAG_AGENT_DELEGATION}' is disabled for workspace {workspace_id}"
            )

        cls._assert_dependencies_ready(db, step)
        profile = await cls.profile_registry.get_profile(profile_id)
        if profile is None:
            raise AgentProfileUnknown(f"Agent profile '{profile_id}' is not registered")
        provider = cls.provider_manager.get(provider_name)
        health = await provider.health()

        parent_run = (
            db.query(AgentRun)
            .filter(
                AgentRun.id == outcome_run.agent_run_id,
                AgentRun.workspace_id == workspace_id,
            )
            .first()
        )
        if parent_run is None:
            raise TaskBoardError(
                f"OutcomeRun {outcome_run.id} has no tenant-safe parent AgentRun"
            )
        assert_can_delegate(db, workspace_id, parent_run.id)
        root_run = resolve_run_chain(db, workspace_id, parent_run.id)[0]

        decision = DelegationPolicyEngine.evaluate(
            parent_permission=parent_run.permission_profile,
            child_permission=profile.permission_profile,
            risk_level=step.risk_level,
            provider_name=provider_name,
            provider_healthy=health.available,
        )
        effective_runtime = runtime_name or profile.preferred_runtime
        idempotency_key = f"delegation:{step.id}:attempt:1"
        status = "queued"
        if decision.action == PolicyAction.REQUIRE_APPROVAL:
            status = "waiting_approval"
        elif decision.action == PolicyAction.DENY:
            status = "denied"

        job = DelegationJob(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            run_step_id=step.id,
            root_agent_run_id=root_run.id,
            parent_agent_run_id=parent_run.id,
            attempt_no=1,
            provider_kind=("agent_runtime" if provider_name == "in_process" else provider_name),
            provider_name=provider_name,
            profile_id=profile.id,
            runtime_name=effective_runtime,
            status=(
                transition_delegation("queued", status)
                if status != "queued"
                else "queued"
            ),
            idempotency_key=idempotency_key,
        )
        db.add(job)
        step.assigned_agent_profile_id = profile.id
        step.assigned_runtime = effective_runtime
        if status == "waiting_approval":
            step.status = transition_step(step.status, "waiting_approval")
        elif status == "denied":
            step.status = transition_step(step.status, "failed")
            job.error_code = "DELEGATION_POLICY_DENIED"
            job.error_message = decision.reason
        db.flush()

        append_run_event(
            db,
            outcome_run.id,
            "step.assigned",
            {
                "step_id": str(step.id),
                "profile_id": profile.id,
                "provider_name": provider_name,
                "runtime_name": effective_runtime,
                "actor_agent_key": actor_agent_key,
            },
            f"step:{step.id}:assigned:attempt:1",
        )
        event_type = {
            "queued": "step.delegation_queued",
            "waiting_approval": "step.waiting_approval",
            "denied": "step.delegation_denied",
        }[status]
        append_run_event(
            db,
            outcome_run.id,
            event_type,
            {
                "step_id": str(step.id),
                "delegation_job_id": str(job.id),
                "reason": decision.reason,
            },
            f"delegation:{job.id}:{status}",
        )

        if status == "waiting_approval":
            ApprovalService.create_approval(
                db,
                workspace_id=workspace_id,
                company_id=parent_run.company_id,
                agent_key=actor_agent_key,
                action_type="delegation.assign",
                tool_name=f"delegation.{provider_name}",
                input_preview={
                    "step_id": str(step.id),
                    "profile_id": profile.id,
                    "runtime_name": effective_runtime,
                },
                risk_level=step.risk_level,
                run_id=parent_run.id,
                capability="agent.delegate",
                resource_type="run_step",
                resource_id=str(step.id),
                idempotency_key=idempotency_key,
                commit=False,
            )

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def _assert_dependencies_ready(db: Session, step: RunStep) -> None:
        dependency_ids = [int(value) for value in (step.depends_on_step_ids or [])]
        if not dependency_ids:
            return
        dependencies = (
            db.query(RunStep)
            .filter(
                RunStep.run_id == step.run_id,
                RunStep.id.in_(dependency_ids),
            )
            .all()
        )
        complete_ids = {dependency.id for dependency in dependencies if dependency.status == "completed"}
        missing = set(dependency_ids) - complete_ids
        if missing:
            raise DependencyNotReady(
                f"RunStep {step.id} is waiting for dependencies {sorted(missing)}"
            )

    @classmethod
    def complete_job(
        cls,
        db: Session,
        workspace_id: int,
        job_id: int,
        result: DelegationResult,
    ) -> DelegationJob:
        job = (
            db.query(DelegationJob)
            .filter(
                DelegationJob.id == job_id,
                DelegationJob.workspace_id == workspace_id,
            )
            .with_for_update()
            .first()
        )
        if job is None:
            raise TaskBoardAccessDenied(
                f"DelegationJob {job_id} does not belong to workspace {workspace_id}"
            )
        step = db.query(RunStep).filter(RunStep.id == job.run_step_id).with_for_update().one()
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == step.run_id).one()
        outcome = db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id).one()
        if outcome.workspace_id != workspace_id:
            raise TaskBoardAccessDenied(
                f"DelegationJob {job_id} crosses workspace boundary"
            )
        if job.status in {"succeeded", "failed", "cancelled", "denied"}:
            return job

        terminal_status = {
            DelegationStatus.SUCCEEDED: "succeeded",
            DelegationStatus.FAILED: "failed",
            DelegationStatus.CANCELLED: "cancelled",
        }.get(result.status)
        if terminal_status is None:
            raise TaskBoardError(
                f"Delegation result '{result.status.value}' is not terminal"
            )

        now = datetime.now(timezone.utc)
        job.status = transition_delegation(job.status, terminal_status)
        job.result_jsonb = result.model_dump(mode="json")
        job.error_code = result.error_code
        job.error_message = result.error_message
        job.completed_at = now
        step.status = transition_step(step.status, {
            "succeeded": "completed",
            "failed": "failed",
            "cancelled": "cancelled",
        }[terminal_status])
        step.result_jsonb = (
            result.structured_result
            if result.structured_result is not None
            else ({"output_text": result.output_text} if result.output_text else None)
        )
        if job.child_agent_run_id is not None:
            child = (
                db.query(AgentRun)
                .filter(
                    AgentRun.id == job.child_agent_run_id,
                    AgentRun.workspace_id == workspace_id,
                )
                .first()
            )
            if child is None:
                raise TaskBoardError("Delegation child AgentRun is missing or cross-workspace")
            child.status = {
                "succeeded": "completed",
                "failed": "failed",
                "cancelled": "cancelled",
            }[terminal_status]
            child.finished_at = now

        append_run_event(
            db,
            outcome_run.id,
            f"step.delegation_{terminal_status}",
            {
                "step_id": str(step.id),
                "delegation_job_id": str(job.id),
                "error_code": result.error_code,
            },
            f"delegation:{job.id}:terminal:{terminal_status}",
        )
        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def cancel_step(
        cls,
        db: Session,
        workspace_id: int,
        step_id: int,
    ) -> DelegationJob:
        job = (
            db.query(DelegationJob)
            .join(RunStep, RunStep.id == DelegationJob.run_step_id)
            .filter(
                DelegationJob.workspace_id == workspace_id,
                RunStep.id == step_id,
                DelegationJob.status.notin_(("succeeded", "failed", "cancelled", "denied")),
            )
            .order_by(DelegationJob.attempt_no.desc())
            .with_for_update()
            .first()
        )
        if job is None:
            raise TaskBoardAccessDenied(f"No active delegation for RunStep {step_id}")
        step = db.query(RunStep).filter(RunStep.id == step_id).first()
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == step.run_id).first() if step else None
        outcome = db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id).first() if outcome_run else None
        if outcome is None or outcome.workspace_id != workspace_id:
            raise TaskBoardAccessDenied(
                f"RunStep {step_id} does not belong to workspace {workspace_id}"
            )
        job.status = transition_delegation(job.status, "cancel_requested")
        job.cancel_requested_at = datetime.now(timezone.utc)
        append_run_event(
            db,
            step.run_id,
            "step.cancel_requested",
            {"step_id": str(step_id), "delegation_job_id": str(job.id)},
            f"delegation:{job.id}:cancel_requested",
        )
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def report_result(
        db: Session,
        workspace_id: int,
        run_id: int,
    ) -> dict[str, Any]:
        outcome_run = (
            db.query(OutcomeRun)
            .join(Outcome, Outcome.id == OutcomeRun.outcome_id)
            .filter(
                OutcomeRun.id == run_id,
                Outcome.workspace_id == workspace_id,
            )
            .first()
        )
        if outcome_run is None:
            raise TaskBoardAccessDenied(
                f"OutcomeRun {run_id} does not belong to workspace {workspace_id}"
            )
        steps = (
            db.query(RunStep)
            .filter(
                RunStep.run_id == run_id,
                RunStep.status == "completed",
                RunStep.assigned_agent_profile_id.is_not(None),
            )
            .order_by(RunStep.created_at, RunStep.id)
            .all()
        )
        return {
            step.assigned_agent_profile_id: step.result_jsonb
            for step in steps
        }
