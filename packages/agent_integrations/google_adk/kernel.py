from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncIterator, Callable, Optional

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types as genai_types

from agent_core.capabilities.canonicalization import compute_payload_hash
from agent_core.capabilities.gateway import GatewayExecutionRequest
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.contracts.capability import CapabilitySpec
from agent_core.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent_core.contracts.kernel import ExecutionKernel
from agent_core.contracts.run import RunRequest, RunResult, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.prompts.bundle import PromptBundle
from agent_core.registry.publisher import publish_agent_spec
from agent_core.registry.repository import InMemorySpecRegistryRepository, SpecRegistryRepository
from agent_core.skills.resolver import SkillResolver
from agent_core.runs.models import RunEventRecord, RunRecord, RunToolCallRecord
from agent_core.runs.repository import InMemoryRunRepository, RunRepository

__all__ = ["GoogleAdkKernel"]


class GoogleAdkKernel:
    """`ExecutionKernel` adapter dùng `google.adk.runners.Runner`/`LlmAgent`
    THẬT (package `google-adk==2.7.0`).

    **KHÔNG phải** `legacy/agent_runtime/workforce/agents/orchestration/adk/
    workflow.py::AdkCofounderWorkflow` — đó là 1 business pipeline production
    cụ thể (mission/task domain của COSA cofounder), không phải generic
    ExecutionKernel candidate; di chuyển/wrap nó vào đây là việc lớn riêng,
    cố ý KHÔNG làm ở Wave 10 (đúng audit A4/A13 trong
    COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md — production
    ADK vẫn ở nguyên vị trí legacy cho tới khi có lý do di chuyển thật). Kernel
    này chỉ dùng `LlmAgent` GENERIC của ADK để verify khả năng làm
    `ExecutionKernel` — tương tự cách `LangChainKernel`/`PydanticAIKernel`
    dùng `BaseChatModel`/`Agent` generic của framework tương ứng.

    **PHẠM VI CỐ Ý THU HẸP** (khác 2 kernel kia, ghi rõ thay vì giả vờ đủ):
    - Chỉ implement `run()` (basic response + tool call ALLOW-path). KHÔNG
      implement `resume()`/approval-pause đầy đủ — ADK dùng session-based
      state (`InMemorySessionService`/`DatabaseSessionService`) + event
      streaming (`Runner.run_async()` trả `AsyncGenerator[Event]`), khác hẳn
      mô hình serialize-state-đơn-giản (`to_json`/`from_json`) của
      OpenAI Agents SDK/PydanticAI — cần nghiên cứu sâu hơn về
      `resumability_config`/`FunctionTool(require_confirmation=...)` +
      `tool_context.request_confirmation()` trước khi implement đúng, việc
      này để lại cho lần hardening sau khi có nhu cầu thật.
    - `cancel()` raise `NotImplementedError` tường minh — không giả vờ hỗ trợ.
    """

    def __init__(
        self,
        *,
        repository: Optional[RunRepository] = None,
        spec_registry: Optional[SpecRegistryRepository] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        model: Optional[Any] = None,
        capability_executor: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._repo = repository or InMemoryRunRepository()
        self._spec_registry = spec_registry or InMemorySpecRegistryRepository()
        self._skill_resolver = SkillResolver(self._spec_registry)
        self._capability_registry = capability_registry
        self._model = model
        self._capability_executor = capability_executor
        self._session_service = InMemorySessionService()

    async def _emit_event(
        self, run_id: str, event_type: str, payload: dict[str, Any], correlation_id: Optional[str] = None
    ) -> None:
        await self._repo.append_event(
            RunEventRecord(run_id=run_id, event_type=event_type, payload=payload, correlation_id=correlation_id)
        )

    async def _execute_tool(self, tool_name: str, args: dict[str, Any], *, run_id: str, tool_call_id: str) -> Any:
        if self._capability_executor:
            try:
                if asyncio.iscoroutinefunction(self._capability_executor):
                    return await self._capability_executor(tool_name, args)
                return self._capability_executor(tool_name, args)
            except TypeError:
                req = GatewayExecutionRequest(
                    run_id=run_id, capability_id=tool_name, input_payload=args, tool_call_id=tool_call_id
                )
                if asyncio.iscoroutinefunction(self._capability_executor):
                    res = await self._capability_executor(req)
                else:
                    res = self._capability_executor(req)
                return res.output_payload if hasattr(res, "output_payload") else res
        return {"status": "success", "executed_tool": tool_name, "params": args}

    def _build_tools(self, spec: AgentSpec, run_id: str) -> list[FunctionTool]:
        if not self._capability_registry or not spec.capability_refs:
            return []
        tools: list[FunctionTool] = []
        for cap_id in spec.capability_refs:
            reg = self._capability_registry.get(cap_id)
            if not reg:
                continue
            tools.append(self._make_tool(reg.spec, run_id))
        return tools

    def _make_tool(self, cap_spec: CapabilitySpec, run_id: str) -> FunctionTool:
        # ADK inject `tool_context: ToolContext` nếu hàm khai báo tham số này
        # — `tool_context.function_call_id` chính là exact tool_call_id ADK
        # sinh ra cho lần gọi đang xử lý, PHẢI dùng lại nguyên vẹn (không tự
        # sinh id mới) — cùng invariant exact `(run_id, tool_call_id)` đã học
        # từ bug thật ở `OpenAIAgentsKernel._execute_tool` (Wave 4).
        async def _tool_fn(tool_context: ToolContext, **kwargs: Any) -> Any:
            call_id = tool_context.function_call_id or f"call_{uuid.uuid4().hex[:8]}"
            await self._emit_event(run_id, "tool.started", {"tool_call_id": call_id, "tool": cap_spec.id})
            result = await self._execute_tool(cap_spec.id, kwargs, run_id=run_id, tool_call_id=call_id)
            await self._emit_event(run_id, "tool.completed", {"tool_call_id": call_id, "result": result})

            tc_record = RunToolCallRecord(
                tool_call_id=call_id,
                run_id=run_id,
                capability_id=cap_spec.id,
                payload_hash=compute_payload_hash(kwargs),
                input_payload=kwargs,
                status="completed",
            )
            await self._repo.save_tool_call(tc_record)
            return result

        _tool_fn.__name__ = cap_spec.id.replace(".", "_")
        _tool_fn.__doc__ = cap_spec.description or ""
        return FunctionTool(_tool_fn)

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        run_id = request.run_id or f"run_{uuid.uuid4().hex[:16]}"
        correlation_id = request.correlation_id or run_id

        pinned_spec = spec if spec.definition_hash else spec.with_hash()
        await publish_agent_spec(pinned_spec, repository=self._spec_registry, publisher=request.principal)

        skill_texts: list[str] = []
        if spec.pinned_skills:
            resolved_skills = await self._skill_resolver.resolve(spec.pinned_skills)
            skill_texts = [s.instructions for s in resolved_skills if s.instructions]

        run_record = RunRecord(
            run_id=run_id,
            tenant_id=request.tenant_id,
            company_id=request.company_id,
            workspace_id=request.workspace_id,
            conversation_id=request.conversation_id,
            session_ref=request.session_ref,
            principal=request.principal,
            root_executable_id=spec.id,
            root_executable_kind="agent",
            root_executable_version=spec.version,
            root_definition_hash=pinned_spec.definition_hash,
            status=RunStatus.RUNNING,
            execution_mode=request.execution_mode,
            correlation_id=correlation_id,
            idempotency_key=request.idempotency_key,
            input_payload=request.input,
            model_policy=request.model_policy or spec.model_policy,
        )
        await self._repo.create_run(run_record)
        await self._emit_event(run_id, "run.started", {"principal": request.principal, "spec_id": spec.id}, correlation_id)

        system_prompt = PromptBundle(
            agent_instructions=spec.instructions,
            skill_instructions=skill_texts,
            locale=request.locale,
        ).render()

        tools = self._build_tools(spec, run_id)
        agent = LlmAgent(name=spec.id.replace(".", "_") or "agent", model=self._model, instruction=system_prompt, tools=tools)

        prompt_content = ""
        if request.input:
            prompt_content = request.input.get("prompt") or request.input.get("message") or json.dumps(request.input)

        app_name = f"cosa_{spec.id}"
        session = await self._session_service.create_session(app_name=app_name, user_id=request.principal or "system")
        runner = Runner(app_name=app_name, agent=agent, session_service=self._session_service)

        try:
            final_text: Optional[str] = None
            async for event in runner.run_async(
                user_id=request.principal or "system",
                session_id=session.id,
                new_message=genai_types.Content(role="user", parts=[genai_types.Part(text=str(prompt_content))]),
            ):
                if event.content:
                    await self._emit_event(
                        run_id, "message.delta", {"content": str(event.content), "role": event.author}, correlation_id
                    )
                if event.is_final_response() and event.content and event.content.parts:
                    final_text = event.content.parts[0].text
        except AgentRuntimeError:
            raise
        except Exception as exc:
            error = AgentRuntimeError(
                RuntimeErrorCode.MODEL_PROVIDER_ERROR,
                f"Google ADK run failed: {exc}",
                retryable=True,
                cause=exc,
            )
            error_details = error.to_error_details()
            await self._repo.update_run_status(run_id, status=RunStatus.FAILED, error_details=error_details)
            await self._emit_event(run_id, "run.failed", error_details, correlation_id)
            return RunResult(run_id=run_id, status=RunStatus.FAILED, errors=[error.message])

        await self._repo.update_run_status(run_id, status=RunStatus.COMPLETED, final_output=final_text)
        await self._emit_event(run_id, "run.completed", {"final_output": final_text}, correlation_id)
        return RunResult(run_id=run_id, status=RunStatus.COMPLETED, final_output=final_text, usage={})

    async def resume(self, run_id: str, checkpoint_ref: str, updates: dict[str, Any]) -> RunResult:
        raise NotImplementedError(
            "GoogleAdkKernel.resume() chưa implement — ADK dùng session-based state "
            "khác mô hình checkpoint serialize đơn giản của 2 kernel kia, cần nghiên "
            "cứu resumability_config/FunctionTool(require_confirmation=...) trước khi "
            "implement đúng (xem docstring class). Ghi rõ giới hạn thay vì giả vờ hỗ trợ."
        )

    async def cancel(self, run_id: str, reason: Optional[str] = None) -> bool:
        raise NotImplementedError(
            "GoogleAdkKernel.cancel() chưa implement — xem docstring class về phạm vi thu hẹp."
        )

    async def stream(self, request: RunRequest, spec: AgentSpec) -> AsyncIterator[dict[str, Any]]:
        result = await self.run(request, spec)
        events = await self._repo.list_events(result.run_id)
        for ev in events:
            yield {
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "payload": ev.payload,
                "sequence_no": ev.sequence_no,
            }
