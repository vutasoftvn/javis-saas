import contextlib
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from agent.artifacts import WorkspaceArtifact
from agent.contracts.run import RunStatus
from agent.contracts.spec import AgentSpec
from agent.conversations.models import ConversationRecord, MessageRecord

from apps.cosa.agents.specs import (
    COSA_FINANCE_AGENT_SPEC,
    COSA_MARKETING_AGENT_SPEC,
    COSA_OPERATIONS_AGENT_SPEC,
)
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.config.planes import resolve_platform_control_plane_url
from apps.cosa.observability.logging import log_context
from apps.cosa.observability.metrics import record_model_tokens, record_run_outcome
from apps.cosa.observability.otel import inject_trace_carrier, trace_span
from apps.cosa.policies.company_policy_client import CosaTenantPolicyError
from apps.cosa.worker.autopilot_run import (
    resume_customer_support_autopilot,
    run_customer_support_autopilot,
)
from apps.cosa.worker.copilot_run import run_customer_support_copilot
from apps.cosa.worker.run_core import (
    RunCoreError,
    prepare_request,
    resolve_spec,
    run_kernel,
)

logger = logging.getLogger(__name__)

# Ánh xạ agent_profile -> AgentSpec cho nhánh dispatch thường (không bao gồm
# customer_support/customer_support_autopilot — 2 profile đó rẽ nhánh riêng
# ở execute_run_task trước khi tới đây). "founder_assistant" là default thật
# đang được Flutter gửi cho MỌI conversation mới (chat_controller.dart
# createNewConversation() không truyền agentProfile) — alias sang Operations
# để giữ đúng hành vi hiện tại, không phải bug cần sửa.
_AGENT_PROFILE_SPECS: dict[str, AgentSpec] = {
    "operations": COSA_OPERATIONS_AGENT_SPEC,
    "founder_assistant": COSA_OPERATIONS_AGENT_SPEC,
    "finance": COSA_FINANCE_AGENT_SPEC,
    "marketing": COSA_MARKETING_AGENT_SPEC,
}


__all__ = [
    "execute_resume_task",
    "execute_run_task",
    "execute_scheduled_session_task",
]


async def _append_message(
    plane: CosaAgentPlane,
    *,
    conversation_id: str,
    role: str,
    content: str,
    run_id: str | None = None,
    status_: str = "completed",
) -> MessageRecord:
    message = MessageRecord(
        conversation_id=conversation_id,
        role=role,
        content=content,
        run_id=run_id,
        status=status_,
    )
    return await plane.conversation_repository.add_message(message)


async def execute_run_task(
    plane: CosaAgentPlane,
    stream_mgr: CosaEventStreamManager,
    payload: dict[str, Any],
) -> None:
    """Thực thi 1 run mới — trước đây là `asyncio.create_task(_execute_canonical_
    run_task(...))` sống trong HTTP process (`apps/cosa/api/routes.py`), giờ
    chạy trong worker process riêng, dispatch bởi `apps/cosa/worker/main.py`
    sau khi claim task + acquire lease durable — theo
    COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §5/§29.6 Phase 4.
    """
    run_id = payload["run_id"]
    agent_profile = payload.get("agent_profile") or "operations"
    workspace_id = payload["workspace_id"]

    if agent_profile == "customer_support" or payload.get("copilot") is True:
        with log_context(run_id=run_id, workspace_id=workspace_id):
            await run_customer_support_copilot(plane, stream_mgr, payload)
            return

    if agent_profile == "customer_support_autopilot":
        with log_context(run_id=run_id, workspace_id=workspace_id):
            await run_customer_support_autopilot(plane, stream_mgr, payload)
            return

    # Ensure correlation context is active for all log lines emitted within this handler.
    # worker/main.py already sets log_context for dispatch_one_task, but
    # execute_run_task can also be called directly from execute_scheduled_session_task.
    with log_context(run_id=run_id, workspace_id=workspace_id):
        await _execute_run_task_inner(plane, stream_mgr, payload)


