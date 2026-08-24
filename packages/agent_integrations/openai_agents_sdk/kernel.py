from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncIterator, Callable, Optional

from agents import Agent, FunctionTool, RunConfig, RunHooks, Runner, RunState
from agents.items import ToolApprovalItem

from agent_core.capabilities.gateway import GatewayExecutionRequest
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.contracts.capability import CapabilitySpec
from agent_core.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent_core.contracts.kernel import ExecutionKernel
from agent_core.contracts.run import RunRequest, RunResult, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.contracts.wait import WaitDescriptor, WaitKind
from agent_core.prompts.bundle import PromptBundle
from agent_core.registry.publisher import publish_agent_spec
from agent_core.registry.repository import InMemorySpecRegistryRepository, SpecRegistryRepository
from agent_core.skills.resolver import SkillResolver
from agent_core.runs.models import (
    RunApprovalRecord,
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent_core.runs.repository import InMemoryRunRepository, RunRepository

__all__ = ["RealOpenAIAgentsSDKKernel"]


class _RunCancelled(Exception):
    """Nội bộ — raise trong hook `on_llm_start` để chặn `Runner.run()` tiếp
    tục turn kế tiếp khi Run đã bị cancel giữa chừng (SDK không expose điểm
    dừng nào chi tiết hơn giữa các turn cho caller ngoài)."""


class _CancellationHooks(RunHooks):
    def __init__(self, run_id: str, cancelled_runs: set[str]) -> None:
        self._run_id = run_id
        self._cancelled_runs = cancelled_runs

    async def on_llm_start(self, context, agent, system_prompt, input_items) -> None:  # type: ignore[override]
        if self._run_id in self._cancelled_runs:
            raise _RunCancelled(self._run_id)


class RealOpenAIAgentsSDKKernel:
    """`ExecutionKernel` implementation dùng `agents.Runner` THẬT của OpenAI
    Agents SDK (package `openai-agents`, không phải
    `packages/agent_core/kernel/openai_agents_kernel.py` — class đó tên trùng
    nhưng là manual reasoning loop, KHÔNG dùng SDK thật, vẫn là kernel mặc
    định production).

    Theo Wave 10 (COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md
    Phần 3) — adapter TUỲ CHỌN theo `ADR-RUNTIME-001`, KHÔNG thay kernel mặc
    định production, chỉ chọn qua runtime policy tường minh giống
    `LangChainKernel`.

    Khác biệt kiến trúc quan trọng so với `LangChainKernel`/`OpenAIAgentsKernel`
    (2 kernel manual-loop): `agents.Runner.run()` tự sở hữu toàn bộ vòng lặp
    reasoning/tool-calling nội bộ SDK — kernel này KHÔNG viết lại vòng lặp,
    chỉ build `Agent`/`FunctionTool` từ `AgentSpec`/`CapabilitySpec`, gọi
    `Runner.run()`, và dịch `RunResult.interruptions` (approval-gate của SDK)
    sang `WaitDescriptor` của COSA. Checkpoint dùng `RunState.to_json()`/
    `from_json()` — cơ chế serialize gốc của SDK, không tự viết serializer
    riêng như 2 kernel kia.
    """

    def __init__(
        self,
        *,
        repository: Optional[RunRepository] = None,
        spec_registry: Optional[SpecRegistryRepository] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        model: Optional[Any] = None,
        capability_executor: Optional[Callable[..., Any]] = None,
        policy_evaluator: Optional[Callable[[str, dict[str, Any], dict[str, Any]], str]] = None,
    ) -> None:
        self._repo = repository or InMemoryRunRepository()
        self._spec_registry = spec_registry or InMemorySpecRegistryRepository()
        self._skill_resolver = SkillResolver(self._spec_registry)
        self._capability_registry = capability_registry
        self._model = model
        self._capability_executor = capability_executor
        self._policy_evaluator = policy_evaluator
        self._cancelled_runs: set[str] = set()
        # Nhớ lại approval TRUE/FALSE gần nhất cho mỗi tool_call_id đã policy-
        # evaluate — `FunctionTool.needs_approval` của SDK là callable đồng bộ
        # với chữ ký (context, args, call_id), không nhận policy_evaluator của
        # COSA trực tiếp nên phải cache quyết định ở đây trước khi Runner gọi.
        self._pending_decisions: dict[str, str] = {}

    async def _emit_event(
        self, run_id: str, event_type: str, payload: dict[str, Any], correlation_id: Optional[str] = None
    ) -> None:
        await self._repo.append_event(
            RunEventRecord(run_id=run_id, event_type=event_type, payload=payload, correlation_id=correlation_id)
        )

    def _evaluate_policy(self, tool_name: str, args: dict[str, Any], context: dict[str, Any]) -> str:
        if self._policy_evaluator:
            try:
                decision_obj = self._policy_evaluator(tool_name, args, context)
            except TypeError:
                decision_obj = self._policy_evaluator(tool_name, args)
        elif "transfer" in tool_name or "payout" in tool_name or "deploy" in tool_name:
            decision_obj = "REQUIRE_APPROVAL"
        else:
            decision_obj = "ALLOW"
        return decision_obj.outcome.value if hasattr(decision_obj, "outcome") else str(decision_obj).upper()

    def _build_tools(self, spec: AgentSpec, run_id: str, context: dict[str, Any]) -> list[FunctionTool]:
        if not self._capability_registry or not spec.capability_refs:
            return []

        tools: list[FunctionTool] = []
        for cap_id in spec.capability_refs:
            reg = self._capability_registry.get(cap_id)
            if not reg:
                continue
            cap_spec: CapabilitySpec = reg.spec
            tools.append(self._make_tool(cap_spec, run_id, context))
        return tools

    def _make_tool(self, cap_spec: CapabilitySpec, run_id: str, context: dict[str, Any]) -> FunctionTool:
        async def _on_invoke(tool_context: Any, args_json: str) -> Any:
            args = json.loads(args_json) if args_json else {}
            call_id = getattr(tool_context, "tool_call_id", None) or f"call_{uuid.uuid4().hex[:8]}"
            await self._emit_event(run_id, "tool.started", {"tool_call_id": call_id, "tool": cap_spec.id})
            result = await self._execute_tool(cap_spec.id, args, run_id=run_id, tool_call_id=call_id)
            await self._emit_event(run_id, "tool.completed", {"tool_call_id": call_id, "result": result})
            return result

        async def _needs_approval(run_context: Any, args: dict[str, Any], call_id: str) -> bool:
            decision = self._evaluate_policy(cap_spec.id, args, context)
            self._pending_decisions[call_id] = decision
            return decision == "REQUIRE_APPROVAL"

        return FunctionTool(
            name=cap_spec.id,
            description=cap_spec.description or "",
            params_json_schema=cap_spec.input_schema or {"type": "object", "properties": {}},
            on_invoke_tool=_on_invoke,
            needs_approval=_needs_approval,
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

        context: dict[str, Any] = dict(request.input)
        tools = self._build_tools(spec, run_id, context)
        agent = Agent(
            name=spec.id,
            instructions=system_prompt,
            tools=tools,
            model=self._model,
        )

        prompt_content = ""
        if request.input:
            prompt_content = request.input.get("prompt") or request.input.get("message") or json.dumps(request.input)

        return await self._invoke_and_translate(
            run_id=run_id,
            agent=agent,
            sdk_input=str(prompt_content),
            correlation_id=correlation_id,
        )

    async def resume(self, run_id: str, checkpoint_ref: str, updates: dict[str, Any]) -> RunResult:
        run_record = await self._repo.get_run(run_id)
        if not run_record:
            return RunResult(run_id=run_id, status=RunStatus.FAILED, errors=[f"Run {run_id} not found"])

        checkpoint = await self._repo.get_checkpoint(checkpoint_ref)
        if not checkpoint:
            return RunResult(run_id=run_id, status=RunStatus.FAILED, errors=[f"Checkpoint {checkpoint_ref} not found"])

        correlation_id = run_record.correlation_id or run_id
        await self._emit_event(run_id, "run.resumed", {"checkpoint_ref": checkpoint_ref, "updates": updates}, correlation_id)

        # Resolve lại đầy đủ AgentSpec (kể cả `capability_refs`) từ spec
        # registry bất biến — KHÔNG dựng lại `AgentSpec(id=..., version=...)`
        # trơ như 2 kernel manual-loop khác, vì `Runner.run()` cần build lại
        # `Agent`/`FunctionTool` set ĐÚNG như lúc pause để resolve interruption
        # (SDK tự khớp tool theo tên trong agent.tools, không phải kernel tự
        # chạy tool trực tiếp như LangChainKernel/OpenAIAgentsKernel resume()).
        # Phát hiện lần đầu chạy test thật: thiếu bước này → "Tool ... not
        # found in agent" khi resume.
        published = await self._spec_registry.get_by_hash(
            "agent", run_record.root_executable_id, run_record.root_definition_hash
        )
        spec = (
            AgentSpec.model_validate(published.content)
            if published
            else AgentSpec(id=run_record.root_executable_id, version=run_record.root_executable_version)
        )
        context: dict[str, Any] = dict(updates)
        tools = self._build_tools(spec, run_id, context)
        agent = Agent(name=spec.id, instructions="", tools=tools, model=self._model)

        # `RunState.to_json()`/`from_json()` — tên gọi gây hiểu nhầm, thực chất
        # nhận/trả `dict[str, Any]` JSON-compatible (KHÔNG phải chuỗi JSON) —
        # phát hiện khi chạy thật (`UserError: Run state JSON must be an
        # object` khi lỡ truyền chuỗi đã json.dumps()).
        state = await RunState.from_json(agent, checkpoint.serialized_state)

        approved_calls = updates.get("approved_tool_calls", {})
        for interruption in state.get_interruptions():
            call_id = interruption.call_id
            if call_id in approved_calls or updates.get("approved") is True:
                state.approve(interruption)
            else:
                state.reject(interruption, rejection_message=updates.get("rejection_message"))

        return await self._invoke_and_translate(
            run_id=run_id,
            agent=agent,
            sdk_input=state,
            correlation_id=correlation_id,
        )

    async def cancel(self, run_id: str, reason: Optional[str] = None) -> bool:
        self._cancelled_runs.add(run_id)
        run_record = await self._repo.get_run(run_id)
        if run_record:
            await self._repo.update_run_status(
                run_id, status=RunStatus.CANCELLED, error_details={"reason": reason or "Cancelled by user"}
            )
            await self._emit_event(run_id, "run.failed", {"status": "cancelled", "reason": reason}, run_record.correlation_id)
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

    async def _invoke_and_translate(
        self,
        *,
        run_id: str,
        agent: Agent,
        sdk_input: Any,
        correlation_id: str,
    ) -> RunResult:
        if run_id in self._cancelled_runs:
            return RunResult(run_id=run_id, status=RunStatus.CANCELLED)

        hooks = _CancellationHooks(run_id, self._cancelled_runs)
        try:
            result = await Runner.run(agent, sdk_input, hooks=hooks, max_turns=10)
        except _RunCancelled:
            return RunResult(run_id=run_id, status=RunStatus.CANCELLED)
        except AgentRuntimeError:
            raise
        except Exception as exc:
            error = AgentRuntimeError(
                RuntimeErrorCode.MODEL_PROVIDER_ERROR,
                f"OpenAI Agents SDK run failed: {exc}",
                retryable=True,
                cause=exc,
            )
            error_details = error.to_error_details()
            await self._repo.update_run_status(run_id, status=RunStatus.FAILED, error_details=error_details)
            await self._emit_event(run_id, "run.failed", error_details, correlation_id)
            return RunResult(run_id=run_id, status=RunStatus.FAILED, errors=[error.message])

        interruptions: list[ToolApprovalItem] = result.interruptions or []
        if interruptions:
            step_index = uuid.uuid4().hex[:8]
            ckpt_ref = f"ckpt_{run_id}_{step_index}"
            # `to_json()` trả `dict[str, Any]` JSON-compatible, không phải chuỗi
            # JSON (tên gọi gây hiểu nhầm) — lưu thẳng vào `serialized_state`
            # (đã là `dict[str, Any]`).
            state_dict = result.to_state().to_json()

            checkpoint = RunCheckpointRecord(
                checkpoint_ref=ckpt_ref,
                run_id=run_id,
                sequence_no=0,
                step_name=interruptions[0].tool_name,
                state_kind="openai_agents_sdk_run_state",
                serialized_state=state_dict,
            )
            await self._repo.save_checkpoint(checkpoint)
            await self._emit_event(run_id, "checkpoint.created", {"checkpoint_ref": ckpt_ref}, correlation_id)

            waits: list[WaitDescriptor] = []
            for interruption in interruptions:
                call_id = interruption.call_id
                tool_name = interruption.tool_name

                tc_record = RunToolCallRecord(
                    tool_call_id=call_id,
                    run_id=run_id,
                    capability_id=tool_name,
                    payload_hash=str(hash(json.dumps(interruption.arguments, sort_keys=True, default=str))),
                    input_payload=json.loads(interruption.arguments) if isinstance(interruption.arguments, str) else interruption.arguments,
                    status="pending",
                )
                await self._repo.save_tool_call(tc_record)

                appr_id = f"appr_{uuid.uuid4().hex[:12]}"
                approval = RunApprovalRecord(
                    approval_id=appr_id,
                    run_id=run_id,
                    tool_call_id=call_id,
                    checkpoint_ref=ckpt_ref,
                    status="pending",
                    action=tool_name,
                    subject=f"Approval requested for tool {tool_name}",
                )
                await self._repo.create_approval(approval)
                await self._emit_event(
                    run_id, "approval.required", {"approval_id": appr_id, "tool_call_id": call_id, "action": tool_name}, correlation_id
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

            await self._repo.update_run_status(run_id, status=RunStatus.WAITING_APPROVAL)
            await self._emit_event(run_id, "run.waiting", {"waits": [w.model_dump() for w in waits]}, correlation_id)
            return RunResult(run_id=run_id, status=RunStatus.WAITING_APPROVAL, interruptions_waits=waits)

        final_out = result.final_output
        await self._repo.update_run_status(run_id, status=RunStatus.COMPLETED, final_output=final_out)
        await self._emit_event(run_id, "run.completed", {"final_output": final_out}, correlation_id)
        return RunResult(run_id=run_id, status=RunStatus.COMPLETED, final_output=final_out, usage={})
