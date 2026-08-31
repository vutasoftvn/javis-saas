"""RunExecutionService — narrower interface for run execution concerns."""

from __future__ import annotations

from typing import Any

from agent.contracts.kernel import ExecutionKernel
from agent.runs.repository import RunRepository


class RunExecutionService:
    """Encapsulates run-related dependencies (kernel, repository, lease, scheduler)."""

    def __init__(
        self,
        kernel: ExecutionKernel,
        repository: RunRepository,
        lease_client: Any,
        scheduler: Any,
    ) -> None:
        self.kernel = kernel
        self.repository = repository
        self.lease_client = lease_client
        self.scheduler = scheduler


class IRunExecutionService:
    """Public interface for consumers — type hint only, no runtime inheritance required."""

    kernel: ExecutionKernel
    repository: RunRepository
    lease_client: Any
    scheduler: Any
