from abc import ABC, abstractmethod
from typing import List, Optional

from app.workforce.agents.execution.types import (
    ExecutionHealth,
    ExecutionStepResult,
    SandboxPolicy,
)


class ExecutionProvider(ABC):
    """Abstract interface isolating COSA business domain from code execution sandboxes."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier of this execution provider (e.g. 'mock', 'opensandbox')."""
        ...

    @abstractmethod
    async def create_workspace(
        self,
        policy: SandboxPolicy,
        metadata: Optional[dict] = None,
        env: Optional[dict] = None,
    ) -> str:
        """Create an ephemeral sandbox instance and return its sandbox_id."""
        ...

    @abstractmethod
    async def execute(
        self,
        sandbox_id: str,
        command: str,
        timeout_seconds: int,
    ) -> ExecutionStepResult:
        """Run a command inside the specified sandbox."""
        ...

    @abstractmethod
    async def upload_file(self, sandbox_id: str, path: str, data: bytes) -> None:
        """Upload raw file content to the sandbox filesystem."""
        ...

    @abstractmethod
    async def download_file(self, sandbox_id: str, path: str) -> bytes:
        """Download raw file content from the sandbox filesystem."""
        ...

    @abstractmethod
    async def list_outputs(self, sandbox_id: str, prefix: str = "/output") -> List[str]:
        """List relative or absolute paths under output directory."""
        ...

    @abstractmethod
    async def terminate(self, sandbox_id: str) -> None:
        """Terminate and destroy the sandbox container."""
        ...

    @abstractmethod
    async def health(self) -> ExecutionHealth:
        """Report execution provider health and availability."""
        ...
