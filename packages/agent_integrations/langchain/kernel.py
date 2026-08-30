from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from agent.capabilities.canonicalization import compute_payload_hash
from agent.capabilities.gateway import GatewayExecutionRequest
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.contracts.wait import WaitDescriptor, WaitKind
from agent.prompts.bundle import PromptBundle
from agent.registry.publisher import publish_agent_spec
from agent.registry.repository import InMemorySpecRegistryRepository, SpecRegistryRepository
from agent.runs.models import (
    RunApprovalRecord,
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent.runs.repository import InMemoryRunRepository, RunRepository
from agent.skills.resolver import SkillResolver
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    messages_from_dict,
    messages_to_dict,
)

from agent_integrations.langchain.tool_schema_adapter import (
    capability_spec_to_langchain_tool_schema,
)

__all__ = ["LangChainKernel", "LangChainKernelRunState"]


class LangChainKernelRunState:
    """State snapshot của LangChainKernel — tương đương KernelRunState của
    OpenAIAgentsKernel nhưng dùng `BaseMessage` (LangChain) thay vì dict thô,
    serialize qua `messages_to_dict`/`messages_from_dict` để checkpoint/resume
    đúng loại message (System/Human/AI/Tool), không mất `tool_calls` structured."""

    def __init__(
        self,
        run_id: str,
        messages: list[BaseMessage],
        pending_tool_calls: list[dict[str, Any]],
        completed_tool_calls: list[dict[str, Any]],
        context: dict[str, Any],
        step_index: int = 0,
    ) -> None:
        self.run_id = run_id
        self.messages = messages
        self.pending_tool_calls = pending_tool_calls
        self.completed_tool_calls = completed_tool_calls
        self.context = context
        self.step_index = step_index

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "messages": messages_to_dict(self.messages),
            "pending_tool_calls": self.pending_tool_calls,
            "completed_tool_calls": self.completed_tool_calls,
            "context": self.context,
            "step_index": self.step_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LangChainKernelRunState:
        return cls(
            run_id=data["run_id"],
            messages=messages_from_dict(data.get("messages", [])),
            pending_tool_calls=data.get("pending_tool_calls", []),
            completed_tool_calls=data.get("completed_tool_calls", []),
            context=data.get("context", {}),
            step_index=data.get("step_index", 0),
        )


