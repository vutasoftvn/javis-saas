from app.workforce.agents.delegation.provider import DelegationProvider
from app.workforce.agents.delegation.types import (
    DelegationHandle,
    DelegationRequest,
    DelegationResult,
    DelegationStatus,
    ProviderHealth,
)
from app.workforce.agents.runtime.manager import (
    AgentRuntimeManager,
    agent_runtime_manager,
)
from app.workforce.agents.runtime.types import AgentRunRequest, AgentRunResult


_RUNTIME_STATUS = {
    "completed": DelegationStatus.SUCCEEDED,
    "partial": DelegationStatus.SUCCEEDED,
    "failed": DelegationStatus.FAILED,
    "cancelled": DelegationStatus.CANCELLED,
    "awaiting_approval": DelegationStatus.WAITING_APPROVAL,
}


class InProcessSubagentProvider(DelegationProvider):
    """Run one AgentRuntime request in the delegation worker process."""

    def __init__(
        self,
        runtime_manager: AgentRuntimeManager = agent_runtime_manager,
    ) -> None:
        self._runtime_manager = runtime_manager

    @property
    def provider_name(self) -> str:
        return "in_process"

    async def delegate(
        self,
        request: DelegationRequest,
        idempotency_key: str,
    ) -> DelegationHandle:
        runtime = self._runtime_manager.get_runtime(
            request.runtime_name,
            allow_default=False,
        )
        context = dict(request.context)
        user_id = context.pop("user_id", 0)
        company_id = context.pop("company_id", request.workspace_id)
        runtime_result = await runtime.run(
            AgentRunRequest(
                company_id=str(company_id),
                workspace_id=str(request.workspace_id),
                user_id=str(user_id),
                agent_key=request.profile_id,
                task=request.task,
                context=context,
                permission_profile=request.permission_profile,
                parent_run_id=str(request.parent_agent_run_id),
                timeout_seconds=request.timeout_seconds,
            )
        )
        normalized = self._normalize(runtime_result)
        return DelegationHandle(
            provider_name=self.provider_name,
            external_id=runtime_result.run_id,
            native_job_id=runtime_result.runtime_session_id,
            safe_metadata={
                "runtime_name": runtime.runtime_name,
                "idempotency_key": idempotency_key,
                "terminal_result": normalized.model_dump(mode="json"),
            },
        )

    async def poll(self, handle: DelegationHandle) -> DelegationResult:
        result = handle.safe_metadata.get("terminal_result")
        if isinstance(result, dict):
            return DelegationResult.model_validate(result)
        return DelegationResult(
            status=DelegationStatus.FAILED,
            retryable=False,
            error_code="DELEGATION_PROVIDER_STATE_LOST",
            error_message="In-process terminal result is missing from the durable handle",
        )

    async def cancel(self, handle: DelegationHandle) -> bool:
        runtime_name = handle.safe_metadata.get("runtime_name")
        if not isinstance(runtime_name, str):
            return False
        runtime = self._runtime_manager.get_runtime(runtime_name, allow_default=False)
        await runtime.cancel(handle.external_id)
        return True

    async def health(self) -> ProviderHealth:
        names = self._runtime_manager.list_runtimes()
        if not names:
            return ProviderHealth(
                provider_name=self.provider_name,
                available=False,
                details={"reason": "no registered AgentRuntime"},
            )
        statuses: dict[str, str] = {}
        available = False
        for name in names:
            health = await self._runtime_manager.get_runtime(
                name,
                allow_default=False,
            ).health()
            statuses[name] = health.status
            available = available or health.status == "healthy"
        return ProviderHealth(
            provider_name=self.provider_name,
            available=available,
            details={"runtimes": statuses},
        )

    @staticmethod
    def _normalize(result: AgentRunResult) -> DelegationResult:
        error = result.error or {}
        return DelegationResult(
            status=_RUNTIME_STATUS[result.status],
            structured_result=result.structured_output,
            output_text=result.output_text,
            metrics=result.metrics,
            retryable=bool(error.get("retryable", False)),
            error_code=error.get("code"),
            error_message=error.get("message"),
        )
