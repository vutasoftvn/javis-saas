from typing import Callable

from sqlalchemy.orm import Session

from agent_runtime.sessions.models import AgentRun
from core.snowflake import generate_snowflake_id
from db.session import SessionLocal
from founder_os.outcomes.models import Artifact
from workforce.agents.execution.long_running.base import LongRunningWorkProvider
from workforce.agents.execution.long_running.manager import LongRunningProviderUnknown
from workforce.agents.execution.long_running.types import (
    CancelResult,
    WorkHandle,
    WorkProviderCapabilities,
    WorkProviderHealth,
    WorkState,
    WorkStatus,
)
from workforce.agents.execution.manager import (
    ExecutionProviderManager,
    execution_provider_manager,
)
from workforce.agents.execution.models import ExecutionJob


_EXECUTION_STATE = {
    "queued": WorkState.QUEUED,
    "preparing": WorkState.RUNNING,
    "running": WorkState.RUNNING,
    "collecting": WorkState.RUNNING,
    "awaiting_approval": WorkState.WAITING_APPROVAL,
    "completed": WorkState.SUCCEEDED,
    "failed": WorkState.FAILED,
    "blocked": WorkState.FAILED,
    "cancelled": WorkState.CANCELLED,
}


class SandboxExecutor(LongRunningWorkProvider):
    def __init__(
        self,
        provider_name: str | None,
        manager: ExecutionProviderManager = execution_provider_manager,
        session_factory: Callable[[], Session] = SessionLocal,
    ) -> None:
        if not provider_name:
            raise LongRunningProviderUnknown(
                "Sandbox delegation requires an explicit execution provider"
            )
        try:
            manager.get(provider_name)
        except Exception as exc:
            raise LongRunningProviderUnknown(
                f"Explicit sandbox provider '{provider_name}' is not registered"
            ) from exc
        self._execution_provider_name = provider_name
        self._manager = manager
        self._session_factory = session_factory

    @property
    def provider_name(self):
        return "sandbox"

    async def start(self, context, request, idempotency_key):
        self._manager.get(self._execution_provider_name)
        db = self._session_factory()
        try:
            existing = db.query(ExecutionJob).filter(
                ExecutionJob.workspace_id == context.workspace_id,
                ExecutionJob.idempotency_key == idempotency_key,
            ).first()
            if existing is not None:
                if existing.provider != self._execution_provider_name:
                    raise RuntimeError("Idempotency key belongs to another sandbox provider")
                return self._handle(existing)
            parent = db.query(AgentRun).filter(
                AgentRun.id == context.parent_agent_run_id,
                AgentRun.workspace_id == context.workspace_id,
            ).one()
            job = ExecutionJob(
                id=generate_snowflake_id(),
                workspace_id=context.workspace_id,
                user_id=parent.user_id,
                agent_key=context.profile_id,
                agent_run_id=context.parent_agent_run_id,
                provider=self._execution_provider_name,
                status="queued",
                idempotency_key=idempotency_key,
                metadata_jsonb={
                    **request.payload,
                    "task": request.task,
                    "run_step_id": str(context.run_step_id),
                },
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            return self._handle(job)
        finally:
            db.close()

    async def poll(self, context, handle):
        db = self._session_factory()
        try:
            job = db.query(ExecutionJob).filter(
                ExecutionJob.id == int(handle.external_id),
                ExecutionJob.workspace_id == context.workspace_id,
                ExecutionJob.provider == self._execution_provider_name,
            ).first()
            if job is None:
                return WorkStatus(
                    state=WorkState.FAILED,
                    error_code="SANDBOX_JOB_STATE_LOST",
                    error_message="ExecutionJob is missing or cross-workspace",
                )
            artifacts = db.query(Artifact).filter(Artifact.execution_job_id == job.id).all()
            return WorkStatus(
                state=_EXECUTION_STATE.get(job.status, WorkState.FAILED),
                structured_result={
                    "job_id": str(job.id),
                    "artifacts": [
                        {
                            "id": str(artifact.id),
                            "title": artifact.title,
                            "type": artifact.type,
                            "object_storage_uri": artifact.object_storage_uri,
                        }
                        for artifact in artifacts
                    ],
                },
                error_code=job.error_code,
                error_message=job.error_message,
                next_poll_after_seconds=(2 if job.status not in ("completed", "failed", "blocked", "cancelled") else None),
            )
        finally:
            db.close()

    async def cancel(self, context, handle):
        db = self._session_factory()
        try:
            job = db.query(ExecutionJob).filter(
                ExecutionJob.id == int(handle.external_id),
                ExecutionJob.workspace_id == context.workspace_id,
            ).first()
            if job is None:
                return CancelResult(accepted=False, state=WorkState.FAILED)
            if job.status == "queued":
                job.status = "cancelled"
                db.commit()
                return CancelResult(accepted=True, state=WorkState.CANCELLED)
            if job.sandbox_id:
                await self._manager.get(job.provider).terminate(job.sandbox_id)
            job.status = "cancelled"
            db.commit()
            return CancelResult(accepted=True, state=WorkState.CANCELLED)
        finally:
            db.close()

    async def health(self):
        health = await self._manager.get(self._execution_provider_name).health()
        return WorkProviderHealth(
            provider_name=self.provider_name,
            available=health.available,
            details={"execution_provider": self._execution_provider_name, **health.details},
        )

    async def capabilities(self):
        return WorkProviderCapabilities()

    def _handle(self, job):
        return WorkHandle(
            provider_name=self.provider_name,
            external_id=str(job.id),
            native_job_id=job.sandbox_id,
            safe_metadata={"execution_provider": self._execution_provider_name},
        )
