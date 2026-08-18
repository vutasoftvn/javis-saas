import logging
from typing import Optional

from app.workforce.agents.runtime.base import AgentRuntime
from app.workforce.agents.runtime.adapters.mock import MockRuntime
from app.workforce.agents.runtime.adapters.deepseek_harness import DeepSeekHarnessAdapter
from app.workforce.agents.runtime.errors import AgentErrorCode, AgentRuntimeError

logger = logging.getLogger(__name__)


class AgentRuntimeManager:
    """Manages lifecycle and resolution of AgentRuntime adapters."""

    def __init__(self) -> None:
        self._runtimes: dict[str, AgentRuntime] = {}
        self._is_started: bool = False

    def register(self, runtime: AgentRuntime) -> None:
        self._runtimes[runtime.runtime_name] = runtime
        logger.info(f"[AgentRuntimeManager] Registered runtime: '{runtime.runtime_name}'")

    async def start(self) -> None:
        if self._is_started:
            return
        
        # Register default built-in runtimes
        if "mock" not in self._runtimes:
            self.register(MockRuntime())
        if "deepseek_harness" not in self._runtimes:
            self.register(DeepSeekHarnessAdapter())

        self._is_started = True
        logger.info("[AgentRuntimeManager] Initialized and started successfully.")

    async def stop(self) -> None:
        self._is_started = False
        self._runtimes.clear()
        logger.info("[AgentRuntimeManager] Stopped and cleared runtimes.")

    def get_runtime(self, runtime_name: Optional[str] = None) -> AgentRuntime:
        name = runtime_name or "mock"
        if name not in self._runtimes:
            # Fallback to mock if not found
            if "mock" in self._runtimes:
                return self._runtimes["mock"]
            mock = MockRuntime()
            self.register(mock)
            return mock
        return self._runtimes[name]

    def list_runtimes(self) -> list[str]:
        return list(self._runtimes.keys())


# Singleton instance across application
agent_runtime_manager = AgentRuntimeManager()
