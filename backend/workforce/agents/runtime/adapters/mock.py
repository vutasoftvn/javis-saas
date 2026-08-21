import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from workforce.agents.runtime.base import AgentRuntime
from workforce.agents.runtime.errors import AgentErrorCode, AgentRuntimeError
from workforce.agents.runtime.types import (
    AgentEvent,
    AgentRunRequest,
    AgentRunResult,
    RuntimeHealth,
)
from core.snowflake import generate_snowflake_str


class MockRuntime(AgentRuntime):
    """Deterministic Mock Runtime for unit tests, contract tests, and local simulation."""

    def __init__(self) -> None:
        self._traces: dict[str, list[AgentEvent]] = {}
        self._cancelled_runs: set[str] = set()
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._is_healthy: bool = True

    @property
    def runtime_name(self) -> str:
        return "mock"

    def set_healthy(self, healthy: bool) -> None:
        self._is_healthy = healthy

    async def health(self) -> RuntimeHealth:
        if not self._is_healthy:
            return RuntimeHealth(
                status="unavailable",
                runtime_name=self.runtime_name,
                version="1.0.0",
                details={"error": "Mock runtime set to unhealthy"},
            )
        return RuntimeHealth(
            status="healthy",
            runtime_name=self.runtime_name,
            version="1.0.0",
            details={"active_runs": len(self._active_tasks)},
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

    async def _execute_internal(self, run_id: str, request: AgentRunRequest) -> AgentRunResult:
        if not self._is_healthy or request.context.get("simulate_crash"):
            self._record_event(run_id, "error", {"error": "Runtime crashed"})
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_RUNTIME_UNAVAILABLE,
                message="Mock runtime crashed or is unavailable",
                run_id=run_id,
            )

        if request.context.get("simulate_error"):
            err_code = request.context.get("error_code", AgentErrorCode.AGENT_TOOL_ERROR)
            msg = request.context.get("error_message", "Simulated tool error")
            self._record_event(run_id, "error", {"code": err_code, "message": msg})
            raise AgentRuntimeError(
                code=err_code,
                message=msg,
                run_id=run_id,
            )

        self._record_event(run_id, "run_started", {"agent_key": request.agent_key, "task": request.task})
        await asyncio.sleep(0.01)

        if run_id in self._cancelled_runs:
            self._record_event(run_id, "cancelled")
            return AgentRunResult(
                run_id=run_id,
                runtime=self.runtime_name,
                agent_key=request.agent_key,
                status="cancelled",
                output_text="Execution was cancelled",
            )

        # Simulate sleep if requested
        sleep_duration = request.context.get("sleep_seconds", 0)
        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)

        if run_id in self._cancelled_runs:
            self._record_event(run_id, "cancelled")
            return AgentRunResult(
                run_id=run_id,
                runtime=self.runtime_name,
                agent_key=request.agent_key,
                status="cancelled",
                output_text="Execution was cancelled",
            )

        self._record_event(run_id, "thought", {"thought": f"Analyzing task: {request.task}"})

        tool_calls = []
        if request.context.get("simulate_tools"):
            self._record_event(run_id, "tool_call_started", {"tool": "mock_read_data"})
            tool_calls.append({"tool": "mock_read_data", "input": {}, "output": {"result": "ok"}})
            self._record_event(run_id, "tool_call_completed", {"tool": "mock_read_data", "output": {"result": "ok"}})

        if request.context.get("simulate_approval_required"):
            self._record_event(run_id, "approval_required", {"action": "execute_high_risk_action"})
            return AgentRunResult(
                run_id=run_id,
                runtime=self.runtime_name,
                agent_key=request.agent_key,
                status="awaiting_approval",
                output_text="Waiting for approval",
                approvals=[{"action": "execute_high_risk_action", "status": "pending"}],
            )

        self._record_event(run_id, "run_completed", {"output": f"Completed task: {request.task}"})

        return AgentRunResult(
            run_id=run_id,
            runtime=self.runtime_name,
            runtime_session_id=f"session_{run_id}",
            agent_key=request.agent_key,
            status="completed",
            output_text=f"Processed by mock runtime for agent '{request.agent_key}': {request.task}",
            structured_output=request.context.get("structured_output", {"status": "ok"}),
            tool_calls=tool_calls,
            metrics={"duration_ms": 15},
        )

    async def run(self, request: AgentRunRequest) -> AgentRunResult:
        run_id = generate_snowflake_str()
        timeout = request.timeout_seconds or 600

        task = asyncio.create_task(self._execute_internal(run_id, request))
        self._active_tasks[run_id] = task

        try:
            result = await asyncio.wait_for(task, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self._record_event(run_id, "error", {"code": AgentErrorCode.AGENT_RUNTIME_TIMEOUT})
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_RUNTIME_TIMEOUT,
                message=f"Agent run exceeded timeout limit of {timeout}s",
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
                output_text="Execution was cancelled",
            )
        except Exception as exc:
            self._record_event(run_id, "error", {"error": str(exc)})
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_UNKNOWN_ERROR,
                message=f"Unexpected error in runtime: {exc}",
                run_id=run_id,
            )
        finally:
            self._active_tasks.pop(run_id, None)

    async def stream(self, request: AgentRunRequest) -> AsyncIterator[AgentEvent]:
        run_id = generate_snowflake_str()

        if not self._is_healthy or request.context.get("simulate_crash"):
            event = self._record_event(run_id, "error", {"error": "Runtime crashed"})
            yield event
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_RUNTIME_UNAVAILABLE,
                message="Mock runtime crashed or is unavailable",
                run_id=run_id,
            )

        yield self._record_event(run_id, "run_started", {"agent_key": request.agent_key})
        await asyncio.sleep(0.01)

        yield self._record_event(run_id, "thought", {"thought": "Planning execution"})
        await asyncio.sleep(0.01)

        if request.context.get("simulate_tools"):
            yield self._record_event(run_id, "tool_call_started", {"tool": "mock_read_data"})
            await asyncio.sleep(0.01)
            yield self._record_event(run_id, "tool_call_completed", {"tool": "mock_read_data"})

        yield self._record_event(run_id, "run_completed", {"output": "Finished"})

    async def resume(self, session_id: str, request: AgentRunRequest) -> AgentRunResult:
        run_id = generate_snowflake_str()
        self._record_event(run_id, "run_resumed", {"session_id": session_id})
        return AgentRunResult(
            run_id=run_id,
            runtime=self.runtime_name,
            runtime_session_id=session_id,
            agent_key=request.agent_key,
            status="completed",
            output_text=f"Resumed session {session_id} for agent {request.agent_key}",
        )

    async def cancel(self, run_id: str) -> None:
        self._cancelled_runs.add(run_id)
        task = self._active_tasks.get(run_id)
        if task and not task.done():
            task.cancel()
        self._record_event(run_id, "cancelled")

    async def get_trace(self, run_id: str) -> list[AgentEvent]:
        return self._traces.get(run_id, [])
