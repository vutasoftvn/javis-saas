import logging
import os
from typing import Dict, List, Optional

from app.agents.execution.adapters.mock import MockExecutor
from app.agents.execution.adapters.opensandbox import OpenSandboxExecutor
from app.agents.execution.base import ExecutionProvider
from app.agents.execution.errors import ExecutionErrorCode, ExecutionRuntimeError

logger = logging.getLogger(__name__)


class ExecutionProviderManager:
    """Manages lifecycle and resolution of ExecutionProvider adapters."""

    def __init__(self) -> None:
        self._providers: Dict[str, ExecutionProvider] = {}
        self._is_started: bool = False

    def register(self, provider: ExecutionProvider) -> None:
        self._providers[provider.provider_name] = provider
        logger.info(f"[ExecutionProviderManager] Registered execution provider: '{provider.provider_name}'")

    async def start(self) -> None:
        if self._is_started:
            return

        if "mock" not in self._providers:
            self.register(MockExecutor())
        if "opensandbox" not in self._providers:
            self.register(OpenSandboxExecutor())

        self._is_started = True
        logger.info("[ExecutionProviderManager] Initialized and started successfully.")

    async def stop(self) -> None:
        # Terminate any remaining active resources if needed
        self._is_started = False
        self._providers.clear()
        logger.info("[ExecutionProviderManager] Stopped and cleared execution providers.")

    def get(self, provider_name: Optional[str] = None) -> ExecutionProvider:
        """Resolve an execution provider by name.
        
        CRITICAL: Bắt buộc raise ExecutionRuntimeError nếu provider không tồn tại (ADR-EXEC-002).
        Tuyệt đối không fallback im lặng về mock khi provider yêu cầu không khớp.
        """
        name = provider_name or os.environ.get("COSA_EXECUTION_PROVIDER", "mock")
        if name not in self._providers:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_PROVIDER_UNKNOWN,
                message=f"Execution provider '{name}' is not registered. Available providers: {list(self._providers.keys())}",
            )
        return self._providers[name]

    def list_providers(self) -> List[str]:
        return list(self._providers.keys())


# Global singleton instance
execution_provider_manager = ExecutionProviderManager()
