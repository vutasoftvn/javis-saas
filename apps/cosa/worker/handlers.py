from __future__ import annotations

from typing import Any

from agent_core.contracts.run import RunRequest, RunStatus
from agent_core.conversations.models import MessageRecord
from apps.cosa.agents.specs import COSA_FINANCE_AGENT_SPEC, COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.policies.company_policy_client import CosaTenantPolicyError

__all__ = ["execute_run_task", "execute_resume_task"]


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
    bearer_token = payload["bearer_token"]

    spec = COSA_FINANCE_AGENT_SPEC if "finance" in agent_profile else COSA_OPERATIONS_AGENT_SPEC

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
        stream_mgr.emit(
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": f"policy_snapshot_unavailable: {exc}"},
        )
        return

    stream_mgr.emit(
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="run.started",
        payload={"run_id": run_id, "conversation_id": conversation_id, "goal": user_prompt},
    )
    stream_mgr.emit(
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="reasoning.status",
        payload={"status": "thinking"},
    )
    stream_mgr.emit(
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

            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="message.delta",
                payload={"delta": output_text},
            )

            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content=output_text,
                run_id=run_id,
                status_="completed",
            )

            stream_mgr.emit(
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.completed",
                payload={"output": output_text, "status": "COMPLETED"},
            )

        elif run_result.status == RunStatus.WAITING_APPROVAL:
            wait_desc = run_result.interruptions_waits[0] if run_result.interruptions_waits else None
            appr_id = wait_desc.related_ref if wait_desc else None
            ckpt_ref = wait_desc.checkpoint_ref if wait_desc else None

            stream_mgr.emit(
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
            stream_mgr.emit(
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
        stream_mgr.emit(
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
    bearer_token = payload["bearer_token"]

    resume_updates: dict[str, Any] = {"approved": True}
    if company_id:
        try:
            fresh_snapshot = await plane.tenant_policy_client.get_snapshot(bearer_token, company_id)
            resume_updates["policy_snapshot"] = fresh_snapshot.model_dump()
        except CosaTenantPolicyError as exc:
            stream_mgr.emit(
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

        stream_mgr.emit(
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="message.delta",
            payload={"delta": output_text},
        )

        stream_mgr.emit(
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.completed",
            payload={"output": output_text, "status": "COMPLETED"},
        )