async def _execute_run_task_inner(
    plane: CosaAgentPlane,
    stream_mgr: CosaEventStreamManager,
    payload: dict[str, Any],
) -> None:
    run_id = payload["run_id"]
    conversation_id = payload["conversation_id"]
    user_prompt = payload["user_prompt"]
    agent_profile = payload.get("agent_profile") or "operations"
    principal = payload["principal"]
    workspace_id = payload["workspace_id"]
    stream_repo = plane.stream_event_repository
    bearer_token = payload.get("delegation_token")
    if not bearer_token:
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content="Missing delegation token — run rejected",
            run_id=run_id,
            status_="failed",
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "missing_delegation_token"},
        )
        return

    local_spec = _AGENT_PROFILE_SPECS.get(agent_profile)
    if local_spec is None:
        # Trước đây mọi agent_profile lạ (kể cả "marketing") âm thầm rơi vào
        # Operations qua so khớp chuỗi "finance" in agent_profile — sửa dead
        # dispatch branch: log rõ ràng để phát hiện được profile chưa được
        # ánh xạ, vẫn fallback Operations (không hard-fail run của người dùng
        # vì 1 giá trị agent_profile chưa biết).
        logger.warning(
            "unmapped agent_profile %r, falling back to operations spec",
            agent_profile,
            extra={"run_id": run_id},
        )
        local_spec = COSA_OPERATIONS_AGENT_SPEC

    # Resolve PolicySnapshot TRƯỚC khi tạo run — §10.5 freshness invariant:
    # không xác nhận được current gate/tenant policy thật KHÔNG được coi là
    # ALLOW ngầm.
    try:
        snapshot = await plane.tenant_policy_client.get_snapshot(bearer_token, workspace_id)
    except CosaTenantPolicyError:
        # Task 6 — không interpolate exception thô (có thể lộ chi tiết nội bộ
        # từ Company tenant-policy service) vào message/event client-facing.
        # Log đầy đủ server-side kèm run_id để debug, client chỉ nhận mã lỗi
        # ổn định — cùng pattern với broad-failure branch bên dưới.
        logger.exception("tenant policy snapshot unavailable", extra={"run_id": run_id})
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content="Unable to verify tenant policy — run rejected",
            run_id=run_id,
            status_="failed",
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "policy_snapshot_unavailable"},
        )
        return

    # Resolve exact spec + dựng request + compliance qua apps/cosa/worker/
    # run_core.py (WGA int. point #2) — lõi dùng chung với headless task
    # goal_decomposition / workspace_task_sweep. Hành vi client-facing của
    # nhánh lỗi giữ nguyên: map RunCoreError.reason_code -> đúng message/event
    # cũ.
    try:
        spec = await resolve_spec(plane, run_id=run_id, local_spec=local_spec)
    except RunCoreError:
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content="Unable to resolve agent spec from registry — run rejected",
            run_id=run_id,
            status_="failed",
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "spec_resolution_unavailable"},
        )
        return

    await stream_mgr.emit(
        stream_repo,
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="run.started",
        payload={"run_id": run_id, "conversation_id": conversation_id, "goal": user_prompt},
    )
    await stream_mgr.emit(
        stream_repo,
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="reasoning.status",
        payload={"status": "thinking"},
    )
    await stream_mgr.emit(
        stream_repo,
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="message.started",
        payload={"role": "assistant"},
    )

    # Task 5 — forward context egress đã hash vào metadata để
    # ComplianceResolver.resolve_for_run dựng DataAccessClaim thật. Chỉ chứa
    # context đã hash, không có nội dung message thô.
    extra_md: dict[str, Any] = {}
    direct_message_data_access = payload.get("direct_message_data_access")
    if direct_message_data_access is not None:
        extra_md["direct_message_data_access"] = direct_message_data_access

    try:
        prep = await prepare_request(
            plane,
            spec=spec,
            run_id=run_id,
            prompt=user_prompt,
            principal=principal,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            policy_snapshot=snapshot,
            extra_metadata=extra_md or None,
        )
    except RunCoreError as exc:
        if exc.reason_code == "compliance_resolver_unavailable":
            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content="AI compliance resolver not configured — run rejected",
                run_id=run_id,
                status_="failed",
            )
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": "compliance_resolver_unavailable"},
            )
            return
        # compliance_denied — chỉ emit reason code, không leak str(exc).
        code = exc.compliance_code or "UNKNOWN"
        if code != "MISSING_DELEGATION_TOKEN":
            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content=f"AI compliance check failed — run rejected: {code}",
                run_id=run_id,
                status_="failed",
            )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "compliance_denied", "reason_code": code},
        )
        return

    _run_start = time.monotonic()
    try:
        run_result, _ = await run_kernel(plane, prep, workspace_id=workspace_id, run_id=run_id)

        _run_duration = time.monotonic() - _run_start

        if getattr(run_result, "usage", None):
            usage = run_result.usage
            p_tok = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            c_tok = usage.get("completion_tokens") or usage.get("output_tokens") or 0
            model_name = getattr(spec, "model_policy", {}).get("model", "deepseek-chat")
            with contextlib.suppress(Exception):
                record_model_tokens(model_name, p_tok, c_tok)

        if run_result.status == RunStatus.COMPLETED:
            record_run_outcome("completed", duration_sec=_run_duration)
            output_text = (
                str(run_result.final_output.get("response", run_result.final_output))
                if isinstance(run_result.final_output, dict)
                else str(run_result.final_output or "")
            )

            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="message.delta",
                payload={"delta": output_text},
            )

            assistant_msg = await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content=output_text,
                run_id=run_id,
                status_="completed",
            )

            if hasattr(plane, "artifact_repository") and plane.artifact_repository is not None:
                try:
                    artifact = WorkspaceArtifact(
                        workspace_id=workspace_id,
                        conversation_id=conversation_id,
                        run_id=run_id,
                        source_message_id=assistant_msg.message_id,
                        artifact_kind="assistant_output",
                        display_name="Agent response",
                        media_type="text/plain",
                        object_ref=f"artifact://run/{run_id}/assistant-output",
                    )
                    await plane.artifact_repository.create(artifact)
                except Exception as e:
                    logger.warning("Failed to persist workspace artifact for run %s: %s", run_id, e)

            if plane.workforce_repository is not None:
                await plane.workforce_repository.enqueue_runtime_signal(
                    workspace_id=workspace_id,
                    source_kind="run",
                    source_id=run_id,
                    sequence=1,
                    state="COMPLETED",
                    observed_at=datetime.now(UTC),
                )

            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.completed",
                payload={"output": output_text, "status": "COMPLETED"},
            )

        elif run_result.status == RunStatus.WAITING_APPROVAL:
            record_run_outcome("waiting_approval", duration_sec=_run_duration)
            wait_desc = (
                run_result.interruptions_waits[0] if run_result.interruptions_waits else None
            )
            appr_id = wait_desc.related_ref if wait_desc else None
            ckpt_ref = wait_desc.checkpoint_ref if wait_desc else None

            if plane.workforce_repository is not None:
                await plane.workforce_repository.enqueue_runtime_signal(
                    workspace_id=workspace_id,
                    source_kind="run",
                    source_id=run_id,
                    sequence=1,
                    state="WAITING_APPROVAL",
                    observed_at=datetime.now(UTC),
                )

            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="approval.required",
                payload={
                    "approval_id": appr_id,
                    "checkpoint_ref": ckpt_ref,
                    "reason": wait_desc.reason if wait_desc else "Approval required",
                },
            )

        else:
            record_run_outcome("failed", duration_sec=_run_duration)
            err_msg = run_result.errors[0] if run_result.errors else "Run failed"
            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content=f"Error: {err_msg}",
                run_id=run_id,
                status_="failed",
            )
            if plane.workforce_repository is not None:
                await plane.workforce_repository.enqueue_runtime_signal(
                    workspace_id=workspace_id,
                    source_kind="run",
                    source_id=run_id,
                    sequence=1,
                    state="FAILED",
                    observed_at=datetime.now(UTC),
                )

            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": err_msg},
            )

    except Exception:
        # Task 6 — exception thô (message, traceback) có thể chứa nội dung
        # nhạy cảm (pinned skill detail, secret trong context, đường dẫn nội
        # bộ...) — TUYỆT ĐỐI không forward nguyên văn cho client qua message
        # hay stream event. Log đầy đủ server-side kèm run_id để debug được,
        # client chỉ nhận thông báo ổn định + mã lỗi chung.
        _run_duration = time.monotonic() - _run_start
        record_run_outcome("failed", duration_sec=_run_duration)
        logger.exception("agent run failed", extra={"run_id": run_id})
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content="Đã xảy ra lỗi không mong muốn khi thực thi run. Vui lòng thử lại hoặc liên hệ hỗ trợ.",
            run_id=run_id,
            status_="failed",
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "internal_error"},
        )


