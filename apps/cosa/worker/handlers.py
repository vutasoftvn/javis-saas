import logging
import os
import uuid
import httpx
from typing import Any

from agent_core.artifacts import WorkspaceArtifact
from agent_core.contracts.run import RunRequest, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.conversations.models import ConversationRecord, MessageRecord
from agent_core.registry.repository import SpecDependencyMissingError
from agent_core.registry.resolver import SpecResolver
from apps.cosa.agents.specs import COSA_FINANCE_AGENT_SPEC, COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.policies.company_policy_client import CosaTenantPolicyError

logger = logging.getLogger(__name__)


__all__ = [
    "execute_run_task",
    "execute_resume_task",
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
    conversation_id = payload["conversation_id"]
    user_prompt = payload["user_prompt"]
    agent_profile = payload.get("agent_profile") or "operations"
    principal = payload["principal"]
    workspace_id = payload["workspace_id"]
    company_id = payload["company_id"]
    bearer_token = payload.get("delegation_token", "scheduled_worker_service_token")
    stream_repo = plane.stream_event_repository


    local_spec = COSA_FINANCE_AGENT_SPEC if "finance" in agent_profile else COSA_OPERATIONS_AGENT_SPEC

    # Resolve PolicySnapshot TRƯỚC khi tạo run — §10.5 freshness invariant:
    # không xác nhận được current gate/tenant policy thật KHÔNG được coi là
    # ALLOW ngầm.
    try:
        snapshot = await plane.tenant_policy_client.get_snapshot(bearer_token, company_id)
    except CosaTenantPolicyError as exc:
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content=f"Unable to verify tenant policy — run rejected: {exc}",
            run_id=run_id,
            status_="failed",
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": f"policy_snapshot_unavailable: {exc}"},
        )
        return

    # Resolve exact spec (đúng version + fingerprint) từ registry TRƯỚC khi
    # tạo Run — không tin tưởng mù quáng object Python đang import (có thể
    # đã drift so với bản đã publish, vd nhiều worker chạy code khác nhau
    # cùng lúc trong lúc rolling deploy). Wave M2b, đúng §15.1 của
    # COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md.
    resolver = SpecResolver(repository=plane.spec_registry)
    try:
        resolution = await resolver.resolve_agent_spec_dependencies(local_spec)
    except SpecDependencyMissingError as exc:
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content=f"Unable to resolve agent spec from registry — run rejected: {exc}",
            run_id=run_id,
            status_="failed",
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": f"spec_resolution_unavailable: {exc}"},
        )
        return

    spec = AgentSpec(**resolution.agent_content)

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

    req = RunRequest(
        run_id=run_id,
        principal=principal,
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": user_prompt},
        workspace_id=workspace_id,
        company_id=company_id,
        conversation_id=conversation_id,
        metadata={"policy_snapshot": snapshot.model_dump()},
    )

    try:
        run_result = await plane.kernel.run(req, spec)

        if run_result.status == RunStatus.COMPLETED:
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
                        company_id=company_id,
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

            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.completed",
                payload={"output": output_text, "status": "COMPLETED"},
            )


        elif run_result.status == RunStatus.WAITING_APPROVAL:
            wait_desc = run_result.interruptions_waits[0] if run_result.interruptions_waits else None
            appr_id = wait_desc.related_ref if wait_desc else None
            ckpt_ref = wait_desc.checkpoint_ref if wait_desc else None

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
            err_msg = run_result.errors[0] if run_result.errors else "Run failed"
            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content=f"Error: {err_msg}",
                run_id=run_id,
                status_="failed",
            )
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": err_msg},
            )

    except Exception as exc:
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content=f"Unexpected error: {str(exc)}",
            run_id=run_id,
            status_="failed",
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": str(exc)},
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
    checkpoint_ref = payload["checkpoint_ref"]
    conversation_id = payload.get("conversation_id") or "unknown"
    company_id = payload.get("company_id")
    bearer_token = payload["delegation_token"]
    stream_repo = plane.stream_event_repository

    resume_updates: dict[str, Any] = {"approved": True}
    if company_id:
        try:
            fresh_snapshot = await plane.tenant_policy_client.get_snapshot(bearer_token, company_id)
            resume_updates["policy_snapshot"] = fresh_snapshot.model_dump()
        except CosaTenantPolicyError as exc:
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": f"policy_snapshot_unavailable_on_resume: {exc}"},
            )
            return

    res = await plane.kernel.resume(
        run_id=run_id,
        checkpoint_ref=checkpoint_ref,
        updates=resume_updates,
    )
    if res.status == RunStatus.COMPLETED:
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
    company_id = payload.get("company_id")
    workspace_id = payload.get("workspace_id")
    prompt_template = payload.get("prompt_template")
    agent_profile = payload.get("agent_profile") or "operations"

    # If payload didn't carry full execution snapshot, fetch from control plane
    if not (company_id and workspace_id and prompt_template) and schedule_exec_id:
        control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
        token = os.environ.get("COSA_WORKER_SERVICE_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{control_plane_url}/cosa/schedules/executions/{schedule_exec_id}",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    company_id = data.get("companyId") or data.get("company_id")
                    workspace_id = data.get("workspaceId") or data.get("workspace_id")
                    prompt_template = data.get("promptTemplateSnapshot") or data.get("prompt_template_snapshot")
                    agent_profile = (
                        data.get("agentProfileSnapshot")
                        or data.get("agent_profile_snapshot")
                        or "operations"
                    )
        except Exception as exc:
            logger.warning("Could not fetch execution snapshot from control plane: %s", exc)

    if not (company_id and workspace_id and prompt_template):
        raise ValueError(f"Incomplete schedule execution data for {schedule_exec_id}")

    conversation_id = f"conv_sched_{uuid.uuid4().hex[:8]}"
    conv = ConversationRecord(
        conversation_id=conversation_id,
        company_id=company_id,
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
        "company_id": company_id,
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
                control_plane_url = os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")
                token = os.environ.get("COSA_WORKER_SERVICE_TOKEN")
                headers = {"Authorization": f"Bearer {token}"} if token else {}
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
                logger.warning("Failed to report complete schedule execution %s: %s", schedule_exec_id, e)

