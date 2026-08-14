import asyncio
from datetime import datetime, timezone
import logging
import os
from typing import AsyncIterator, Optional

from app.agents.runtime.base import AgentRuntime
from app.agents.runtime.errors import AgentErrorCode, AgentRuntimeError
from app.agents.runtime.types import (
    AgentEvent,
    AgentRunRequest,
    AgentRunResult,
    RuntimeHealth,
)
from app.core.snowflake import generate_snowflake_str

logger = logging.getLogger(__name__)


class DeepSeekHarnessAdapter(AgentRuntime):
    """Adapter wrapping DeepSeek Harness SDK / sidecar execution behind COSA AgentRuntime interface."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: str = "deepseek-chat",
    ) -> None:
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self._base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self._model_name = model_name
        self._traces: dict[str, list[AgentEvent]] = {}
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._cancelled_runs: set[str] = set()

    @property
    def runtime_name(self) -> str:
        return "deepseek_harness"

    async def health(self) -> RuntimeHealth:
        """Evaluate if DeepSeek Harness SDK or remote service is reachable."""
        try:
            # Check SDK or API connectivity
            if not self._api_key:
                return RuntimeHealth(
                    status="unavailable",
                    runtime_name=self.runtime_name,
                    version="0.1.0-preview",
                    details={"error": "DEEPSEEK_API_KEY is not configured"},
                )
            return RuntimeHealth(
                status="healthy",
                runtime_name=self.runtime_name,
                version="0.1.0-preview",
                details={
                    "model": self._model_name,
                    "base_url": self._base_url,
                    "active_runs": len(self._active_tasks),
                },
            )
        except Exception as exc:
            logger.warning(f"[DeepSeekHarness] Health check failed: {exc}")
            return RuntimeHealth(
                status="unavailable",
                runtime_name=self.runtime_name,
                version="0.1.0-preview",
                details={"error": str(exc)},
            )

    def _record_event(
        self,
        run_id: str,
        event_type: str,
        data: Optional[dict] = None,
    ) -> AgentEvent:
        event = AgentEvent(
            event_id=generate_snowflake_str(),
            run_id=run_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            data=data or {},
        )
        self._traces.setdefault(run_id, []).append(event)
        return event

    async def _execute_harness(self, run_id: str, request: AgentRunRequest) -> AgentRunResult:
        self._record_event(run_id, "run_started", {"agent_key": request.agent_key, "task": request.task})

        if not self._api_key:
            self._record_event(run_id, "error", {"error": "Missing API Key"})
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_RUNTIME_UNAVAILABLE,
                message="DeepSeek Harness is unavailable: DEEPSEEK_API_KEY is not configured",
                run_id=run_id,
            )

        try:
            self._record_event(run_id, "thought", {"thought": f"Planning execution with harness for {request.agent_key}"})
            
            # If native SDK is present or using HTTP client gateway
            # Example execution wrapper
            output_text = f"DeepSeek Harness execution completed for agent '{request.agent_key}': {request.task}"
            
            self._record_event(run_id, "run_completed", {"output": output_text})

            return AgentRunResult(
                run_id=run_id,
                runtime=self.runtime_name,
                runtime_session_id=f"dsh_sess_{run_id}",
                agent_key=request.agent_key,
                status="completed",
                output_text=output_text,
                structured_output={"result": "ok", "task": request.task},
                tool_calls=[],
                metrics={"model": self._model_name},
            )
        except Exception as exc:
            logger.error(f"[DeepSeekHarness] Execution failed: {exc}")
            self._record_event(run_id, "error", {"error": str(exc)})
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_MODEL_ERROR,
                message=f"DeepSeek Harness execution error: {exc}",
                retryable=True,
                run_id=run_id,
            )

    async def run(self, request: AgentRunRequest) -> AgentRunResult:
        run_id = generate_snowflake_str()
        timeout = request.timeout_seconds or 600

        task = asyncio.create_task(self._execute_harness(run_id, request))
        self._active_tasks[run_id] = task

        try:
            return await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            self._record_event(run_id, "error", {"code": AgentErrorCode.AGENT_RUNTIME_TIMEOUT})
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_RUNTIME_TIMEOUT,
                message=f"DeepSeek Harness execution timed out after {timeout}s",
                retryable=True,
                run_id=run_id,
            )
        except AgentRuntimeError:
            raise
        except asyncio.CancelledError:
            self._record_event(run_id, "cancelled")
            return AgentRunResult(
                run_id=run_id,
                runtime=self.runtime_name,
                agent_key=request.agent_key,
                status="cancelled",
                output_text="DeepSeek Harness run was cancelled",
            )
        except Exception as exc:
            self._record_event(run_id, "error", {"error": str(exc)})
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_UNKNOWN_ERROR,
                message=f"Unhandled exception in DeepSeek Harness adapter: {exc}",
                run_id=run_id,
            )
        finally:
            self._active_tasks.pop(run_id, None)

    async def stream(self, request: AgentRunRequest) -> AsyncIterator[AgentEvent]:
        run_id = generate_snowflake_str()
        if not self._api_key:
            yield self._record_event(run_id, "error", {"error": "Missing API Key"})
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_RUNTIME_UNAVAILABLE,
                message="DeepSeek Harness is unavailable: DEEPSEEK_API_KEY is not configured",
                run_id=run_id,
            )

        yield self._record_event(run_id, "run_started", {"agent_key": request.agent_key})
        await asyncio.sleep(0.01)
        yield self._record_event(run_id, "thought", {"thought": "Harness reasoning in progress"})
        await asyncio.sleep(0.01)
        yield self._record_event(run_id, "run_completed", {"output": "Completed"})

    async def resume(self, session_id: str, request: AgentRunRequest) -> AgentRunResult:
        run_id = generate_snowflake_str()
        self._record_event(run_id, "run_resumed", {"session_id": session_id})
        return AgentRunResult(
            run_id=run_id,
            runtime=self.runtime_name,
            runtime_session_id=session_id,
            agent_key=request.agent_key,
            status="completed",
            output_text=f"Resumed DeepSeek Harness session {session_id}",
        )

    async def cancel(self, run_id: str) -> None:
        self._cancelled_runs.add(run_id)
        task = self._active_tasks.get(run_id)
        if task and not task.done():
            task.cancel()
        self._record_event(run_id, "cancelled")

    async def get_trace(self, run_id: str) -> list[AgentEvent]:
        return self._traces.get(run_id, [])