async def execute_resume_task(
    plane: CosaAgentPlane,
    stream_mgr: CosaEventStreamManager,
    payload: dict[str, Any],
) -> None:
    """Resume 1 run đang WAITING_APPROVAL sau khi được approve — trước đây là
    `asyncio.create_task(do_resume())` sống trong HTTP process
    (`apps/cosa/api/routes.py::decide_approval`), giờ chạy trong worker
    process riêng sau khi claim task + acquire lease durable."""
    run_id = payload["run_id"]
    agent_profile = payload.get("agent_profile")

    if agent_profile == "customer_support_autopilot" or payload.get("autopilot") is True:
        with log_context(run_id=run_id, workspace_id=payload.get("workspace_id", "")):
            await resume_customer_support_autopilot(plane, stream_mgr, payload)
            return

    checkpoint_ref = payload["checkpoint_ref"]
    conversation_id = payload.get("conversation_id") or "unknown"
    workspace_id = payload.get("workspace_id")
    bearer_token = payload["delegation_token"]
    stream_repo = plane.stream_event_repository

    resume_updates: dict[str, Any] = {"approved": True}
    if workspace_id:
        try:
            fresh_snapshot = await plane.tenant_policy_client.get_snapshot(
                bearer_token, workspace_id
            )
            resume_updates["policy_snapshot"] = fresh_snapshot.model_dump()
        except CosaTenantPolicyError:
            # Final-review Finding 2 — cùng bug class với branch đã fix trong
            # `_execute_run_task_inner` ở trên: không interpolate exception
            # thô (có thể lộ host/port control-plane) vào payload client-
            # facing. Log đầy đủ server-side kèm run_id, client chỉ nhận mã
            # lỗi ổn định.
            logger.exception("policy snapshot unavailable on resume", extra={"run_id": run_id})
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": "policy_snapshot_unavailable_on_resume"},
            )
            return

    _resume_start = time.monotonic()
    async with trace_span(
        "kernel.resume",
        attributes={
            "run_id": run_id,
            "checkpoint_ref": checkpoint_ref,
            "workspace_id": workspace_id,
        },
    ):
        res = await plane.kernel.resume(
            run_id=run_id,
            checkpoint_ref=checkpoint_ref,
            updates=resume_updates,
        )
    _resume_duration = time.monotonic() - _resume_start

    if getattr(res, "usage", None):
        usage = res.usage
        p_tok = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        c_tok = usage.get("completion_tokens") or usage.get("output_tokens") or 0
        with contextlib.suppress(Exception):
            record_model_tokens("deepseek-chat", p_tok, c_tok)

    if res.status == RunStatus.COMPLETED:
        record_run_outcome("completed", duration_sec=_resume_duration)
        output_text = (
            str(res.final_output.get("response", res.final_output))
            if isinstance(res.final_output, dict)
            else str(res.final_output or "")
        )

        if conversation_id != "unknown":
            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content=output_text,
                run_id=run_id,
                status_="completed",
            )

        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="message.delta",
            payload={"delta": output_text},
        )

        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.completed",
            payload={"output": output_text, "status": "COMPLETED"},
        )


