from datetime import datetime, timedelta, timezone

from app.workforce.agents.delegation.provider import DelegationProvider
from app.workforce.agents.delegation.types import (
    DelegationHandle,
    DelegationRequest,
    DelegationResult,
    DelegationStatus,
    ProviderHealth,
)
from app.workforce.agents.execution.long_running.manager import (
    LongRunningWorkProviderManager,
    long_running_provider_manager,
)
from app.workforce.agents.execution.long_running.types import (
    WorkContext,
    WorkHandle,
    WorkRequest,
    WorkState,
    WorkStatus,
)


_STATUS_MAP = {
    WorkState.QUEUED: DelegationStatus.QUEUED,
    WorkState.RUNNING: DelegationStatus.RUNNING,
    WorkState.WAITING_APPROVAL: DelegationStatus.WAITING_APPROVAL,
    WorkState.SUCCEEDED: DelegationStatus.SUCCEEDED,
    WorkState.FAILED: DelegationStatus.FAILED,
    WorkState.CANCELLED: DelegationStatus.CANCELLED,
}


class LongRunningExecutorBridge(DelegationProvider):
    """Adapt one long-running provider to the durable delegation worker."""

    def __init__(
        self,
        provider_name: str,
        manager: LongRunningWorkProviderManager = long_running_provider_manager,
    ) -> None:
        self._provider_name = provider_name
        self._manager = manager

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def delegate(
        self,
        request: DelegationRequest,
        idempotency_key: str,
    ) -> DelegationHandle:
        if request.provider_name != self.provider_name:
            raise ValueError(
                f"Bridge '{self.provider_name}' cannot route request for "
                f"'{request.provider_name}'"
            )
        provider = self._manager.get(request.provider_name)
        capabilities = await provider.capabilities()
        if not capabilities.idempotent_start:
            raise RuntimeError(
                f"Long-running provider '{request.provider_name}' cannot guarantee "
                "idempotent start"
            )
        context = self._context(request)
        work_handle = await provider.start(
            context,
            WorkRequest(
                task=request.task,
                permission_profile=request.permission_profile,
                timeout_seconds=request.timeout_seconds,
                payload=request.context,
            ),
            idempotency_key,
        )
        return DelegationHandle(
            provider_name=request.provider_name,
            external_id=work_handle.external_id,
            native_job_id=work_handle.native_job_id,
            safe_metadata={
                "work_context": context.model_dump(mode="json"),
                "work_handle": work_handle.model_dump(mode="json"),
            },
        )

    async def poll(self, handle: DelegationHandle) -> DelegationResult:
        provider = self._manager.get(handle.provider_name)
        context, work_handle = self._restore(handle)
        status = await provider.poll(context, work_handle)
        return self._normalize(status)

    async def cancel(self, handle: DelegationHandle) -> bool:
        provider = self._manager.get(handle.provider_name)
        context, work_handle = self._restore(handle)
        result = await provider.cancel(context, work_handle)
        return result.accepted

    async def health(self) -> ProviderHealth:
        health = await self._manager.get(self.provider_name).health()
        capabilities = await self._manager.get(self.provider_name).capabilities()
        return ProviderHealth(
            provider_name=self.provider_name,
            available=health.available,
            details={
                **health.details,
                "capabilities": capabilities.model_dump(mode="json"),
            },
        )

    @staticmethod
    def _context(request: DelegationRequest) -> WorkContext:
        return WorkContext(
            workspace_id=request.workspace_id,
            outcome_run_id=request.outcome_run_id,
            run_step_id=request.run_step_id,
            root_agent_run_id=request.root_agent_run_id,
            parent_agent_run_id=request.parent_agent_run_id,
            profile_id=request.profile_id,
        )

    @staticmethod
    def _restore(handle: DelegationHandle) -> tuple[WorkContext, WorkHandle]:
        context = handle.safe_metadata.get("work_context")
        work_handle = handle.safe_metadata.get("work_handle")
        if not isinstance(context, dict) or not isinstance(work_handle, dict):
            raise ValueError("Long-running delegation handle is missing durable bridge state")
        return WorkContext.model_validate(context), WorkHandle.model_validate(work_handle)

    @staticmethod
    def _normalize(status: WorkStatus) -> DelegationResult:
        next_poll_at = None
        if status.next_poll_after_seconds is not None:
            next_poll_at = datetime.now(timezone.utc) + timedelta(
                seconds=status.next_poll_after_seconds
            )
        return DelegationResult(
            status=_STATUS_MAP[status.state],
            structured_result=status.structured_result,
            output_text=status.output_text,
            metrics={
                **status.metrics,
                **({"progress": status.progress} if status.progress is not None else {}),
            },
            retryable=status.retryable,
            error_code=status.error_code,
            error_message=status.error_message,
            next_poll_at=next_poll_at,
        )
