import asyncio
import queue
import threading
from datetime import datetime, timezone
import logging
import os
from typing import Any, AsyncIterator, Optional

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

_SDK_MODULE_NAME = "deepseek_harness"


class DeepSeekHarnessAdapter(AgentRuntime):
    """Adapter wrapping the real `deepseek-harness-sdk` (PyPI, Developer Preview)
    behind the COSA AgentRuntime interface.

    The SDK drives a bundled subprocess (`deepseek-harness-runtime-bin`) over
    JSON-RPC stdio and is entirely synchronous, so every call into it runs on a
    worker thread via `asyncio.to_thread`/a dedicated thread to avoid blocking
    the FastAPI event loop. `resume`/`fork` are not implemented yet: resuming a
    prior session correctly depends on wiring `session_root` persistence, which
    is out of scope for the Phase 1 spike (see adjustment plan Phase 1 notes).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: str = "deepseek-v4-flash",
        max_tokens: Optional[int] = 4096,
    ) -> None:
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self._base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self._model_name = model_name
        # Omitting max_tokens leaves the harness's own per-provider default in control,
        # which for deepseek-official is large enough to blow past a routed model's real
        # context window (verified live: 256000 vs OpenRouter's 163840 cap -> the run
        # fails with CONTEXT_WINDOW_EXCEEDED before it ever reaches the model). Capping it
        # here keeps the adapter usable against any downstream provider/model.
        self._max_tokens = max_tokens
        self._traces: dict[str, list[AgentEvent]] = {}
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._active_harnesses: dict[str, Any] = {}
        self._cancelled_runs: set[str] = set()

    @property
    def runtime_name(self) -> str:
        return "deepseek_harness"

    async def health(self) -> RuntimeHealth:
        """Cheap health check: config + SDK importability only.

        Does not spawn the runtime subprocess (that only happens on `run`), so
        this is safe to call frequently without launching real processes or
        touching the network.
        """
        if not self._api_key:
            return RuntimeHealth(
                status="unavailable",
                runtime_name=self.runtime_name,
                version="0.1.0rc6",
                details={"error": "DEEPSEEK_API_KEY is not configured"},
            )
        try:
            import importlib.util

            if importlib.util.find_spec(_SDK_MODULE_NAME) is None:
                return RuntimeHealth(
                    status="unavailable",
                    runtime_name=self.runtime_name,
                    version="0.1.0rc6",
                    details={"error": "deepseek-harness-sdk is not installed"},
                )
        except Exception as exc:
            logger.warning(f"[DeepSeekHarness] Health check failed: {exc}")
            return RuntimeHealth(
                status="unavailable",
                runtime_name=self.runtime_name,
                version="0.1.0rc6",
                details={"error": str(exc)},
            )

        return RuntimeHealth(
            status="healthy",
            runtime_name=self.runtime_name,
            version="0.1.0rc6",
            details={
                "model": self._model_name,
                "base_url": self._base_url,
                "active_runs": len(self._active_tasks),
            },
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

    def _import_sdk(self):
        try:
            from deepseek_harness import DeepSeekHarness, DeepSeekHarnessConfig
        except ImportError as exc:
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_RUNTIME_UNAVAILABLE,
                message=f"deepseek-harness-sdk chưa được cài đặt: {exc}",
            ) from exc
        return DeepSeekHarness, DeepSeekHarnessConfig

    def _new_harness(self):
        DeepSeekHarness, DeepSeekHarnessConfig = self._import_sdk()
        config = DeepSeekHarnessConfig(
            api_key=self._api_key,
            base_url=self._base_url,
            model=self._model_name,
            max_tokens=self._max_tokens,
        )
        return DeepSeekHarness(config)

    @staticmethod
    def _run_harness_sync(harness, task: str):
        harness.start()
        try:
            return harness.run(task)
        finally:
            harness.close()

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
            harness = self._new_harness()
        except AgentRuntimeError as err:
            self._record_event(run_id, "error", {"error": err.message})
            err.run_id = run_id
            raise

        self._active_harnesses[run_id] = harness
        self._record_event(run_id, "thought", {"thought": f"Dispatching to DeepSeek Harness runtime for {request.agent_key}"})

        try:
            result = await asyncio.to_thread(self._run_harness_sync, harness, request.task)
        except Exception as exc:
            if run_id in self._cancelled_runs:
                self._record_event(run_id, "cancelled")
                return AgentRunResult(
                    run_id=run_id,
                    runtime=self.runtime_name,
                    agent_key=request.agent_key,
                    status="cancelled",
                    output_text="DeepSeek Harness run was cancelled",
                )
            logger.error(f"[DeepSeekHarness] Execution failed: {exc}")
            self._record_event(run_id, "error", {"error": str(exc)})
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_MODEL_ERROR,
                message=f"DeepSeek Harness execution error: {exc}",
                retryable=True,
                run_id=run_id,
            )
        finally:
            self._active_harnesses.pop(run_id, None)

        self._record_event(
            run_id,
            "run_completed",
            {"output": result.final_response, "finish_reason": result.finish_reason},
        )

        return AgentRunResult(
            run_id=run_id,
            runtime=self.runtime_name,
            runtime_session_id=result.session_id,
            agent_key=request.agent_key,
            status="completed" if result.finish_reason == "completed" else "partial",
            output_text=result.final_response,
            structured_output={"finish_reason": result.finish_reason},
            tool_calls=[],
            metrics={"model": self._model_name},
        )

    async def run(self, request: AgentRunRequest) -> AgentRunResult:
        run_id = generate_snowflake_str()
        timeout = request.timeout_seconds or 600

        task = asyncio.create_task(self._execute_harness(run_id, request))
        self._active_tasks[run_id] = task

        try:
            return await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            await self.cancel(run_id)
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
        """Bridge the SDK's synchronous notification callback onto an async
        generator via a thread-safe queue, so streamed events reflect the real
        JSON-RPC notifications from the harness subprocess rather than
        synthetic placeholders.
        """
        run_id = generate_snowflake_str()

        if not self._api_key:
            yield self._record_event(run_id, "error", {"error": "Missing API Key"})
            raise AgentRuntimeError(
                code=AgentErrorCode.AGENT_RUNTIME_UNAVAILABLE,
                message="DeepSeek Harness is unavailable: DEEPSEEK_API_KEY is not configured",
                run_id=run_id,
            )

        try:
            harness = self._new_harness()
        except AgentRuntimeError as err:
            yield self._record_event(run_id, "error", {"error": err.message})
            err.run_id = run_id
            raise

        self._active_harnesses[run_id] = harness
        yield self._record_event(run_id, "run_started", {"agent_key": request.agent_key})

        notification_queue: "queue.Queue[object]" = queue.Queue()
        _DONE = object()

        def on_notification(notification) -> None:
            notification_queue.put(notification)

        def run_blocking() -> None:
            try:
                harness.start()
                result = harness.run(request.task, on_notification=on_notification)
                notification_queue.put(("__result__", result))
            except Exception as exc:  # noqa: BLE001 - surfaced to the async side below
                notification_queue.put(("__error__", exc))
            finally:
                notification_queue.put(_DONE)
                harness.close()

        worker = threading.Thread(target=run_blocking, daemon=True)
        worker.start()

        try:
            while True:
                item = await asyncio.to_thread(notification_queue.get)
                if item is _DONE:
                    break
                if isinstance(item, tuple) and item[0] == "__error__":
                    exc = item[1]
                    if run_id in self._cancelled_runs:
                        yield self._record_event(run_id, "cancelled")
                        return
                    yield self._record_event(run_id, "error", {"error": str(exc)})
                    raise AgentRuntimeError(
                        code=AgentErrorCode.AGENT_MODEL_ERROR,
                        message=f"DeepSeek Harness stream error: {exc}",
                        retryable=True,
                        run_id=run_id,
                    )
                if isinstance(item, tuple) and item[0] == "__result__":
                    result = item[1]
                    yield self._record_event(
                        run_id,
                        "run_completed",
                        {"output": result.final_response, "finish_reason": result.finish_reason},
                    )
                    continue
                yield self._record_event(
                    run_id,
                    "harness_notification",
                    {"method": item.method, "payload": item.payload},
                )
        finally:
            self._active_harnesses.pop(run_id, None)

    async def resume(self, session_id: str, request: AgentRunRequest) -> AgentRunResult:
        raise NotImplementedError(
            "resume is not supported yet on runtime 'deepseek_harness': needs session_root "
            "persistence wiring beyond the Phase 1 spike scope"
        )

    async def cancel(self, run_id: str) -> None:
        self._cancelled_runs.add(run_id)
        harness = self._active_harnesses.get(run_id)
        if harness is not None:
            await asyncio.to_thread(harness.close)
        task = self._active_tasks.get(run_id)
        if task and not task.done():
            task.cancel()
        self._record_event(run_id, "cancelled")

    async def get_trace(self, run_id: str) -> list[AgentEvent]:
        return self._traces.get(run_id, [])
