from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from agent_core.capabilities.canonicalization import compute_payload_hash
from agent_core.capabilities.gateway import GatewayExecutionRequest
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.contracts.capability import CapabilitySpec
from agent_core.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent_core.contracts.run import RunRequest, RunResult, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.contracts.wait import WaitDescriptor, WaitKind
from agent_core.prompts.bundle import PromptBundle
from agent_core.registry.publisher import publish_agent_spec
from agent_core.registry.repository import InMemorySpecRegistryRepository, SpecRegistryRepository
from agent_core.runs.models import (
    RunApprovalRecord,
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent_core.runs.repository import InMemoryRunRepository, RunRepository
from agent_core.skills.resolver import SkillResolver
from pydantic_ai import Agent, DeferredToolRequests, DeferredToolResults
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.tools import Tool

__all__ = ["PydanticAIKernel"]


class PydanticAIKernel:
    """`ExecutionKernel` implementation dùng PydanticAI `Agent.run()` THẬT.

    Theo Wave 10 (COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md
    Phần 4) — adapter TUỲ CHỌN theo `ADR-RUNTIME-001`, KHÔNG thay kernel mặc
    định production.

    Approval-gate dùng cơ chế "deferred tools" NATIVE của PydanticAI
    (`Tool(..., requires_approval=True)` → `DeferredToolRequests` khi model
    gọi tool đó → `DeferredToolResults` để resume) thay vì tự cài policy
    evaluator can thiệp vào vòng lặp như 2 kernel kia — PydanticAI đã có sẵn
    khái niệm này ở tầng framework, tái dùng thay vì viết lại.

    Checkpoint dùng `result.all_messages_json()`/`ModelMessagesTypeAdapter`
    (cơ chế serialize gốc của PydanticAI cho `message_history`), không tự
    viết serializer riêng.
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
    ) -> None:
        self._repo = repository or InMemoryRunRepository()
        self._spec_registry = spec_registry or InMemorySpecRegistryRepository()
        self._skill_resolver = SkillResolver(self._spec_registry)
        self._capability_registry = capability_registry
        self._model = model
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

    def _build_tools(self, spec: AgentSpec, run_id: str, context: dict[str, Any]) -> list[Tool]:
        if not self._capability_registry or not spec.capability_refs:
            return []
        tools: list[Tool] = []
        for cap_id in spec.capability_refs:
            reg = self._capability_registry.get(cap_id)
            if not reg:
                continue
            tools.append(self._make_tool(reg.spec, run_id, context))
        return tools

    def _make_tool(self, cap_spec: CapabilitySpec, run_id: str, context: dict[str, Any]) -> Tool:
        requires_approval = self._evaluate_policy(cap_spec.id, {}, context) == "REQUIRE_APPROVAL"

        async def _fn(**kwargs: Any) -> Any:
            call_id = f"call_{uuid.uuid4().hex[:8]}"
            await self._emit_event(
                run_id, "tool.started", {"tool_call_id": call_id, "tool": cap_spec.id}
            )
            result = await self._execute_tool(
                cap_spec.id, kwargs, run_id=run_id, tool_call_id=call_id
            )
            await self._emit_event(
                run_id, "tool.completed", {"tool_call_id": call_id, "result": result}
            )
            return result

        _fn.__name__ = cap_spec.id.replace(".", "_")
        return Tool(
            _fn,
            name=cap_spec.id,
            description=cap_spec.description or "",
            requires_approval=requires_approval,
        )

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

        if run_id in self._cancelled_runs:
            return RunResult(run_id=run_id, status=RunStatus.CANCELLED)

        system_prompt = PromptBundle(
            agent_instructions=spec.instructions,
            skill_instructions=skill_texts,
            locale=request.locale,
        ).render()

        context: dict[str, Any] = dict(request.input)
        tools = self._build_tools(spec, run_id, context)
        agent: Agent = Agent(
            model=self._model,
            instructions=system_prompt,
            tools=tools,
            output_type=[str, DeferredToolRequests],
        )

        prompt_content = ""
        if request.input:
            prompt_content = (
                request.input.get("prompt")
                or request.input.get("message")
                or json.dumps(request.input)
            )

        return await self._invoke_and_translate(
            run_id=run_id,
            agent=agent,
            correlation_id=correlation_id,
            user_prompt=str(prompt_content),
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
        context: dict[str, Any] = dict(updates)
        tools = self._build_tools(spec, run_id, context)
        agent: Agent = Agent(
            model=self._model, tools=tools, output_type=[str, DeferredToolRequests]
        )

        message_history: list[ModelMessage] = ModelMessagesTypeAdapter.validate_python(
            checkpoint.serialized_state["messages"]
        )
        pending_requests: DeferredToolRequests = _deferred_requests_from_dict(
            checkpoint.serialized_state["deferred_requests"]
        )

        approved_calls = updates.get("approved_tool_calls", {})
        approvals: dict[str, bool] = {}
        for call in pending_requests.approvals:
            call_id = call.tool_call_id
            approvals[call_id] = bool(call_id in approved_calls or updates.get("approved") is True)

        deferred_results = pending_requests.build_results(approvals=approvals)

        return await self._invoke_and_translate(
            run_id=run_id,
            agent=agent,
            correlation_id=correlation_id,
            message_history=message_history,
            deferred_tool_results=deferred_results,
        )

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

    async def _invoke_and_translate(
        self,
        *,
        run_id: str,
        agent: Agent,
        correlation_id: str,
        user_prompt: str | None = None,
        message_history: list[ModelMessage] | None = None,
        deferred_tool_results: DeferredToolResults | None = None,
    ) -> RunResult:
        if run_id in self._cancelled_runs:
            return RunResult(run_id=run_id, status=RunStatus.CANCELLED)

        try:
            kwargs: dict[str, Any] = {}
            if message_history is not None:
                kwargs["message_history"] = message_history
            if deferred_tool_results is not None:
                kwargs["deferred_tool_results"] = deferred_tool_results
            result = await agent.run(user_prompt, **kwargs)
        except AgentRuntimeError:
            raise
        except Exception as exc:
            error = AgentRuntimeError(
                RuntimeErrorCode.MODEL_PROVIDER_ERROR,
                f"PydanticAI run failed: {exc}",
                retryable=True,
                cause=exc,
            )
            error_details = error.to_error_details()
            await self._repo.update_run_status(
                run_id, status=RunStatus.FAILED, error_details=error_details
            )
            await self._emit_event(run_id, "run.failed", error_details, correlation_id)
            return RunResult(run_id=run_id, status=RunStatus.FAILED, errors=[error.message])

        output = result.output
        if isinstance(output, DeferredToolRequests):
            step_index = uuid.uuid4().hex[:8]
            ckpt_ref = f"ckpt_{run_id}_{step_index}"

            messages_json = result.all_messages_json()
            checkpoint = RunCheckpointRecord(
                checkpoint_ref=ckpt_ref,
                run_id=run_id,
                sequence_no=0,
                step_name=output.approvals[0].tool_name if output.approvals else None,
                state_kind="pydantic_ai_run_state",
                serialized_state={
                    "messages": json.loads(messages_json),
                    "deferred_requests": _deferred_requests_to_dict(output),
                },
            )
            await self._repo.save_checkpoint(checkpoint)
            await self._emit_event(
                run_id, "checkpoint.created", {"checkpoint_ref": ckpt_ref}, correlation_id
            )

            waits: list[WaitDescriptor] = []
            for call in output.approvals:
                call_id = call.tool_call_id
                tool_name = call.tool_name

                tc_record = RunToolCallRecord(
                    tool_call_id=call_id,
                    run_id=run_id,
                    capability_id=tool_name,
                    payload_hash=compute_payload_hash(call.args),
                    input_payload=call.args_as_dict() if hasattr(call, "args_as_dict") else {},
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

        final_out = output
        await self._repo.update_run_status(
            run_id, status=RunStatus.COMPLETED, final_output=final_out
        )
        await self._emit_event(run_id, "run.completed", {"final_output": final_out}, correlation_id)
        return RunResult(
            run_id=run_id, status=RunStatus.COMPLETED, final_output=final_out, usage={}
        )


def _deferred_requests_to_dict(requests: DeferredToolRequests) -> dict[str, Any]:
    """Serialize `DeferredToolRequests` (dataclass, không phải Pydantic model)
    sang dict JSON-compatible cho checkpoint — chỉ giữ field cần để build lại
    `build_results()` khi resume (tool_call_id/tool_name/args)."""
    return {
        "calls": [
            {"tool_call_id": c.tool_call_id, "tool_name": c.tool_name, "args": c.args}
            for c in requests.calls
        ],
        "approvals": [
            {"tool_call_id": c.tool_call_id, "tool_name": c.tool_name, "args": c.args}
            for c in requests.approvals
        ],
    }


def _deferred_requests_from_dict(data: dict[str, Any]) -> DeferredToolRequests:
    from pydantic_ai.messages import ToolCallPart

    return DeferredToolRequests(
        calls=[
            ToolCallPart(tool_name=c["tool_name"], args=c["args"], tool_call_id=c["tool_call_id"])
            for c in data["calls"]
        ],
        approvals=[
            ToolCallPart(tool_name=c["tool_name"], args=c["args"], tool_call_id=c["tool_call_id"])
            for c in data["approvals"]
        ],
    )
