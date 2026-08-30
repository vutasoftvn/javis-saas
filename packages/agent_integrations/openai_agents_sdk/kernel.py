from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable
from typing import Any

from agent.capabilities.canonicalization import compute_payload_hash
from agent.capabilities.gateway import GatewayExecutionRequest
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
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
from agents import Agent, FunctionTool, RunHooks, Runner, RunState

from agent_integrations.openai_agents_sdk.model_guard import ModelInputGuard

__all__ = ["RealOpenAIAgentsSDKKernel"]


class _RunCancelled(Exception):
    """Nội bộ — raise trong hook `on_llm_start` để chặn `Runner.run()` tiếp
    tục turn kế tiếp khi Run đã bị cancel giữa chừng (SDK không expose điểm
    dừng nào chi tiết hơn giữa các turn cho caller ngoài)."""


class _CancellationHooks(RunHooks):
    def __init__(
        self,
        run_id: str,
        cancelled_runs: set[str],
        model_input_guard: ModelInputGuard | None = None,
        context: Any | None = None,
    ) -> None:
        self._run_id = run_id
        self._cancelled_runs = cancelled_runs
        self._model_input_guard = model_input_guard
        self._context = context or {}

    async def on_llm_start(self, context, agent, system_prompt, input_items) -> None:
        if self._model_input_guard:
            await self._model_input_guard.assert_before_model_call(self._context)
        if self._run_id in self._cancelled_runs:
            raise _RunCancelled(self._run_id)


