from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from app.workforce.agents.runtime.types import (
    AgentEvent,
    AgentRunRequest,
    AgentRunResult,
    RuntimeHealth,
)


class AgentRuntime(ABC):
    """Abstract interface isolating COSA business domain from agent execution runtimes."""

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
        raise NotImplementedError(f"Fork is not supported on runtime '{self.runtime_name}'")

    @abstractmethod
    async def health(self) -> RuntimeHealth:
        """Report runtime availability and health status."""
        ...
