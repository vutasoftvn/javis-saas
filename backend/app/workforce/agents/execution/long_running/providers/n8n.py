from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.db.session import SessionLocal
from app.workforce.agents.execution.long_running.base import LongRunningWorkProvider
from app.workforce.agents.execution.long_running.types import (
    CancelResult,
    WorkContext,
    WorkHandle,
    WorkProviderCapabilities,
    WorkProviderHealth,
    WorkRequest,
    WorkState,
    WorkStatus,
)
from app.workforce.automation.models import AutomationRun
from app.workforce.automation.runtime.adapters.n8n import N8nAdapter
from app.workforce.automation.runtime.base import AutomationProvider
from app.workforce.automation.runtime.types import AutomationRequest


_AUTOMATION_STATE = {
    "queued": WorkState.QUEUED,
    "running": WorkState.RUNNING,
    "succeeded": WorkState.SUCCEEDED,
    "completed": WorkState.SUCCEEDED,
    "failed": WorkState.FAILED,
    "cancelled": WorkState.CANCELLED,
}


class N8nExecutor(LongRunningWorkProvider):
    def __init__(
        self,
        provider: AutomationProvider | None = None,
        session_factory: Callable[[], Session] = SessionLocal,
    ) -> None:
        self._provider = provider or N8nAdapter()
        self._session_factory = session_factory

    @property
    def provider_name(self) -> str:
        return "n8n"

    async def start(self, context, request, idempotency_key):
        automation_key = request.payload.get("automation_key")
        if not isinstance(automation_key, str) or not automation_key:
            raise ValueError("n8n work requires payload.automation_key")
        db = self._session_factory()
        try:
            run = (
                db.query(AutomationRun)
                .filter(
                    AutomationRun.workspace_id == context.workspace_id,
                    AutomationRun.idempotency_key == idempotency_key,
                )
                .first()
            )
            if run is not None:
                return self._handle(run)
            run = AutomationRun(
                id=generate_snowflake_id(),
                workspace_id=context.workspace_id,
                company_id=context.workspace_id,
                automation_key=automation_key,
                provider="n8n",
                agent_run_id=context.parent_agent_run_id,
                status="running",
                risk_level="high",
                idempotency_key=idempotency_key,
                payload_jsonb={
                    **request.payload,
                    "correlation_id": idempotency_key,
                    "run_step_id": str(context.run_step_id),
                },
                started_at=datetime.now(timezone.utc),
            )
            db.add(run)
            db.commit()
            start = await self._provider.execute(
                AutomationRequest(
                    automation_key=automation_key,
                    execution_id=str(run.id),
                    workspace_id=context.workspace_id,
                    company_id=context.workspace_id,
                    payload=request.payload,
                    correlation_id=idempotency_key,
                    idempotency_key=idempotency_key,
                )
            )
            run.provider_execution_id = start.provider_execution_id
            run.status = start.status
            if start.status == "failed":
                run.error_summary = start.error
                run.finished_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(run)
            return self._handle(run)
        finally:
            db.close()

    async def poll(self, context, handle):
        db = self._session_factory()
        try:
            run = db.query(AutomationRun).filter(
                AutomationRun.id == int(handle.external_id),
                AutomationRun.workspace_id == context.workspace_id,
                AutomationRun.provider == "n8n",
            ).first()
            if run is None:
                return WorkStatus(
                    state=WorkState.FAILED,
                    error_code="N8N_RUN_STATE_LOST",
                    error_message="AutomationRun is missing or cross-workspace",
                )
            if run.status not in ("succeeded", "completed", "failed", "cancelled"):
                native = await self._provider.get_status(run.provider_execution_id or "")
                run.status = native.status
                run.result_jsonb = native.result
                run.error_summary = native.error
                if native.status in ("succeeded", "failed", "cancelled"):
                    run.finished_at = datetime.now(timezone.utc)
                db.commit()
            return WorkStatus(
                state=_AUTOMATION_STATE.get(run.status, WorkState.FAILED),
                structured_result=run.result_jsonb,
                error_code=("N8N_UNKNOWN_STATUS" if run.status not in _AUTOMATION_STATE else None),
                error_message=run.error_summary,
                next_poll_after_seconds=(2 if run.status not in ("succeeded", "completed", "failed", "cancelled") else None),
            )
        finally:
            db.close()

    async def cancel(self, context, handle):
        try:
            await self._provider.cancel(handle.native_job_id or "")
        except NotImplementedError as exc:
            return CancelResult(
                accepted=False,
                state=WorkState.RUNNING,
                message=str(exc),
            )
        return CancelResult(accepted=True, state=WorkState.CANCELLED)

    async def health(self):
        health = await self._provider.health()
        return WorkProviderHealth(
            provider_name=self.provider_name,
            available=health.status == "healthy",
            details=health.details,
        )

    async def capabilities(self):
        return WorkProviderCapabilities(
            cancel_supported=False,
            idempotent_start=True,
            asynchronous=True,
        )

    def _handle(self, run):
        return WorkHandle(
            provider_name=self.provider_name,
            external_id=str(run.id),
            native_job_id=run.provider_execution_id,
            safe_metadata={"correlation_id": run.idempotency_key},
        )
