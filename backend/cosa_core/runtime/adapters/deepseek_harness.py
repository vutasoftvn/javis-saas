import asyncio
import json
import logging
import os
import queue
import threading
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional

from cosa_core.governance.budget import BudgetTracker
from cosa_core.governance.models import AgentRun
from cosa_core.governance.stuck_detector import StuckDetector
from cosa_core.runtime.base import AgentRuntime
from cosa_core.runtime.errors import AgentErrorCode, AgentRuntimeError
from cosa_core.runtime.execution_scope import ExecutionScope
from cosa_core.runtime.json_output import parse_structured_output, parse_tool_calls
from cosa_core.runtime.tool_bridge import dispatch_tool_call
from cosa_core.runtime.types import (
    AgentEvent,
    AgentRunRequest,
    AgentRunResult,
    RuntimeHealth,
)
from cosa_core.feature_flags import FLAG_AGENT_RUNTIME_TOOLS, is_enabled
from cosa_core.snowflake import generate_snowflake_str
from db.session import SessionLocal

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

    def _create_harness_instance(self):
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
            harness = self._create_harness_instance()
        except AgentRuntimeError as err:
            self._record_event(run_id, "error", {"error": err.message})
            err.run_id = run_id
            raise

        self._active_harnesses[run_id] = harness
        self._record_event(run_id, "thought", {"thought": f"Dispatching to DeepSeek Harness runtime for {request.agent_key}"})

        # Check if tool execution loop is enabled for this workspace
        # Deferred import: app.core.toolset_resolver imports ExecutionScope from
        # this package's runtime/__init__.py, which eagerly imports this adapter
        # module - a top-level import here would be circular.
        from core.toolset_resolver import get_workspace_company_stage, resolve_toolset

        db = SessionLocal()
        try:
            ws_id = int(request.workspace_id) if request.workspace_id else None
            tools_flag_enabled = (
                request.context.get("enable_tools", False)
                or (ws_id is not None and is_enabled(db, FLAG_AGENT_RUNTIME_TOOLS, ws_id))
            )
            
            allowed_specs = []
            if tools_flag_enabled and ws_id is not None:
                company_stage = get_workspace_company_stage(db, ws_id)
                execution_scope = ExecutionScope(
                    workspace_id=ws_id,
                    company_id=(
                        int(request.company_id)
                        if request.company_id
                        else ws_id
                    ),
                    principal_user_id=(
                        int(request.user_id) if request.user_id else 0
                    ),
                    principal_member_id=(
                        int(request.user_id) if request.user_id else 0
                    ),
                    principal_role="agent",
                    operating_unit_id=None,
                    offering_id=None,
                    initiative_id=None,
                    profile_id=None,
                    session_id=None,
                    grants=(),
                )
                allowed_specs = resolve_toolset(
                    db,
                    ws_id,
                    agent_key=request.agent_key,
                    company_stage=company_stage,
                    execution_scope=execution_scope,
                )

            if not tools_flag_enabled or not allowed_specs:
                # Single-shot execution without tool loop
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

            # Tool execution loop (max 6 turns).
            #
            # AgentToolCall.run_id has a FK to agent_runs.id, and Budget/Stuck checks read
            # AgentToolCall by run_id - so tool dispatch must use a run_id that actually has
            # an AgentRun row, not the adapter's own trace id minted above. When the caller
            # already created one (chief_of_staff.py sets parent_run_id=str(mission_id)
            # before calling us), reuse it; otherwise (e.g. a direct POST /agents/run caller)
            # create a minimal one now so governance has something real to attach to.
            mission_run_id = int(request.parent_run_id) if request.parent_run_id else int(run_id)
            agent_run = db.get(AgentRun, mission_run_id)
            if agent_run is None:
                agent_run = AgentRun(
                    id=mission_run_id,
                    workspace_id=ws_id,
                    company_id=int(request.company_id) if request.company_id else ws_id,
                    user_id=int(request.user_id),
                    agent_key=request.agent_key,
                    runtime=self.runtime_name,
                    status="running",
                    permission_profile=request.permission_profile,
                    started_at=datetime.now(timezone.utc),
                )
                db.add(agent_run)
                db.commit()

            tool_schemas = [s.to_openai_spec() for s in allowed_specs]
            tool_prompt_header = (
                f"You are agent '{request.agent_key}'. You have access to the following tools:\n"
                f"{json.dumps(tool_schemas, ensure_ascii=False, indent=2)}\n\n"
                "When you need to call a tool, respond with JSON format:\n"
                '{"tool_call": {"name": "<flat_tool_name>", "arguments": {<args>}}}\n\n'
                "When you have the final answer, respond with:\n"
                '{"final": "<your answer>"}\n\n'
                f"Task:\n{request.task}"
            )

            await asyncio.to_thread(harness.start)
            session = harness.start_session()
            accumulated_tool_calls: list[dict[str, Any]] = []
            pending_approvals: list[dict[str, Any]] = []
            current_prompt = tool_prompt_header
            final_output = ""
            finish_reason = "completed"
            session_id = None

            try:
                for turn in range(6):
                    if run_id in self._cancelled_runs:
                        self._record_event(run_id, "cancelled")
                        return AgentRunResult(
                            run_id=run_id,
                            runtime=self.runtime_name,
                            agent_key=request.agent_key,
                            status="cancelled",
                            output_text="DeepSeek Harness run was cancelled",
                        )

                    budget_check = BudgetTracker.check(db, agent_run, current_step=turn)
                    if budget_check.is_exceeded:
                        agent_run.status = "failed"
                        agent_run.error_code = budget_check.reason_code
                        agent_run.error_message = budget_check.message
                        agent_run.finished_at = datetime.now(timezone.utc)
                        db.commit()
                        self._record_event(run_id, "error", {"error": budget_check.message, "code": budget_check.reason_code})
                        return AgentRunResult(
                            run_id=run_id,
                            runtime=self.runtime_name,
                            agent_key=request.agent_key,
                            status="failed",
                            output_text=budget_check.message,
                            structured_output={"finish_reason": "budget_exceeded", "reason_code": budget_check.reason_code},
                            tool_calls=accumulated_tool_calls,
                            metrics={"model": self._model_name, "turns": turn},
                        )

                    stuck_check = StuckDetector.analyze_run(db, mission_run_id)
                    if stuck_check.is_stuck and stuck_check.suggested_action == "ABORT_RUN":
                        agent_run.status = "failed"
                        agent_run.error_code = "STUCK_LOOP"
                        agent_run.error_message = stuck_check.detail
                        agent_run.finished_at = datetime.now(timezone.utc)
                        db.commit()
                        self._record_event(run_id, "error", {"error": stuck_check.detail, "code": "STUCK_LOOP"})
                        return AgentRunResult(
                            run_id=run_id,
                            runtime=self.runtime_name,
                            agent_key=request.agent_key,
                            status="failed",
                            output_text=stuck_check.detail,
                            structured_output={"finish_reason": "stuck_loop", "loop_type": stuck_check.loop_type},
                            tool_calls=accumulated_tool_calls,
                            metrics={"model": self._model_name, "turns": turn},
                        )
                    if stuck_check.is_stuck and stuck_check.suggested_action == "WARN_CHANGE_STRATEGY":
                        self._record_event(run_id, "thought", {"warning": stuck_check.detail, "code": "WARN_CHANGE_STRATEGY"})
                        current_prompt = (
                            f"NOTICE: {stuck_check.detail} Change your approach - do not repeat the same "
                            f"tool call again.\n\n{current_prompt}"
                        )

                    turn_result = await asyncio.to_thread(session.run, current_prompt)
                    session_id = turn_result.session_id
                    response_text = turn_result.final_response or ""
                    finish_reason = turn_result.finish_reason

                    calls = parse_tool_calls(response_text)
                    if not calls:
                        parsed_struct = parse_structured_output(response_text)
                        if parsed_struct and "final" in parsed_struct:
                            final_output = str(parsed_struct["final"])
                        else:
                            final_output = response_text
                        break

                    # Dispatch tool calls
                    tool_results = []
                    awaiting_approval = False
                    for call in calls:
                        tc_name = call["name"]
                        tc_args = call["arguments"]

                        self._record_event(
                            run_id,
                            "tool_call_started",
                            {"tool": tc_name, "arguments": tc_args},
                        )

                        tool_res = await dispatch_tool_call(
                            db=db,
                            request=request,
                            tool_flat_name=tc_name,
                            args=tc_args,
                            run_id=mission_run_id,
                        )

                        accumulated_tool_calls.append({
                            "tool": tc_name,
                            "input": tc_args,
                            "output": tool_res,
                        })

                        self._record_event(
                            run_id,
                            "tool_call_completed",
                            {"tool": tc_name, "output": tool_res},
                        )

                        if isinstance(tool_res, dict) and tool_res.get("status") == "awaiting_approval":
                            self._record_event(
                                run_id,
                                "approval_required",
                                {"tool": tc_name, "approval_id": tool_res.get("approval_id")},
                            )
                            pending_approvals.append({
                                "approval_id": tool_res.get("approval_id"),
                                "tool_name": tool_res.get("tool_name", tc_name),
                                "status": "pending",
                            })
                            awaiting_approval = True
                            tool_results.append(f"Tool '{tc_name}' requires human approval (Approval ID: {tool_res.get('approval_id')}). Execution paused.")
                        else:
                            tool_results.append(f"Tool '{tc_name}' output: {json.dumps(tool_res, ensure_ascii=False)}")

                    if awaiting_approval:
                        return AgentRunResult(
                            run_id=run_id,
                            runtime=self.runtime_name,
                            runtime_session_id=session_id,
                            agent_key=request.agent_key,
                            status="awaiting_approval",
                            output_text="Action requires human approval before proceeding.",
                            structured_output={"finish_reason": "awaiting_approval"},
                            tool_calls=accumulated_tool_calls,
                            approvals=pending_approvals,
                            metrics={"model": self._model_name, "turns": turn + 1},
                        )

                    current_prompt = "Tool execution results:\n" + "\n".join(tool_results) + "\n\nProceed with the task or provide final response."
                else:
                    final_output = response_text
            finally:
                await asyncio.to_thread(harness.close)
                self._active_harnesses.pop(run_id, None)

            self._record_event(
                run_id,
                "run_completed",
                {"output": final_output, "finish_reason": finish_reason},
            )

            return AgentRunResult(
                run_id=run_id,
                runtime=self.runtime_name,
                runtime_session_id=session_id,
                agent_key=request.agent_key,
                status="completed" if finish_reason == "completed" else "partial",
                output_text=final_output,
                structured_output={"finish_reason": finish_reason},
                tool_calls=accumulated_tool_calls,
                approvals=pending_approvals,
                metrics={"model": self._model_name},
            )
        finally:
            db.close()

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
            harness = self._create_harness_instance()
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