class RealOpenAIAgentsSDKKernel:
    """`ExecutionKernel` implementation dùng `agents.Runner` THẬT của OpenAI
    Agents SDK (package `openai-agents`, không phải
    `packages/agent/kernel/openai_agents_kernel.py` — class đó tên trùng
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
        repository: RunRepository | None = None,
        spec_registry: SpecRegistryRepository | None = None,
        capability_registry: CapabilityRegistry | None = None,
        model: Any | None = None,
        capability_executor: Callable[..., Any] | None = None,
        policy_evaluator: Callable[..., Any] | None = None,
        compliance_resolver: Any | None = None,
        model_input_guard: ModelInputGuard | None = None,
    ) -> None:
        self._repo = repository or InMemoryRunRepository()
        self._spec_registry = spec_registry or InMemorySpecRegistryRepository()
        self._skill_resolver = SkillResolver(self._spec_registry)
        self._capability_registry = capability_registry
        self._model = model
        self._capability_executor = capability_executor
        self._policy_evaluator = policy_evaluator
        self._compliance_resolver = compliance_resolver
        self._model_input_guard = model_input_guard
        self._cancelled_runs: set[str] = set()

        # Nhớ lại approval TRUE/FALSE gần nhất cho mỗi tool_call_id đã policy-
        # evaluate — `FunctionTool.needs_approval` của SDK là callable đồng bộ
        # với chữ ký (context, args, call_id), không nhận policy_evaluator của
        # COSA trực tiếp nên phải cache quyết định ở đây trước khi Runner gọi.
        self._pending_decisions: dict[str, str] = {}

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

    def _evaluate_policy(
        self, tool_name: str, args: dict[str, Any], context: dict[str, Any]
    ) -> str:
        if self._policy_evaluator:
            try:
                decision_obj = self._policy_evaluator(tool_name, args, context)
            except TypeError:
                decision_obj = self._policy_evaluator(tool_name, args)
        elif "transfer" in tool_name or "payout" in tool_name or "deploy" in tool_name:
            decision_obj = "REQUIRE_APPROVAL"
        else:
            decision_obj = "ALLOW"
        return (
            decision_obj.outcome.value
            if hasattr(decision_obj, "outcome")
            else str(decision_obj).upper()
        )

    def _build_tools(self, spec: AgentSpec, run_id: str, context: dict[str, Any]) -> list[Any]:
        if not self._capability_registry or not spec.capability_refs:
            return []

        compliance_snapshot = context.get("compliance_snapshot")
        allowed_set: set[str] | None = None
        if compliance_snapshot:
            allowed = (
                compliance_snapshot.get("allowed_capabilities")
                if isinstance(compliance_snapshot, dict)
                else getattr(compliance_snapshot, "allowed_capabilities", None)
            )
            if allowed is not None:
                allowed_set = set(allowed)

        tools: list[FunctionTool] = []
        for cap_id in spec.capability_refs:
            if allowed_set is not None and "*" not in allowed_set and cap_id not in allowed_set:
                continue
            reg = self._capability_registry.get(cap_id)

            if not reg:
                continue
            cap_spec: CapabilitySpec = reg.spec
            tools.append(self._make_tool(cap_spec, run_id, context))
        return tools

    def _make_tool(
        self, cap_spec: CapabilitySpec, run_id: str, context: dict[str, Any]
    ) -> FunctionTool:
        async def _on_invoke(tool_context: Any, args_json: str) -> Any:
            args = json.loads(args_json) if args_json else {}
            call_id = getattr(tool_context, "tool_call_id", None) or f"call_{uuid.uuid4().hex[:8]}"
            await self._emit_event(
                run_id, "tool.started", {"tool_call_id": call_id, "tool": cap_spec.id}
            )
            result = await self._execute_tool(
                cap_spec.id,
                args,
                run_id=run_id,
                tool_call_id=call_id,
                context=context,
                cap_spec=cap_spec,
            )
            await self._emit_event(
                run_id, "tool.completed", {"tool_call_id": call_id, "result": result}
            )
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

    async def _execute_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        *,
        run_id: str,
        tool_call_id: str,
        context: dict[str, Any] | None = None,
        cap_spec: CapabilitySpec | None = None,
    ) -> Any:
        ctx = context or {}
        workspace_id = str(ctx.get("workspace_id") or "")
        principal = str(ctx.get("principal") or "system")
        checkpoint_ref = str(ctx.get("checkpoint_ref") or f"ckpt_{run_id}_{tool_call_id}")
        exec_mode = ctx.get("execution_mode") or ExecutionMode.AGENT

        # Task 5 — `_company_delegation_token` (raw JWT, do
        # apps.cosa.compliance.resolver.ComplianceResolver mint) KHÔNG bao
        # giờ được đưa vào InvocationContext.metadata — field đó có thể bị
        # log/serialize cho audit. `delegation_identity` (jti, đã an toàn để
        # audit) đi vào field frozen riêng của InvocationContext thay vì
        # metadata rời rạc.
        raw_delegation_token = ctx.get("_company_delegation_token")
        delegation_identity = ctx.get("company_delegation_ref") or ctx.get("delegation_identity")
        safe_metadata = {k: v for k, v in ctx.items() if k != "_company_delegation_token"}

        inv_ctx = InvocationContext(
            run_id=run_id,
            tool_call_id=tool_call_id,
            checkpoint_ref=checkpoint_ref,
            workspace_id=workspace_id,
            principal=principal,
            conversation_id=ctx.get("conversation_id"),
            correlation_id=ctx.get("correlation_id"),
            policy_snapshot=ctx.get("policy_snapshot"),
            policy_snapshot_ref=ctx.get("policy_snapshot_ref"),
            policy_snapshot_version=ctx.get("policy_snapshot_version"),
            root_spec_identity=ctx.get("root_spec_identity"),
            capability_identity=tool_name,
            execution_mode=exec_mode
            if isinstance(exec_mode, ExecutionMode)
            else ExecutionMode.AGENT,
            delegation_identity=str(delegation_identity) if delegation_identity else None,
            metadata=safe_metadata,
        )

        # Task 5 §Step 4 — header xác thực cho các lệnh gọi Company
        # (CompanyServiceClient) trong PHẠM VI đúng tool call này, dựng
        # HOÀN TOÀN từ InvocationContext (run_id, workspace_id,
        # capability_identity, delegation token đã resolve trước kernel.run)
        # — KHÔNG BAO GIỜ đọc từ `args` (đối số do model sinh ra). Không có
        # raw_delegation_token (vd. run không cấu hình compliance resolver —
        # dev/test kernel-level) ⇒ không set Authorization, cuộc gọi Company
        # đi không có header xác thực như hành vi cũ trước Task 5.
        from agent.capabilities.outbound_headers import (
            reset_outbound_headers,
            set_outbound_headers,
        )

        outbound_headers: dict[str, str] = {
            "X-Workspace-Id": inv_ctx.workspace_id,
            "X-COSA-Run-Id": inv_ctx.run_id,
            "X-COSA-Capability-Id": inv_ctx.capability_identity or tool_name,
        }
        if raw_delegation_token:
            outbound_headers["Authorization"] = f"Bearer {raw_delegation_token}"
        headers_token = set_outbound_headers(outbound_headers)

        try:
            result = None
            if self._capability_executor:
                try:
                    if asyncio.iscoroutinefunction(self._capability_executor):
                        result = await self._capability_executor(tool_name, args, inv_ctx)
                    else:
                        result = self._capability_executor(tool_name, args, inv_ctx)
                except TypeError:
                    pass

                if result is None:
                    try:
                        if asyncio.iscoroutinefunction(self._capability_executor):
                            result = await self._capability_executor(tool_name, args)
                        else:
                            result = self._capability_executor(tool_name, args)
                    except TypeError:
                        req = GatewayExecutionRequest(
                            run_id=run_id,
                            capability_id=tool_name,
                            input_payload=args,
                            principal=principal,
                            checkpoint_ref=checkpoint_ref,
                            tool_call_id=tool_call_id,
                            execution_mode=exec_mode
                            if isinstance(exec_mode, ExecutionMode)
                            else ExecutionMode.AGENT,
                            workspace_id=workspace_id,
                            context=inv_ctx,
                        )
                        if asyncio.iscoroutinefunction(self._capability_executor):
                            res = await self._capability_executor(req)
                        else:
                            res = self._capability_executor(req)
                        result = res.output_payload if hasattr(res, "output_payload") else res
        finally:
            reset_outbound_headers(headers_token)

        if result is None:
            result = {"status": "success", "executed_tool": tool_name, "params": args}

        if self._model_input_guard:
            result = await self._model_input_guard.prepare_tool_output(
                inv_ctx.metadata, tool_name, result
            )

        return result

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        run_id = request.run_id or f"run_{uuid.uuid4().hex[:16]}"
        correlation_id = request.correlation_id or run_id

        pinned_spec = spec if spec.definition_hash else spec.with_hash()
        await publish_agent_spec(
            pinned_spec, repository=self._spec_registry, publisher=request.principal
        )

        skill_texts: list[str] = []
        if spec.pinned_skills:
            resolved_skills = await self._skill_resolver.resolve(spec.pinned_skills)
            skill_texts = [s.instructions for s in resolved_skills if s.instructions]

        # Task 5 — worker (apps/cosa/worker/handlers.py::_execute_run_task_inner)
        # giờ resolve compliance TRƯỚC khi gọi kernel.run(), đúng vị trí "mint
        # sau khi run_id + AgentSpec capability_ids đã resolve" — kernel chỉ
        # còn tự resolve như fallback khi caller khác gọi kernel.run() trực
        # tiếp mà chưa resolve trước (vd. test kernel-level, hoặc composition
        # root khác không đi qua worker COSA). Guard bằng key
        # "compliance_snapshot" đã có trong metadata — tránh mint delegation
        # 2 lần cho cùng 1 run khi worker đã resolve.
        if self._compliance_resolver and "compliance_snapshot" not in request.metadata:
            compliance_metadata = await self._compliance_resolver.resolve_for_run(request, spec)
            request.metadata.update(compliance_metadata)

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

        system_prompt = PromptBundle(
            agent_instructions=spec.instructions,
            skill_instructions=skill_texts,
            locale=request.locale,
        ).render()

        # request.metadata (không phải request.input — đó là literal prompt
        # text/args) là nơi đúng để mang ambient governance context (vd.
        # policy_snapshot) cho policy_evaluator — cùng fix đã áp dụng cho
        # ManualToolLoopKernel (packages/agent/kernel/openai_agents_kernel.py),
        # theo COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §5.3.
        context: dict[str, Any] = dict(request.metadata)
        context["workspace_id"] = request.workspace_id
        context["principal"] = request.principal
        context["correlation_id"] = correlation_id
        context["conversation_id"] = request.conversation_id
        context["execution_mode"] = request.execution_mode
        context["root_spec_identity"] = spec.id
        context["root_definition_hash"] = pinned_spec.definition_hash

        compliance_snapshot = context.get("compliance_snapshot")
        if compliance_snapshot:
            allowed = (
                compliance_snapshot.get("allowed_capabilities")
                if isinstance(compliance_snapshot, dict)
                else getattr(compliance_snapshot, "allowed_capabilities", None)
            )
            if allowed is not None:
                allowed_set = set(allowed)
                unbound = (
                    [c for c in (spec.capability_refs or []) if c not in allowed_set]
                    if "*" not in allowed_set
                    else []
                )
                if unbound:
                    await self._repo.update_run_status(run_id, RunStatus.FAILED)

                    await self._emit_event(
                        run_id,
                        "run.failed",
                        {"error": f"Capabilities not bound in compliance snapshot: {unbound}"},
                        correlation_id,
                    )
                    return RunResult(
                        run_id=run_id,
                        status=RunStatus.FAILED,
                        errors=[f"Capabilities not bound in compliance snapshot: {unbound}"],
                    )

        tools = self._build_tools(spec, run_id, context)
        agent = Agent(
            name=spec.id,
            instructions=system_prompt,
            tools=tools,
            model=self._model,
        )

        prompt_content = ""
        if request.input:
            prompt_content = (
                request.input.get("prompt")
                or request.input.get("message")
                or json.dumps(request.input)
            )

        if self._model_input_guard:
            try:
                prompt_content = await self._model_input_guard.prepare_initial_input(
                    context, str(prompt_content)
                )
            except Exception as e:
                await self._repo.update_run_status(run_id, RunStatus.FAILED)
                await self._emit_event(
                    run_id,
                    "run.failed",
                    {"error": str(e)},
                    correlation_id,
                )
                return RunResult(
                    run_id=run_id,
                    status=RunStatus.FAILED,
                    errors=[str(e)],
                )

        from opentelemetry import trace

        tracer = trace.get_tracer("agent_integrations.openai_agents_sdk")
        with tracer.start_as_current_span(
            "kernel.run",
            attributes={
                "run_id": run_id,
                "agent_spec_id": spec.id,
                "workspace_id": request.workspace_id or "",
                "principal": request.principal,
            },
        ):
            return await self._invoke_and_translate(
                run_id=run_id,
                agent=agent,
                sdk_input=str(prompt_content),
                correlation_id=correlation_id,
                spec=spec,
                context=context,
            )

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

        published = await self._spec_registry.get_by_hash(
            "agent", run_record.root_executable_id, run_record.root_definition_hash or ""
        )
        spec = (
            AgentSpec.model_validate(published.content)
            if published
            else AgentSpec(
                id=run_record.root_executable_id, version=run_record.root_executable_version
            )
        )
        if self._compliance_resolver and run_record.workspace_id:
            dummy_req = RunRequest(
                root_executable_ref="agent:" + spec.id,
                workspace_id=run_record.workspace_id,
                principal="system",
                metadata=updates,
            )
            compliance_metadata = await self._compliance_resolver.resolve_for_run(dummy_req, spec)
            updates.update(compliance_metadata)

        context: dict[str, Any] = dict(updates)
        tools = self._build_tools(spec, run_id, context)

        agent = Agent(name=spec.id, instructions="", tools=tools, model=self._model)

        state = await RunState.from_json(agent, checkpoint.serialized_state)

        approved_calls = updates.get("approved_tool_calls", {})
        for interruption in state.get_interruptions():
            call_id = interruption.call_id
            if call_id in approved_calls or updates.get("approved") is True:
                state.approve(interruption)
            elif updates.get("approved") is False:
                state.reject(interruption)

        from opentelemetry import trace

        tracer = trace.get_tracer("agent_integrations.openai_agents_sdk")
        with tracer.start_as_current_span(
            "kernel.resume",
            attributes={
                "run_id": run_id,
                "checkpoint_ref": checkpoint_ref,
                "agent_spec_id": spec.id,
            },
        ):
            return await self._invoke_and_translate(
                run_id=run_id,
                agent=agent,
                sdk_input=state,
                correlation_id=correlation_id,
                spec=spec,
                context=context,
            )

    async def cancel(self, run_id: str, reason: str | None = None) -> bool:
        self._cancelled_runs.add(run_id)
        run_record = await self._repo.get_run(run_id)
        if run_record and run_record.status == RunStatus.RUNNING:
            await self._repo.update_run_status(run_id, RunStatus.CANCELLED)
            await self._emit_event(
                run_id,
                "run.cancelled",
                {"reason": reason} if reason else {},
                run_record.correlation_id or run_id,
            )
        return True

    async def _invoke_and_translate(
        self,
        *,
        run_id: str,
        agent: Agent,
        sdk_input: Any,
        correlation_id: str,
        spec: AgentSpec | None = None,
        context: dict[str, Any] | None = None,
    ) -> RunResult:
        hooks = _CancellationHooks(
            run_id=run_id,
            cancelled_runs=self._cancelled_runs,
            model_input_guard=self._model_input_guard,
            context=context,
        )

        runner = Runner()
        try:
            sdk_result = await runner.run(agent, sdk_input, hooks=hooks)
        except _RunCancelled:
            await self._repo.update_run_status(run_id, RunStatus.CANCELLED)
            await self._emit_event(run_id, "run.cancelled", {}, correlation_id)
            return RunResult(run_id=run_id, status=RunStatus.CANCELLED)
        except Exception as e:
            await self._repo.update_run_status(run_id, RunStatus.FAILED)
            await self._emit_event(run_id, "run.failed", {"error": str(e)}, correlation_id)
            return RunResult(run_id=run_id, status=RunStatus.FAILED, errors=[str(e)])

        interruptions = sdk_result.interruptions
        if interruptions:
            serialized_state = sdk_result.to_state().to_json()
            ckpt_ref = f"ckpt_{run_id}_{uuid.uuid4().hex[:8]}"
            await self._repo.save_checkpoint(
                RunCheckpointRecord(
                    checkpoint_ref=ckpt_ref,
                    run_id=run_id,
                    sequence_no=0,
                    serialized_state=serialized_state,
                )
            )
            await self._repo.update_run_status(run_id, RunStatus.WAITING_APPROVAL)
            await self._emit_event(
                run_id, "checkpoint.created", {"checkpoint_ref": ckpt_ref}, correlation_id
            )

            waits: list[WaitDescriptor] = []
            for interruption in interruptions:
                call_id = interruption.call_id or f"call_{uuid.uuid4().hex[:12]}"
                tool_name = interruption.tool_name or ""
                raw_args: Any = interruption.arguments or {}
                args_payload = (
                    json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                )
                if not isinstance(args_payload, dict):
                    args_payload = {"value": args_payload}

                tc_record = RunToolCallRecord(
                    tool_call_id=call_id,
                    run_id=run_id,
                    capability_id=tool_name,
                    payload_hash=compute_payload_hash(args_payload),
                    input_payload=args_payload,
                    status="pending",
                )
                await self._repo.save_tool_call(tc_record)

                appr_id = f"appr_{run_id}_{call_id}"
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

            await self._repo.update_run_status(run_id, status=RunStatus.WAITING_APPROVAL)
            await self._emit_event(
                run_id, "run.waiting", {"waits": [w.model_dump() for w in waits]}, correlation_id
            )
            return RunResult(
                run_id=run_id, status=RunStatus.WAITING_APPROVAL, interruptions_waits=waits
            )

        final_out = sdk_result.final_output
        usage_dict = getattr(sdk_result, "usage", {}) or {}

        if spec and spec.output_schema:
            is_valid, parsed_out, errs = validate_output_payload(final_out, spec.output_schema)
            if not is_valid:
                val_fail = ValidationFailure(is_valid=False, errors=errs, raw_output=final_out)
                await self._repo.update_run_status(
                    run_id, status=RunStatus.FAILED, final_output=val_fail.model_dump()
                )
                await self._emit_event(
                    run_id,
                    "run.failed",
                    {"error": f"Output validation failed: {errs}"},
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
        await self._emit_event(run_id, "run.completed", {"final_output": final_out}, correlation_id)
        return RunResult(
            run_id=run_id,
            status=RunStatus.COMPLETED,
            final_output=final_out,
            usage=usage_dict if isinstance(usage_dict, dict) else {},
        )