async def execute_scheduled_session_task(
    plane: CosaAgentPlane,
    stream_mgr: CosaEventStreamManager,
    payload: dict[str, Any],
    run_id: str,
) -> None:
    """Xử lý task schedule_execution được dispatch bởi scheduler cron/run_now.

    1. Lấy thông tin schedule execution.
    2. Tạo ConversationRecord mới scoped đúng company_id / workspace_id với created_by_principal='service:scheduler'.
    3. Thực thi run_task với prompt template snapshot và agent profile snapshot.
    4. Cập nhật trạng thái hoàn thành (succeeded/failed) cho schedule execution.
    """
    schedule_exec_id = payload.get("schedule_execution_id")
    workspace_id = payload.get("workspace_id")
    prompt_template = payload.get("prompt_template")
    agent_profile = payload.get("agent_profile") or "operations"

    # If payload didn't carry full execution snapshot, fetch from control plane
    if not (workspace_id and prompt_template) and schedule_exec_id:
        control_plane_url = resolve_platform_control_plane_url()
        token = os.environ.get("COSA_WORKER_SERVICE_TOKEN")
        fetch_headers: dict[str, str] = inject_trace_carrier({})
        if token:
            fetch_headers["Authorization"] = f"Bearer {token}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{control_plane_url}/cosa/schedules/executions/{schedule_exec_id}",
                    headers=fetch_headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    workspace_id = data.get("workspaceId") or data.get("workspace_id")
                    prompt_template = data.get("promptTemplateSnapshot") or data.get(
                        "prompt_template_snapshot"
                    )
                    agent_profile = (
                        data.get("agentProfileSnapshot")
                        or data.get("agent_profile_snapshot")
                        or "operations"
                    )
        except Exception as exc:
            logger.warning("Could not fetch execution snapshot from control plane: %s", exc)

    if not (workspace_id and prompt_template):
        raise ValueError(f"Incomplete schedule execution data for {schedule_exec_id}")

    conversation_id = f"conv_sched_{uuid.uuid4().hex[:8]}"
    conv = ConversationRecord(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        created_by_principal="service:scheduler",
        title=f"Scheduled execution: {prompt_template[:30]}",
    )
    await plane.conversation_repository.create_conversation(conv)

    user_msg = MessageRecord(
        conversation_id=conversation_id,
        role="user",
        content=prompt_template,
    )
    await plane.conversation_repository.add_message(user_msg)

    run_payload = {
        "run_id": run_id,
        "conversation_id": conversation_id,
        "user_prompt": prompt_template,
        "principal": "service:scheduler",
        "workspace_id": workspace_id,
        "agent_name": agent_profile,
        "agent_profile": agent_profile,
        "delegation_token": payload.get("delegation_token") or "scheduled_worker_service_token",
    }

    error_msg = None
    state = "succeeded"
    try:
        await execute_run_task(plane, stream_mgr, run_payload)
    except Exception as exc:
        state = "failed"
        error_msg = str(exc)
        raise
    finally:
        if schedule_exec_id:
            try:
                control_plane_url = resolve_platform_control_plane_url()
                token = os.environ.get("COSA_WORKER_SERVICE_TOKEN")
                headers: dict[str, str] = inject_trace_carrier({})
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        f"{control_plane_url}/cosa/schedules/executions/complete",
                        json={
                            "executionId": schedule_exec_id,
                            "state": state,
                            "conversationId": conversation_id,
                            "runId": run_id,
                            "error": error_msg,
                        },
                        headers=headers,
                    )
            except Exception as e:
                logger.warning(
                    "Failed to report complete schedule execution %s: %s", schedule_exec_id, e
                )
