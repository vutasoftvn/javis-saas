"""Interface adapter contract for AgentRuntime — enables adding new runtime implementations
without modifying cosa_core.runtime.manager."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from cosa_core.runtime.types import (
    AgentEvent,
    AgentRunRequest,
    AgentRunResult,
    RuntimeHealth,
)


class RuntimeAdapterContract(ABC):
    """Contract that every runtime adapter (DeepSeek Harness, and future runtimes)
    must implement to be compatible with cosa_core.runtime.manager."""

    @property
    @abstractmethod
    def runtime_name(self) -> str:
        """Identifier of this runtime adapter (e.g. 'mock', 'deepseek_harness')."""
        ...

    @abstractmethod
    async def run(self, request: AgentRunRequest) -> AgentRunResult:
        """Execute an agent request synchronously to completion."""
        ...

    @abstractmethod
    async def stream(self, request: AgentRunRequest) -> AsyncIterator[AgentEvent]:
        """Stream events during agent execution."""
        ...

    @abstractmethod
    async def resume(self, session_id: str, request: AgentRunRequest) -> AgentRunResult:
        """Resume an awaiting or paused agent session."""
        ...

    @abstractmethod
    async def cancel(self, run_id: str) -> None:
        """Cancel an in-flight agent run."""
        ...

    @abstractmethod
    async def get_trace(self, run_id: str) -> list[AgentEvent]:
        """Retrieve recorded trace events for a given run ID."""
        ...

    async def fork(self, session_id: str, from_event_id: Optional[str] = None) -> str:
        """Fork an execution session. Optional until adapter confirms support."""
        raise NotImplementedError(f"Fork is not supported on this runtime")

    @abstractmethod
    async def health(self) -> RuntimeHealth:
        """Report runtime availability and health status."""
        ...