class LangChainKernel:
    """`ExecutionKernel` implementation dùng LangChain `BaseChatModel` (mặc định
    `ChatDeepSeek`) làm model provider, theo `ADR-RUNTIME-001` (DRAFT, chờ review
    — xem docs/architecture/adr/) và Blueprint V2 §64/§74.

    KHÔNG phải kernel mặc định production. Chỉ được chọn qua runtime policy tường
    minh (`apps/cosa/composition/agent_plane.py`), chạy song song với
    `OpenAIAgentsKernel`/ADK cho tới khi pass đủ `agent_testkit/kernel_conformance/`.

    Giữ đúng các invariant đã chứng minh ở `OpenAIAgentsKernel`:
    - Typed error (`AgentRuntimeError`) — không convert provider failure thành
      assistant content COMPLETED.
    - Publish spec vào registry TRƯỚC khi pin Run (Blueprint V2 §25).
    - `PromptBundle` cho system message (platform policy + agent instructions + locale).
    - Exact `(run_id, tool_call_id)` giữ nguyên xuyên suốt kernel → gateway, không
      tự sinh lại (đúng bug đã fix ở `OpenAIAgentsKernel._execute_tool`).
    """

    def __init__(
        self,
        *,
        repository: RunRepository | None = None,
        spec_registry: SpecRegistryRepository | None = None,
        capability_registry: CapabilityRegistry | None = None,
        chat_model: Any | None = None,
        capability_executor: Callable[..., Any] | None = None,
        policy_evaluator: Callable[..., Any] | None = None,
    ) -> None:
        self._repo = repository or InMemoryRunRepository()
        self._spec_registry = spec_registry or InMemorySpecRegistryRepository()
        self._skill_resolver = SkillResolver(self._spec_registry)
        self._capability_registry = capability_registry
        self._chat_model = chat_model
        self._capability_executor = capability_executor
        self._policy_evaluator = policy_evaluator
        self._cancelled_runs: set[str] = set()

    def _resolve_chat_model(self, spec: AgentSpec) -> Any:
        if self._chat_model is not None:
            return self._chat_model
        from langchain_deepseek import ChatDeepSeek

        return ChatDeepSeek(
            model=spec.model_policy.get("model", "deepseek-chat"),
            temperature=spec.model_policy.get("temperature", 0.0),
        )

    def _bind_tools(self, chat_model: Any, spec: AgentSpec) -> Any:
        if not self._capability_registry or not spec.capability_refs:
            return chat_model
        tool_schemas = []
        for cap_id in spec.capability_refs:
            reg = self._capability_registry.get(cap_id)
            if reg:
                tool_schemas.append(capability_spec_to_langchain_tool_schema(reg.spec))
        if not tool_schemas:
            return chat_model
        return chat_model.bind_tools(tool_schemas)

    async def _emit_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        await self._repo.append_event(
            RunEventRecord(
                run_id=run_id, event_type=event_type, payload=payload, correlation_id=correlation_id
            )
        )

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        run_id = request.run_id or f"run_{uuid.uuid4().hex[:16]}"
        correlation_id = request.correlation_id or run_id

        # Publish spec bất biến TRƯỚC khi pin Run — cùng invariant như OpenAIAgentsKernel.
        pinned_spec = spec if spec.definition_hash else spec.with_hash()
        await publish_agent_spec(
            pinned_spec, repository=self._spec_registry, publisher=request.principal
        )

        # Resolve pinned skills TRƯỚC khi tạo Run — mismatch/không tồn tại là lỗi
        # cấu hình, propagate raw, không để RunRecord kẹt RUNNING (ADR-SKILL-IDENTITY §4).
        skill_texts: list[str] = []
        if spec.pinned_skills:
            resolved_skills = await self._skill_resolver.resolve(spec.pinned_skills)
            skill_texts = [s.instructions for s in resolved_skills if s.instructions]

        run_record = RunRecord(
            run_id=run_id,
            # sau Task 7: workspace là tenant key duy nhất; capability/governance layer nhận workspace_id qua tên tenant_id
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
        await self._emit_event(
            run_id,
            "run.started",
            {"principal": request.principal, "spec_id": spec.id},
            correlation_id,
        )

        system_prompt = PromptBundle(
            agent_instructions=spec.instructions,
            skill_instructions=skill_texts,
            locale=request.locale,
        ).render()
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        if request.input:
            prompt_content = (
                request.input.get("prompt")
                or request.input.get("message")
                or json.dumps(request.input)
            )
            messages.append(HumanMessage(content=str(prompt_content)))

        state = LangChainKernelRunState(
            run_id=run_id,
            messages=messages,
            pending_tool_calls=[],
            completed_tool_calls=[],
            context=dict(request.input),
        )
        return await self._execute_reasoning_loop(run_record, state, spec, correlation_id)

    async def resume(self, run_id: str, checkpoint_ref: str, updates: dict[str, Any]) -> RunResult:
        run_record = await self._repo.get_run(run_id)
        if not run_record:
            return RunResult(
                run_id=run_id, status=RunStatus.FAILED, errors=[f"Run {run_id} not found"]
            )

        checkpoint = await self._repo.get_checkpoint(checkpoint_ref)
        if not checkpoint:
            return RunResult(
                run_id=run_id,
                status=RunStatus.FAILED,
                errors=[f"Checkpoint {checkpoint_ref} not found"],
            )

        correlation_id = run_record.correlation_id or run_id
        await self._emit_event(
            run_id,
            "run.resumed",
            {"checkpoint_ref": checkpoint_ref, "updates": updates},
            correlation_id,
        )

        state = LangChainKernelRunState.from_dict(checkpoint.serialized_state)
        state.context.update(updates)

        approved_calls = updates.get("approved_tool_calls", {})
        remaining_pending: list[dict[str, Any]] = []
        for call in state.pending_tool_calls:
            call_id = str(call.get("id") or call.get("tool_call_id") or "")
            if call_id in approved_calls or updates.get("approved") is True:
                tool_name = call.get("name", "")
                args = call.get("args", {})

                await self._emit_event(
                    run_id,
                    "tool.started",
                    {"tool_call_id": call_id, "tool": tool_name},
                    correlation_id,
                )
                tool_res = await self._execute_tool(
                    tool_name, args, run_id=run_id, tool_call_id=call_id
                )
                # Audit event chỉ lưu hash — cùng nguyên tắc Task 9 áp dụng cho
                # CapabilityGateway/RealOpenAIAgentsSDKKernel/ManualToolLoopKernel
                # (đều ghi vào chung bảng `agent.run_events`). `tool_res` thô vẫn
                # đi vào `state.messages`/`completed_tool_calls` để tiếp tục
                # reasoning loop — không bị ảnh hưởng.
                await self._emit_event(
                    run_id,
                    "tool.completed",
                    {
                        "tool_call_id": call_id,
                        "output_hash": compute_payload_hash(tool_res),
                        "output_present": tool_res is not None,
                    },
                    correlation_id,
                )

                state.messages.append(
                    ToolMessage(content=json.dumps(tool_res, default=str), tool_call_id=call_id)
                )
                state.completed_tool_calls.append({"id": call_id, "result": tool_res})
            else:
                remaining_pending.append(call)

        state.pending_tool_calls = remaining_pending
        spec = AgentSpec(
            id=run_record.root_executable_id, version=run_record.root_executable_version
        )

        return await self._execute_reasoning_loop(run_record, state, spec, correlation_id)

    async def cancel(self, run_id: str, reason: str | None = None) -> bool:
        self._cancelled_runs.add(run_id)
        run_record = await self._repo.get_run(run_id)
        if run_record:
            await self._repo.update_run_status(
                run_id,
                status=RunStatus.CANCELLED,
                error_details={"reason": reason or "Cancelled by user"},
            )
            await self._emit_event(
                run_id,
                "run.failed",
                {"status": "cancelled", "reason": reason},
                run_record.correlation_id,
            )
        return True

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

    async def _execute_reasoning_loop(
        self,
        run_record: RunRecord,
        state: LangChainKernelRunState,
        spec: AgentSpec,
        correlation_id: str,
    ) -> RunResult:
        run_id = run_record.run_id
        max_turns = 10

        try:
            return await self._run_reasoning_turns(run_id, state, spec, correlation_id, max_turns)
        except AgentRuntimeError as err:
            error_details = err.to_error_details()
            await self._repo.update_run_status(
                run_id, status=RunStatus.FAILED, error_details=error_details
            )
            await self._emit_event(run_id, "run.failed", error_details, correlation_id)
            return RunResult(run_id=run_id, status=RunStatus.FAILED, errors=[err.message])

    async def _run_reasoning_turns(
        self,
        run_id: str,
        state: LangChainKernelRunState,
        spec: AgentSpec,
        correlation_id: str,
        max_turns: int,
    ) -> RunResult:
        chat_model = self._bind_tools(self._resolve_chat_model(spec), spec)

        while state.step_index < max_turns:
            if run_id in self._cancelled_runs:
                return RunResult(run_id=run_id, status=RunStatus.CANCELLED)

            state.step_index += 1

            try:
                ai_msg = await chat_model.ainvoke(state.messages)
            except AgentRuntimeError:
                raise
            except Exception as exc:
                raise AgentRuntimeError(
                    RuntimeErrorCode.MODEL_PROVIDER_ERROR,
                    f"LangChain model provider call failed: {exc}",
                    retryable=True,
                    cause=exc,
                ) from exc

            if not isinstance(ai_msg, AIMessage):
                raise AgentRuntimeError(
                    RuntimeErrorCode.MODEL_INVALID_RESPONSE,
                    f"LangChain chat model trả về loại message không mong đợi: {type(ai_msg).__name__}",
                )

            state.messages.append(ai_msg)
            if ai_msg.content:
                # Audit event nội bộ kernel này KHÔNG phải kênh hiển thị UI thật —
                # đường hiển thị thật đọc `RunResult.final_output` sau khi
                # `kernel.run()` trả về rồi tự emit `message.delta` riêng vào bảng
                # `run_stream_events` (apps/cosa/worker/handlers.py, qua
                # `CosaEventStreamManager.emit()`), độc lập với `agent.run_events`
                # mà `_emit_event` ở đây ghi vào. Vì vậy chỉ lưu hash ở đây, không
                # ảnh hưởng hiển thị chat thật.
                await self._emit_event(
                    run_id,
                    "message.delta",
                    {
                        "content_hash": compute_payload_hash(ai_msg.content),
                        "content_present": True,
                        "role": "assistant",
                    },
                    correlation_id,
                )

            tool_calls = ai_msg.tool_calls or []
            if not tool_calls:
                final_out = ai_msg.content
                await self._repo.update_run_status(
                    run_id, status=RunStatus.COMPLETED, final_output=final_out
                )
                # Audit event chỉ lưu hash — final_output thô thật đi qua
                # RunRecord.final_output (update_run_status ở trên) và RunResult
                # trả về ngay dưới.
                await self._emit_event(
                    run_id,
                    "run.completed",
                    {
                        "final_output_hash": compute_payload_hash(final_out),
                        "final_output_present": final_out is not None,
                    },
                    correlation_id,
                )
                return RunResult(
                    run_id=run_id,
                    status=RunStatus.COMPLETED,
                    final_output=final_out,
                    usage=ai_msg.usage_metadata or {} if hasattr(ai_msg, "usage_metadata") else {},
                )

            waits: list[WaitDescriptor] = []
            for call in tool_calls:
                call_id = call.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                tool_name = call.get("name", "")
                args = call.get("args", {})

                await self._emit_event(
                    run_id,
                    "tool.requested",
                    {"tool_call_id": call_id, "tool": tool_name, "args": args},
                    correlation_id,
                )

                tc_record = RunToolCallRecord(
                    tool_call_id=call_id,
                    run_id=run_id,
                    capability_id=tool_name,
                    payload_hash=compute_payload_hash(args),
                    input_payload=args,
                    status="pending",
                )
                await self._repo.save_tool_call(tc_record)

                decision_obj = "ALLOW"
                if self._policy_evaluator:
                    try:
                        decision_obj = self._policy_evaluator(tool_name, args, state.context)
                    except TypeError:
                        decision_obj = self._policy_evaluator(tool_name, args)
                elif "transfer" in tool_name or "payout" in tool_name or "deploy" in tool_name:
                    decision_obj = "REQUIRE_APPROVAL"

                decision_str = (
                    decision_obj.outcome.value
                    if hasattr(decision_obj, "outcome")
                    else str(decision_obj).upper()
                )
                await self._emit_event(
                    run_id,
                    "policy.evaluated",
                    {"tool_call_id": call_id, "decision": decision_str},
                    correlation_id,
                )

                if decision_str == "REQUIRE_APPROVAL":
                    state.pending_tool_calls.append(
                        {"id": call_id, "name": tool_name, "args": args}
                    )

                    ckpt_ref = f"ckpt_{run_id}_{state.step_index}"
                    checkpoint = RunCheckpointRecord(
                        checkpoint_ref=ckpt_ref,
                        run_id=run_id,
                        sequence_no=state.step_index,
                        step_name=tool_name,
                        state_kind="langchain_kernel_run_state",
                        serialized_state=state.to_dict(),
                    )
                    await self._repo.save_checkpoint(checkpoint)
                    await self._emit_event(
                        run_id, "checkpoint.created", {"checkpoint_ref": ckpt_ref}, correlation_id
                    )

                    appr_id = f"appr_{uuid.uuid4().hex[:12]}"
                    approval = RunApprovalRecord(
                        approval_id=appr_id,
                        run_id=run_id,
                        tool_call_id=call_id,
                        checkpoint_ref=ckpt_ref,
                        status="pending",
                        action=tool_name,
                        subject=f"Approval requested for tool {tool_name} with params {args}",
                    )
                    await self._repo.create_approval(approval)
                    await self._emit_event(
                        run_id,
                        "approval.required",
                        {"approval_id": appr_id, "tool_call_id": call_id, "action": tool_name},
                        correlation_id,
                    )

                    waits.append(
                        WaitDescriptor(
                            kind=WaitKind.APPROVAL,
                            reason=f"Action '{tool_name}' requires human approval",
                            checkpoint_ref=ckpt_ref,
                            related_ref=appr_id,
                            resume_trigger="approval.decided",
                        )
                    )

            if waits:
                await self._repo.update_run_status(run_id, status=RunStatus.WAITING_APPROVAL)
                await self._emit_event(
                    run_id,
                    "run.waiting",
                    {"waits": [w.model_dump() for w in waits]},
                    correlation_id,
                )
                return RunResult(
                    run_id=run_id, status=RunStatus.WAITING_APPROVAL, interruptions_waits=waits
                )

            # Tất cả tool call ALLOW -> thực thi ngay, exact identity giữ nguyên
            for call in tool_calls:
                call_id = call.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                tool_name = call.get("name", "")
                args = call.get("args", {})

                await self._emit_event(
                    run_id,
                    "tool.started",
                    {"tool_call_id": call_id, "tool": tool_name},
                    correlation_id,
                )
                tool_res = await self._execute_tool(
                    tool_name, args, run_id=run_id, tool_call_id=call_id
                )
                await self._emit_event(
                    run_id,
                    "tool.completed",
                    {
                        "tool_call_id": call_id,
                        "output_hash": compute_payload_hash(tool_res),
                        "output_present": tool_res is not None,
                    },
                    correlation_id,
                )

                state.messages.append(
                    ToolMessage(content=json.dumps(tool_res, default=str), tool_call_id=call_id)
                )
                state.completed_tool_calls.append({"id": call_id, "result": tool_res})

        await self._repo.update_run_status(
            run_id, status=RunStatus.FAILED, error_details={"error": "Max reasoning turns reached"}
        )
        return RunResult(
            run_id=run_id, status=RunStatus.FAILED, errors=["Max reasoning turns reached"]
        )

    async def _execute_tool(
        self, tool_name: str, args: dict[str, Any], *, run_id: str, tool_call_id: str
    ) -> Any:
        if self._capability_executor:
            try:
                if asyncio.iscoroutinefunction(self._capability_executor):
                    return await self._capability_executor(tool_name, args)
                return self._capability_executor(tool_name, args)
            except TypeError:
                req = GatewayExecutionRequest(
                    run_id=run_id,
                    capability_id=tool_name,
                    input_payload=args,
                    tool_call_id=tool_call_id,
                )
                if asyncio.iscoroutinefunction(self._capability_executor):
                    res = await self._capability_executor(req)
                else:
                    res = self._capability_executor(req)
                return res.output_payload if hasattr(res, "output_payload") else res
        return {"status": "success", "executed_tool": tool_name, "params": args}
