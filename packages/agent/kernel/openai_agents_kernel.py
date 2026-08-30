from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from agent.capabilities.canonicalization import compute_payload_hash
from agent.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent.contracts.invocation import InvocationContext
from agent.contracts.output import ValidationFailure, validate_output_payload
from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.contracts.wait import WaitDescriptor, WaitKind
from agent.governance.contracts import ExecutionMode
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

__all__ = ["KernelRunState", "ManualToolLoopKernel"]


class KernelRunState:
    """State snapshot của OpenAI Agents Kernel để serialize và resume bền vững."""

    def __init__(
        self,
        run_id: str,
        messages: list[dict[str, Any]],
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
            "messages": self.messages,
            "pending_tool_calls": self.pending_tool_calls,
            "completed_tool_calls": self.completed_tool_calls,
            "context": self.context,
            "step_index": self.step_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KernelRunState:
        return cls(
            run_id=data["run_id"],
            messages=data.get("messages", []),
            pending_tool_calls=data.get("pending_tool_calls", []),
            completed_tool_calls=data.get("completed_tool_calls", []),
            context=data.get("context", {}),
            step_index=data.get("step_index", 0),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, json_str: str) -> KernelRunState:
        return cls.from_dict(json.loads(json_str))


class ManualToolLoopKernel:
    """Cài đặt Canonical ExecutionKernel dựa trên vòng lặp reasoning/tool-call
    THỦ CÔNG (manual), tương thích OpenAI/DeepSeek qua interface
    `.chat.completions.create(...)`. KHÔNG dùng `agents.Runner` thật — kernel
    dùng SDK thật là `RealOpenAIAgentsSDKKernel`
    (packages/agent_integrations/openai_agents_sdk/kernel.py), kernel mặc
    định production cho `runtime="openai_agents"` kể từ
    COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md Phase 1. Lớp
    này vẫn dùng được qua `runtime="manual_tool_loop"` tường minh.

    Chịu trách nhiệm:
    - Vòng lặp model reasoning, tool call generation, streaming execution events.
    - Checkpointing và serialize KernelRunState.
    - Phát hiện tool approval/interruption và map sang WaitDescriptor + RunApprovalRecord.
    - Quản lý cancellation và resume qua process độc lập.
    """

    def __init__(
        self,
        *,
        repository: RunRepository | None = None,
        spec_registry: SpecRegistryRepository | None = None,
        model_client: Any | None = None,
        capability_executor: Callable[..., Any] | None = None,
        policy_evaluator: Callable[..., Any] | None = None,
    ) -> None:
        self._repo = repository or InMemoryRunRepository()
        self._spec_registry = spec_registry or InMemorySpecRegistryRepository()
        self._skill_resolver = SkillResolver(self._spec_registry)
        self._client = model_client
        self._capability_executor = capability_executor
        self._policy_evaluator = policy_evaluator
        self._cancelled_runs: set[str] = set()

    async def _emit_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        event = RunEventRecord(
            run_id=run_id,
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
        )
        await self._repo.append_event(event)

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        run_id = request.run_id or f"run_{uuid.uuid4().hex[:16]}"
        correlation_id = request.correlation_id or run_id

        # 0. Publish spec vào registry bất biến TRƯỚC khi pin Run vào đó (Blueprint
        # V2 §25) — đảm bảo replay sau này resolve đúng nội dung spec đã dùng, kể cả
        # khi code hiện tại đã đổi `instructions`/`capability_refs` cho version khác.
        # Idempotent nếu cùng hash; raise SpecVersionHashConflictError nếu version đã
        # publish với nội dung KHÁC — đây là lỗi cấu hình thật (quên bump version),
        # không phải runtime failure tạm thời, nên KHÔNG convert thành RunResult FAILED.
        pinned_spec = spec if spec.definition_hash else spec.with_hash()
        await publish_agent_spec(
            pinned_spec, repository=self._spec_registry, publisher=request.principal
        )

        # 0.1 Resolve pinned skills TRƯỚC khi tạo Run — cùng nguyên tắc như publish
        # spec ở trên: mismatch/không tồn tại là lỗi cấu hình (fail cứng, propagate
        # raw AgentRuntimeError), KHÔNG phải runtime failure của 1 Run đã bắt đầu
        # (ADR-SKILL-IDENTITY §4, kích hoạt 2026-08-24) — tránh để lại RunRecord kẹt
        # ở status RUNNING nếu resolve thất bại giữa chừng.
        skill_texts: list[str] = []
        if spec.pinned_skills:
            resolved_skills = await self._skill_resolver.resolve(spec.pinned_skills)
            skill_texts = [s.instructions for s in resolved_skills if s.instructions]

        # 1. Tạo bản ghi Run
        run_record = RunRecord(
            run_id=run_id,
            workspace_id=request.workspace_id,
            conversation_id=request.conversation_id,
            session_ref=request.session_ref,
            principal=request.principal,
            root_executable_id=spec.id,
            root_executable_kind="agent",
            root_executable_version=spec.version,
            root_definition_hash=pinned_spec.definition_hash,
            policy_snapshot_ref=request.metadata.get("policy_snapshot_ref"),
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

        # 2. Khởi tạo KernelRunState
        # System message compose qua PromptBundle (Blueprint V2 §68.2): platform
        # policy (bất biến, mọi agent) + agent instructions (từ spec đã pin) +
        # resolved skill instructions + locale policy (canonical English, điều
        # khiển ngôn ngữ output theo request.locale — mặc định vi-VN).
        system_prompt = PromptBundle(
            agent_instructions=spec.instructions,
            skill_instructions=skill_texts,
            locale=request.locale,
        ).render()
        messages = [{"role": "system", "content": system_prompt}]
        if request.input:
            prompt_content = (
                request.input.get("prompt")
                or request.input.get("message")
                or json.dumps(request.input)
            )
            messages.append({"role": "user", "content": str(prompt_content)})

        state = KernelRunState(
            run_id=run_id,
            messages=messages,
            pending_tool_calls=[],
            completed_tool_calls=[],
            # request.metadata (không phải request.input — đó là literal prompt
            # text/args) là nơi đúng để mang ambient governance context (vd.
            # policy_snapshot) cho policy_evaluator. Trước đây context bị gán
            # nhầm = dict(request.input), khiến mọi ambient check trong
            # CosaPolicyEngine (tenant_status/principal_status) không bao giờ
            # thấy đúng key — theo COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_
            # 2026-08-25.md §29.3 mục 1.
            context=dict(request.metadata),
            step_index=0,
        )

        from opentelemetry import trace

        tracer = trace.get_tracer("agent.kernel")
        with tracer.start_as_current_span(
            "kernel.run",
            attributes={
                "run_id": run_id,
                "agent_spec_id": spec.id,
                "workspace_id": request.workspace_id or "",
                "principal": request.principal,
            },
        ):
            return await self._execute_reasoning_loop(run_record, state, spec, correlation_id)

    async def resume(
        self,
        run_id: str,
        checkpoint_ref: str,
        updates: dict[str, Any],
    ) -> RunResult:
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

        # Deserialize state từ checkpoint
        state = KernelRunState.from_dict(checkpoint.serialized_state)
        state.context.update(updates)

        # Xử lý các tool calls đã được approved/updated trong updates
        approved_calls = updates.get("approved_tool_calls", {})
        remaining_pending = []
        for call in state.pending_tool_calls:
            call_id = str(call.get("id") or call.get("tool_call_id") or "")
            if call_id in approved_calls or updates.get("approved") is True:
                # Thực thi tool call sau khi được approve
                tool_name = call.get("name") or call.get("function", {}).get("name", "")
                args_str = call.get("arguments") or call.get("function", {}).get("arguments", "{}")
                args = json.loads(args_str) if isinstance(args_str, str) else args_str

                await self._emit_event(
                    run_id,
                    "tool.started",
                    {"tool_call_id": call_id, "tool": tool_name},
                    correlation_id,
                )
                tool_res = await self._execute_tool(
                    tool_name,
                    args,
                    run_id=run_id,
                    tool_call_id=call_id,
                    run_record=run_record,
                    checkpoint_ref=checkpoint_ref,
                )
                # Audit event chỉ lưu hash — cùng nguyên tắc Task 9 áp dụng cho
                # CapabilityGateway/RealOpenAIAgentsSDKKernel (đều ghi vào chung
                # bảng `agent.run_events`). `tool_res` thô vẫn đi vào
                # `state.messages`/`completed_tool_calls` ngay dưới đây để tiếp
                # tục reasoning loop — không bị ảnh hưởng.
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
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(tool_res, default=str),
                    }
                )
                state.completed_tool_calls.append({"id": call_id, "result": tool_res})
            else:
                remaining_pending.append(call)

        state.pending_tool_calls = remaining_pending
        spec = AgentSpec(
            id=run_record.root_executable_id,
            version=run_record.root_executable_version,
            model_input_capability_ref="model.input.direct-user-message",
        )

        from opentelemetry import trace

        tracer = trace.get_tracer("agent.kernel")
        with tracer.start_as_current_span(
            "kernel.resume",
            attributes={
                "run_id": run_id,
                "checkpoint_ref": checkpoint_ref,
                "agent_spec_id": spec.id,
            },
        ):
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

    async def stream(
        self,
        request: RunRequest,
        spec: AgentSpec,
    ) -> AsyncIterator[dict[str, Any]]:
        # Khởi chạy Run và yield các events theo chuẩn SSE
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
        state: KernelRunState,
        spec: AgentSpec,
        correlation_id: str,
    ) -> RunResult:
        run_id = run_record.run_id
        max_turns = 10

        try:
            return await self._run_reasoning_turns(
                run_id, state, spec, correlation_id, max_turns, run_record=run_record
            )
        except AgentRuntimeError as err:
            # Typed runtime failure — Run phải FAILED tường minh, không âm thầm
            # biến lỗi provider thành assistant content COMPLETED.
            error_details = err.to_error_details()
            await self._repo.update_run_status(
                run_id, status=RunStatus.FAILED, error_details=error_details
            )
            await self._emit_event(run_id, "run.failed", error_details, correlation_id)
            return RunResult(run_id=run_id, status=RunStatus.FAILED, errors=[err.message])

    async def _run_reasoning_turns(
        self,
        run_id: str,
        state: KernelRunState,
        spec: AgentSpec,
        correlation_id: str,
        max_turns: int,
        run_record: RunRecord | None = None,
    ) -> RunResult:
        while state.step_index < max_turns:
            if run_id in self._cancelled_runs:
                return RunResult(run_id=run_id, status=RunStatus.CANCELLED)

            state.step_index += 1

            # 1. Gọi Model Provider
            response = await self._call_model(state.messages, spec)

            # 2. Xử lý message content
            if response.get("content"):
                content_text = response["content"]
                state.messages.append({"role": "assistant", "content": content_text})
                await self._emit_event(
                    run_id,
                    "message.delta",
                    {"content": content_text, "role": "assistant"},
                    correlation_id,
                )

            # 3. Kiểm tra Tool Calls
            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                # Không còn tool call nào -> Hoàn thành Run
                final_out = response.get("content")
                if spec and spec.output_schema:
                    is_valid, parsed_out, errs = validate_output_payload(
                        final_out, spec.output_schema
                    )
                    if not is_valid:
                        val_fail = ValidationFailure(
                            is_valid=False, errors=errs, raw_output=final_out
                        )
                        await self._repo.update_run_status(
                            run_id,
                            status=RunStatus.FAILED,
                            error_details={"validation_errors": errs},
                        )
                        await self._emit_event(
                            run_id,
                            "run.failed",
                            {
                                "error_type": "OutputValidationError",
                                "error_hash": compute_payload_hash(errs),
                                "error_count": len(errs),
                            },
                            correlation_id,
                        )
                        return RunResult(
                            run_id=run_id,
                            status=RunStatus.FAILED,
                            errors=[f"Output validation failed: {e}" for e in errs],
                            final_output=val_fail.model_dump(),
                        )
                    final_out = parsed_out

                await self._repo.update_run_status(
                    run_id, status=RunStatus.COMPLETED, final_output=final_out
                )
                # Audit event chỉ lưu hash — final_output thô vẫn đi qua
                # RunRecord.final_output (update_run_status ở trên) và RunResult
                # trả về ngay dưới, đây mới là kênh caller thật đọc.
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
                    usage=response.get("usage", {}),
                )

            # 4. Có tool calls -> Đánh giá Policy / Approval
            waits: list[WaitDescriptor] = []
            for call in tool_calls:
                call_id = call.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                tool_name = call.get("name") or call.get("function", {}).get("name", "")
                args_str = call.get("arguments") or call.get("function", {}).get("arguments", "{}")
                args = json.loads(args_str) if isinstance(args_str, str) else args_str

                await self._emit_event(
                    run_id,
                    "tool.requested",
                    {"tool_call_id": call_id, "tool": tool_name, "args": args},
                    correlation_id,
                )

                # Lưu ToolCall record vào exact invocation ledger
                tc_record = RunToolCallRecord(
                    tool_call_id=call_id,
                    run_id=run_id,
                    capability_id=tool_name,
                    payload_hash=compute_payload_hash(args),
                    input_payload=args,
                    status="pending",
                )
                await self._repo.save_tool_call(tc_record)

                # Policy Evaluation
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
                    state.pending_tool_calls.append(call)

                    # Checkpoint trước khi pause
                    ckpt_ref = f"ckpt_{run_id}_{state.step_index}"
                    checkpoint = RunCheckpointRecord(
                        checkpoint_ref=ckpt_ref,
                        run_id=run_id,
                        sequence_no=state.step_index,
                        step_name=tool_name,
                        state_kind="kernel_run_state",
                        serialized_state=state.to_dict(),
                    )
                    await self._repo.save_checkpoint(checkpoint)
                    await self._emit_event(
                        run_id, "checkpoint.created", {"checkpoint_ref": ckpt_ref}, correlation_id
                    )

                    # Tạo Approval record
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
                # Tạm dừng Run ở trạng thái WAITING_APPROVAL
                await self._repo.update_run_status(run_id, status=RunStatus.WAITING_APPROVAL)
                await self._emit_event(
                    run_id,
                    "run.waiting",
                    {"waits": [w.model_dump() for w in waits]},
                    correlation_id,
                )
                return RunResult(
                    run_id=run_id,
                    status=RunStatus.WAITING_APPROVAL,
                    interruptions_waits=waits,
                )

            # 5. Nếu tất cả tool calls đều được ALLOW -> Thực thi ngay
            for call in tool_calls:
                call_id = call.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                tool_name = call.get("name") or call.get("function", {}).get("name", "")
                args_str = call.get("arguments") or call.get("function", {}).get("arguments", "{}")
                args = json.loads(args_str) if isinstance(args_str, str) else args_str

                await self._emit_event(
                    run_id,
                    "tool.started",
                    {"tool_call_id": call_id, "tool": tool_name},
                    correlation_id,
                )
                tool_res = await self._execute_tool(
                    tool_name,
                    args,
                    run_id=run_id,
                    tool_call_id=call_id,
                    run_record=run_record,
                )
                # Audit event chỉ lưu hash — cùng nguyên tắc Task 9 áp dụng cho
                # CapabilityGateway/RealOpenAIAgentsSDKKernel (đều ghi vào chung
                # bảng `agent.run_events`). `tool_res` thô vẫn đi vào
                # `state.messages`/`completed_tool_calls` ngay dưới đây để tiếp
                # tục reasoning loop — không bị ảnh hưởng.
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
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(tool_res, default=str),
                    }
                )
                state.completed_tool_calls.append({"id": call_id, "result": tool_res})

        # Quá số turn tối đa
        await self._repo.update_run_status(
            run_id, status=RunStatus.FAILED, error_details={"error": "Max reasoning turns reached"}
        )
        return RunResult(
            run_id=run_id, status=RunStatus.FAILED, errors=["Max reasoning turns reached"]
        )

    async def _call_model(self, messages: list[dict[str, Any]], spec: AgentSpec) -> dict[str, Any]:
        if not (
            self._client
            and hasattr(self._client, "chat")
            and hasattr(self._client.chat, "completions")
        ):
            # Production KHÔNG được silently mock khi model_client chưa cấu
            # hình — đây từng là nguồn của lỗi correctness nghiêm trọng: mọi
            # agent run production trả kết quả giả (keyword-matched), kể cả
            # khi DEEPSEEK_API_KEY đã set đúng, vì composition mặc định
            # không bao giờ inject model_client (COSA_PRODUCTION_RUNTIME_
            # CLOSURE_ADJUSTMENT_2026-08-25.md §3.2). Test dùng
            # agent_testkit.mock_tool_loop_model_client.MockToolLoopModelClient
            # tường minh thay vì dựa vào fallback ngầm.
            raise AgentRuntimeError(
                RuntimeErrorCode.MODEL_PROVIDER_ERROR,
                "ManualToolLoopKernel requires an explicit model_client "
                "(e.g. LiteLLMModelClient) — no implicit mock fallback in "
                "production. Tests must pass "
                "model_client=agent_testkit.mock_tool_loop_model_client.MockToolLoopModelClient() "
                "explicitly.",
                retryable=False,
            )

        # Gọi real OpenAI / DeepSeek client
        try:
            resp = await self._client.chat.completions.create(
                model=spec.model_policy.get("model", "deepseek-chat"),
                messages=messages,
                temperature=spec.model_policy.get("temperature", 0.0),
            )
            choice = resp.choices[0]
            tool_calls = []
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    tool_calls.append(
                        {
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    )
            return {
                "content": choice.message.content or "",
                "tool_calls": tool_calls,
                "usage": {
                    "total_tokens": getattr(resp.usage, "total_tokens", 0),
                    "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
                }
                if resp.usage
                else {},
            }
        except AgentRuntimeError:
            # `self._client` (vd LiteLLMModelClient) đã tự phân loại đúng
            # RuntimeErrorCode (MODEL_RATE_LIMIT, CONTEXT_LIMIT_EXCEEDED...) —
            # không re-wrap thành MODEL_PROVIDER_ERROR chung chung, mất thông tin.
            raise
        except Exception as exc:
            # Provider/runtime failure phải là typed error, không phải assistant
            # content thành công (Blueprint V2 §56 anti-pattern; ADR-RUNTIME-001).
            raise AgentRuntimeError(
                RuntimeErrorCode.MODEL_PROVIDER_ERROR,
                f"Model provider call failed: {exc}",
                retryable=True,
                cause=exc,
            ) from exc

    async def _execute_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        *,
        run_id: str,
        tool_call_id: str,
        run_record: RunRecord | None = None,
        checkpoint_ref: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Thực thi capability qua `capability_executor`.

        BẮT BUỘC truyền `run_id`/`tool_call_id` THẬT của lần gọi đang xử lý và
        InvocationContext đầy đủ tenancy để không bị mất context.
        """
        ctx = context or {}
        ws_id = str(
            (run_record.workspace_id if run_record else None) or ctx.get("workspace_id") or ""
        )
        princ = str(
            (run_record.principal if run_record else None) or ctx.get("principal") or "system"
        )
        ckpt = str(checkpoint_ref or ctx.get("checkpoint_ref") or f"ckpt_{run_id}_{tool_call_id}")
        exec_mode = (
            (run_record.execution_mode if run_record else None)
            or ctx.get("execution_mode")
            or ExecutionMode.AGENT
        )

        inv_ctx = InvocationContext(
            run_id=run_id,
            tool_call_id=tool_call_id,
            checkpoint_ref=ckpt,
            workspace_id=ws_id,
            principal=princ,
            conversation_id=run_record.conversation_id
            if run_record
            else ctx.get("conversation_id"),
            correlation_id=run_record.correlation_id if run_record else ctx.get("correlation_id"),
            policy_snapshot=ctx.get("policy_snapshot"),
            policy_snapshot_ref=ctx.get("policy_snapshot_ref"),
            policy_snapshot_version=ctx.get("policy_snapshot_version"),
            root_spec_identity=run_record.root_executable_id
            if run_record
            else ctx.get("root_spec_identity"),
            capability_identity=tool_name,
            execution_mode=exec_mode
            if isinstance(exec_mode, ExecutionMode)
            else ExecutionMode.AGENT,
            metadata=ctx,
        )

        if self._capability_executor:
            try:
                if asyncio.iscoroutinefunction(self._capability_executor):
                    return await self._capability_executor(tool_name, args, inv_ctx)
                return self._capability_executor(tool_name, args, inv_ctx)
            except TypeError:
                pass

            try:
                if asyncio.iscoroutinefunction(self._capability_executor):
                    return await self._capability_executor(tool_name, args)
                return self._capability_executor(tool_name, args)
            except TypeError:
                from agent.capabilities.gateway import GatewayExecutionRequest

                req = GatewayExecutionRequest(
                    run_id=run_id,
                    capability_id=tool_name,
                    input_payload=args,
                    principal=princ,
                    checkpoint_ref=ckpt,
                    tool_call_id=tool_call_id,
                    execution_mode=exec_mode
                    if isinstance(exec_mode, ExecutionMode)
                    else ExecutionMode.AGENT,
                    workspace_id=ws_id,
                    context=inv_ctx,
                )
                if asyncio.iscoroutinefunction(self._capability_executor):
                    res = await self._capability_executor(req)
                else:
                    res = self._capability_executor(req)
                return res.output_payload if hasattr(res, "output_payload") else res
        return {"status": "success", "executed_tool": tool_name, "params": args}
