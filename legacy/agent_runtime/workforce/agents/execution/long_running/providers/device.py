from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from agent_runtime.sessions.models import AgentRun
from core.snowflake import generate_snowflake_id
from db.session import SessionLocal
from integrations.devices.models import Device, DeveloperJob
from integrations.devices.service import request_job_cancel
from workforce.agents.execution.long_running.base import LongRunningWorkProvider
from workforce.agents.execution.long_running.types import (
    CancelResult,
    WorkContext,
    WorkHandle,
    WorkProviderCapabilities,
    WorkProviderHealth,
    WorkRequest,
    WorkState,
    WorkStatus,
)


_DEVICE_STATUS = {
    "QUEUED": WorkState.QUEUED,
    "WAITING_FOR_DEVICE": WorkState.QUEUED,
    "CLAIMED": WorkState.RUNNING,
    "RUNNING": WorkState.RUNNING,
    "WAITING_APPROVAL": WorkState.WAITING_APPROVAL,
    "SUCCEEDED": WorkState.SUCCEEDED,
    "FAILED": WorkState.FAILED,
    "CANCELLED": WorkState.CANCELLED,
}


class DeviceWorkProvider(LongRunningWorkProvider):
    executor_kind: str
    required_capabilities: tuple[str, ...]

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    @property
    def provider_name(self) -> str:
        return f"{self.executor_kind}_device"

    async def start(
        self,
        context: WorkContext,
        request: WorkRequest,
        idempotency_key: str,
    ) -> WorkHandle:
        db = self._session_factory()
        try:
            existing = (
                db.query(DeveloperJob)
                .filter(
                    DeveloperJob.workspace_id == context.workspace_id,
                    DeveloperJob.idempotency_key == idempotency_key,
                )
                .first()
            )
            if existing is not None:
                if existing.executor_kind != self.executor_kind:
                    raise RuntimeError("Idempotency key belongs to another executor kind")
                return self._handle(existing)
            parent = (
                db.query(AgentRun)
                .filter(
                    AgentRun.id == context.parent_agent_run_id,
                    AgentRun.workspace_id == context.workspace_id,
                )
                .one()
            )
            job = DeveloperJob(
                id=generate_snowflake_id(),
                workspace_id=context.workspace_id,
                agent_run_id=context.parent_agent_run_id,
                run_step_id=context.run_step_id,
                title=request.task[:255],
                executor_kind=self.executor_kind,
                required_capabilities=list(self.required_capabilities),
                status="QUEUED",
                request_jsonb={
                    "task": request.task,
                    "payload": request.payload,
                    "permission_profile": request.permission_profile,
                    "timeout_seconds": request.timeout_seconds,
                    "user_id": parent.user_id,
                },
                idempotency_key=idempotency_key,
                created_at=datetime.utcnow(),
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            return self._handle(job)
        finally:
            db.close()

    async def poll(self, context: WorkContext, handle: WorkHandle) -> WorkStatus:
        db = self._session_factory()
        try:
            job = (
                db.query(DeveloperJob)
                .filter(
                    DeveloperJob.id == int(handle.external_id),
                    DeveloperJob.workspace_id == context.workspace_id,
                    DeveloperJob.executor_kind == self.executor_kind,
                )
                .first()
            )
            if job is None:
                return WorkStatus(
                    state=WorkState.FAILED,
                    error_code="DEVICE_JOB_STATE_LOST",
                    error_message="DeveloperJob is missing or cross-workspace",
                )
            return WorkStatus(
                state=_DEVICE_STATUS.get(job.status, WorkState.FAILED),
                structured_result=job.result_jsonb,
                metrics={"assigned_device_id": job.assigned_device_id},
                error_code=("DEVICE_JOB_UNKNOWN_STATUS" if job.status not in _DEVICE_STATUS else None),
                error_message=(f"Unknown DeveloperJob status {job.status}" if job.status not in _DEVICE_STATUS else None),
                next_poll_after_seconds=(2 if job.status not in ("SUCCEEDED", "FAILED", "CANCELLED") else None),
            )
        finally:
            db.close()

    async def cancel(self, context: WorkContext, handle: WorkHandle) -> CancelResult:
        db = self._session_factory()
        try:
            job = request_job_cancel(
                db,
                int(handle.external_id),
                context.workspace_id,
            )
            state = _DEVICE_STATUS.get(job.status, WorkState.RUNNING)
            return CancelResult(accepted=True, state=state)
        finally:
            db.close()

    async def health(self) -> WorkProviderHealth:
        db = self._session_factory()
        try:
            devices = (
                db.query(Device)
                .filter(
                    Device.status == "online",
                    Device.capabilities.contains(list(self.required_capabilities)),
                )
                .count()
            )
            return WorkProviderHealth(
                provider_name=self.provider_name,
                available=devices > 0,
                details={"compatible_devices": devices},
            )
        finally:
            db.close()

    async def capabilities(self) -> WorkProviderCapabilities:
        return WorkProviderCapabilities(
            cancel_supported=True,
            idempotent_start=True,
            asynchronous=True,
        )

    def _handle(self, job: DeveloperJob) -> WorkHandle:
        return WorkHandle(
            provider_name=self.provider_name,
            external_id=str(job.id),
            native_job_id=str(job.id),
            safe_metadata={"executor_kind": self.executor_kind},
        )
