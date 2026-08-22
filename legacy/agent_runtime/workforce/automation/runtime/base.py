from abc import ABC, abstractmethod
from typing import Optional

from workforce.automation.runtime.types import (
    AutomationHealth,
    AutomationRequest,
    AutomationRunStatus,
    AutomationStartResult,
)


class AutomationProvider(ABC):
    """Abstract interface isolating COSA from external automation execution engines (n8n, mock)."""

    @abstractmethod
    async def health(self) -> AutomationHealth:
        """Check connection health and status with the automation provider."""
        ...

    @abstractmethod
    async def execute(self, request: AutomationRequest) -> AutomationStartResult:
        """Trigger an asynchronous automation workflow."""
        ...

    @abstractmethod
    async def get_status(self, external_run_id: str) -> AutomationRunStatus:
        """Poll the execution status of a running automation."""
        ...

    @abstractmethod
    async def cancel(self, external_run_id: str) -> None:
        """Cancel a running automation on the external engine."""
        ...

    @abstractmethod
    async def list_capabilities(self) -> list[str]:
        """List supported automation capabilities and integrations."""
        ...
