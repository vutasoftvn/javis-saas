from typing import Optional
from workforce.automation.runtime.base import AutomationProvider
from workforce.automation.runtime.types import (
    AutomationHealth,
    AutomationRequest,
    AutomationRunStatus,
    AutomationStartResult,
)


class MockAutomationProvider(AutomationProvider):
    """Deterministic mock provider for automated unit testing and sandbox development."""

    def __init__(self, healthy: bool = True) -> None:
        self._healthy = healthy
        self._runs: dict[str, AutomationRunStatus] = {}

    async def health(self) -> AutomationHealth:
        if not self._healthy:
            return AutomationHealth(
                status="unavailable",
                provider="mock",
                details={"reason": "Mock provider manually set to unavailable"},
            )
        return AutomationHealth(
            status="healthy",
            provider="mock",
            details={"version": "1.0-mock", "active_runs": len(self._runs)},
        )

    async def execute(self, request: AutomationRequest) -> AutomationStartResult:
        external_id = f"mock_exec_{request.execution_id}"
        self._runs[external_id] = AutomationRunStatus(
            status="succeeded",
            progress=1.0,
            result={"delivered": True, "target": request.automation_key, "payload": request.payload},
        )
        return AutomationStartResult(
            execution_id=request.execution_id,
            provider_execution_id=external_id,
            status="completed",
        )

    async def get_status(self, external_run_id: str) -> AutomationRunStatus:
        return self._runs.get(
            external_run_id,
            AutomationRunStatus(status="failed", error=f"Run {external_run_id} not found"),
        )

    async def cancel(self, external_run_id: str) -> None:
        if external_run_id in self._runs:
            self._runs[external_run_id].status = "cancelled"

    async def list_capabilities(self) -> list[str]:
        return [
            "system.telegram_notification",
            "system.email_notification",
            "sales.lead_ingest",
            "sales.followup_email",
            "marketing.publish_social",
        ]
