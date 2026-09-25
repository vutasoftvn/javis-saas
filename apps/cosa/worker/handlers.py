import contextlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from agent.artifacts import WorkspaceArtifact
from agent.contracts.run import RunStatus
from agent.conversations.models import ConversationRecord, MessageRecord

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.goal_intent import (
    GoalIntentSuggestion,
    classify_weekly_goal_llm,
    detect_weekly_goal_suggestion,
    looks_like_weekly_goal,
)
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.config.planes import resolve_platform_control_plane_url
from apps.cosa.observability.logging import log_context
from apps.cosa.observability.metrics import record_model_tokens, record_run_outcome
from apps.cosa.observability.otel import inject_trace_carrier, trace_span
from apps.cosa.policies.company_policy_client import CosaTenantPolicyError
from apps.cosa.policies.snapshot import AgentAuthorizationSnapshot
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
from apps.cosa.worker.wga_run import advance_wga_task_after_resume

logger = logging.getLogger(__name__)

# Ánh xạ agent_profile -> AgentSpec cho nhánh dispatch thường (không bao gồm
# customer_support/customer_support_autopilot — 2 profile đó rẽ nhánh riêng ở
# execute_run_task trước khi tới đây). Bảng THẬT nằm ở
# `apps/cosa/agents/agent_profile_specs.py` (tách riêng để
# `apps/cosa/api/model_policy_routes.py` dùng CHUNG đúng 1 bảng mà không phải
# kéo theo toàn bộ import chain nặng của module này — xem docstring ở đó).
_AGENT_PROFILE_SPECS = AGENT_PROFILE_SPECS

from apps.cosa.agents.startup_team_profiles_generated import STARTUP_TEAM_PROFILE_KEYS
from apps.cosa.company.project_team_client import (
    ProjectTeamAuthorityError,
    ProjectTeamClient,
)

PROJECT_TEAM_OPERATING_PROFILES = set(STARTUP_TEAM_PROFILE_KEYS) - {"founder_assistant"}


from apps.cosa.worker.executive_board_handler import (
    execute_executive_deliberation_framed_task,
)

__all__ = [
    "RunTaskResult",
    "execute_automation_run_task",
    "execute_executive_deliberation_framed_task",
    "execute_resume_task",
    "execute_run_task",
    "execute_scheduled_session_task",
]


@dataclass
class RunTaskResult:
    status: str
    error: str | None = None
    run_id: str | None = None


async def _weekly_goal_suggestion(plane: CosaAgentPlane, user_prompt: str) -> GoalIntentSuggestion:
    """WGA #5 — quyết định có chèn goal_confirm không. Pre-filter rẻ gate việc
    gọi LLM; LLM classify (structured, có ngưỡng confidence) là quyết định
    chính; lỗi/không có model -> heuristic."""
    if not looks_like_weekly_goal(user_prompt):
        return GoalIntentSuggestion(should_suggest=False, normalized_goal="")

    model = getattr(getattr(plane, "kernel", None), "_model", None)
    if model is not None:
        try:
            threshold = float(os.environ.get("WGA_GOAL_INTENT_CONFIDENCE", "0.75"))
            res = await classify_weekly_goal_llm(model, user_prompt)
            if res.is_weekly_goal_statement and res.confidence >= threshold:
                return GoalIntentSuggestion(
                    should_suggest=True, normalized_goal=res.normalized_goal
                )
            return GoalIntentSuggestion(should_suggest=False, normalized_goal="")
        except Exception:
            logger.debug("goal-intent LLM classify failed, falling back to heuristic")

    return detect_weekly_goal_suggestion(user_prompt)


async def _append_message(
    plane: CosaAgentPlane,
    *,
    conversation_id: str,
    role: str,
    content: str,
    run_id: str | None = None,
    status_: str = "completed",
    project_id: str | None = None,
) -> MessageRecord:
    message = MessageRecord(
        conversation_id=conversation_id,
        project_id=project_id,
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
) -> RunTaskResult:
    """Thực thi 1 run mới — trước đây là `asyncio.create_task(_execute_canonical_
    run_task(...))` sống trong HTTP process (`apps/cosa/api/routes.py`), giờ
    chạy trong worker process riêng, dispatch bởi `apps/cosa/worker/main.py`
    sau khi claim task + acquire lease durable — theo
    COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §5/§29.6 Phase 4.
    """
    run_id = payload.get("run_id") or str(uuid.uuid4())
    agent_profile = payload.get("agent_profile") or "operations"
    workspace_id = payload.get("workspace_id")
    # Task 3 (plan 2026-09-11-project-scoped-founder-hub) — mọi stream_mgr.emit()
    # trong module này forward 3 kwarg này để CosaEventStreamManager cũng ghi
    # Project Activity projection (idempotent, TRƯỚC live fanout). project_id
    # có thể None (run legacy/agent_profile khác operations) — emit() tự bỏ
    # qua projection khi đó, không raise.
    project_id = payload.get("project_id")

    if agent_profile == "operations" and not payload.get("project_id"):
        conversation_id = payload.get("conversation_id")
        stream_repo = getattr(plane, "stream_event_repository", None)
        if stream_repo and conversation_id and stream_mgr:
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": "project_context_required"},
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
            )
        return RunTaskResult(status="failed", error="project_context_required", run_id=run_id)

    # Project-scoped Founder Hub — defense-in-depth: dù conversation_routes.py
    # đã verify request project_id == conversation.project_id TRƯỚC khi
    # schedule, worker KHÔNG tin payload đã schedule là nguồn sự thật cuối
    # cùng (payload có thể trôi/stale giữa lúc schedule và lúc dispatch thật
    # — rolling deploy, retry, hoặc caller khác của scheduler ngoài HTTP
    # route). Re-check với ConversationRecord ĐÃ LƯU TRƯỚC khi chạm kernel.
    if agent_profile == "operations":
        conversation_id = payload.get("conversation_id")
        conv_repo = getattr(plane, "conversation_repository", None)
        if conversation_id and conv_repo is not None:
            persisted_conv = await conv_repo.get_conversation(conversation_id)
            if (
                persisted_conv is not None
                and persisted_conv.project_id
                and persisted_conv.project_id != payload.get("project_id")
            ):
                logger.error(
                    "run_id=%s project_id mismatch: payload=%r conversation=%r, failing closed",
                    run_id,
                    payload.get("project_id"),
                    persisted_conv.project_id,
                )
                stream_repo = getattr(plane, "stream_event_repository", None)
                if stream_repo and stream_mgr:
                    await stream_mgr.emit(
                        stream_repo,
                        run_id=run_id,
                        conversation_id=conversation_id,
                        event_type="run.failed",
                        payload={"error": "project_context_mismatch"},
                        activity_service=getattr(plane, "project_activity_service", None),
                        workspace_id=workspace_id,
                        project_id=project_id,
                    )
                return RunTaskResult(
                    status="failed", error="project_context_mismatch", run_id=run_id
                )

    if agent_profile in PROJECT_TEAM_OPERATING_PROFILES:
        if not workspace_id or not project_id:
            conversation_id = payload.get("conversation_id")
            stream_repo = getattr(plane, "stream_event_repository", None)
            if stream_repo and conversation_id and stream_mgr:
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id=conversation_id,
                    event_type="run.failed",
                    payload={"error": "project_context_required"},
                    activity_service=getattr(plane, "project_activity_service", None),
                    workspace_id=workspace_id,
                    project_id=project_id,
                )
            return RunTaskResult(status="failed", error="project_context_required", run_id=run_id)

        team_client = getattr(plane, "project_team_client", None) or ProjectTeamClient()
        try:
            authority = await team_client.get_run_authority(
                workspace_id=str(workspace_id),
                project_id=str(project_id),
                profile_key=agent_profile,
            )
        except ProjectTeamAuthorityError as exc:
            logger.warning(
                "run_id=%s authority denied for %s in project=%s: %s",
                run_id,
                agent_profile,
                project_id,
                exc,
            )
            conversation_id = payload.get("conversation_id")
            stream_repo = getattr(plane, "stream_event_repository", None)
            if stream_repo and conversation_id and stream_mgr:
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id=conversation_id,
                    event_type="run.failed",
                    payload={"error": "project_team_authority_denied", "details": str(exc)},
                    activity_service=getattr(plane, "project_activity_service", None),
                    workspace_id=workspace_id,
                    project_id=project_id,
                )
            return RunTaskResult(
                status="failed", error="project_team_authority_denied", run_id=run_id
            )

        if (
            str(authority.workspace_id) != str(workspace_id)
            or str(authority.project_id) != str(project_id)
            or authority.profile_key != agent_profile
        ):
            conversation_id = payload.get("conversation_id")
            stream_repo = getattr(plane, "stream_event_repository", None)
            if stream_repo and conversation_id and stream_mgr:
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id=conversation_id,
                    event_type="run.failed",
                    payload={"error": "project_context_mismatch"},
                    activity_service=getattr(plane, "project_activity_service", None),
                    workspace_id=workspace_id,
                    project_id=project_id,
                )
            return RunTaskResult(status="failed", error="project_context_mismatch", run_id=run_id)

        local_spec = _AGENT_PROFILE_SPECS.get(agent_profile)
        if not local_spec:
            return RunTaskResult(status="failed", error="unknown_agent_profile", run_id=run_id)

        if (
            local_spec.id != authority.spec.id
            or local_spec.version != authority.spec.version
            or local_spec.compute_hash() != authority.spec.hash
        ):
            logger.error(
                "run_id=%s spec mismatch for %s: local=(%s, %s, %s) authority=(%s, %s, %s)",
                run_id,
                agent_profile,
                local_spec.id,
                local_spec.version,
                local_spec.compute_hash(),
                authority.spec.id,
                authority.spec.version,
                authority.spec.hash,
            )
            conversation_id = payload.get("conversation_id")
            stream_repo = getattr(plane, "stream_event_repository", None)
            if stream_repo and conversation_id and stream_mgr:
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id=conversation_id,
                    event_type="run.failed",
                    payload={"error": "spec_hash_mismatch"},
                    activity_service=getattr(plane, "project_activity_service", None),
                    workspace_id=workspace_id,
                    project_id=project_id,
                )
            return RunTaskResult(status="failed", error="spec_hash_mismatch", run_id=run_id)

        if agent_profile == "customer_support" and not authority.policy_snapshot.get(
            "knowledge_gate_passed", False
        ):
            conversation_id = payload.get("conversation_id")
            stream_repo = getattr(plane, "stream_event_repository", None)
            if stream_repo and conversation_id and stream_mgr:
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id=conversation_id,
                    event_type="run.failed",
                    payload={"error": "support_knowledge_gate_required"},
                    activity_service=getattr(plane, "project_activity_service", None),
                    workspace_id=workspace_id,
                    project_id=project_id,
                )
            return RunTaskResult(
                status="failed",
                error="support_knowledge_gate_required",
                run_id=run_id,
            )

        payload["assignment_version"] = authority.assignment_version
        payload["spec_hash"] = authority.spec.hash

    if agent_profile == "customer_support" or payload.get("copilot") is True:
        with log_context(run_id=run_id, workspace_id=workspace_id):
            await run_customer_support_copilot(plane, stream_mgr, payload)
            return RunTaskResult(status="completed", run_id=run_id)

    if agent_profile == "customer_support_autopilot":
        with log_context(run_id=run_id, workspace_id=workspace_id):
            await run_customer_support_autopilot(plane, stream_mgr, payload)
            return RunTaskResult(status="completed", run_id=run_id)

    # Ensure correlation context is active for all log lines emitted within this handler.
    # worker/main.py already sets log_context for dispatch_one_task, but
    # execute_run_task can also be called directly from execute_scheduled_session_task.
    with log_context(run_id=run_id, workspace_id=workspace_id):
        await _execute_run_task_inner(plane, stream_mgr, payload)
        return RunTaskResult(status="completed", run_id=run_id)


async def _execute_run_task_inner(
    plane: CosaAgentPlane,
    stream_mgr: CosaEventStreamManager,
    payload: dict[str, Any],
) -> None:
    run_id = payload["run_id"]
    conversation_id = payload["conversation_id"]
    agent_profile = payload.get("agent_profile") or "operations"
    principal = payload["principal"]
    workspace_id = payload["workspace_id"]
    # Task 3 — xem comment ở execute_run_task() phía trên cùng lý do.
    project_id = payload.get("project_id")
    stream_repo = plane.stream_event_repository

    # IA24: trước đây payload["user_prompt"] truy cập trực tiếp — một payload
    # event-driven thiếu field này (vd producer/adapter cũ, hoặc lỗi upstream)
    # sẽ raise KeyError chưa được bắt, làm hỏng cả task thay vì fail-closed có
    # kiểm soát như đường thiếu delegation_token ngay bên dưới.
    user_prompt = payload.get("user_prompt")
    if not user_prompt:
        logger.error("run_id=%s missing user_prompt in payload, failing closed", run_id)
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content="Missing user_prompt — run rejected",
            run_id=run_id,
            status_="failed",
            project_id=project_id,
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "missing_user_prompt"},
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
        )
        return

    bearer_token = payload.get("delegation_token")
    if not bearer_token:
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content="Missing delegation token — run rejected",
            run_id=run_id,
            status_="failed",
            project_id=project_id,
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "missing_delegation_token"},
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
        )
        return

    local_spec = _AGENT_PROFILE_SPECS.get(agent_profile)
    if local_spec is None:
        logger.error(
            "unsupported agent_profile %r for run_id=%s, failing closed",
            agent_profile,
            run_id,
        )
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content=f"Unsupported agent profile '{agent_profile}' — run rejected",
            run_id=run_id,
            status_="failed",
            project_id=project_id,
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": f"unsupported_agent_profile_{agent_profile}"},
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
        )
        return

    assignment_id = payload.get("assignment_id")
    company_workforce_member_id = payload.get("company_workforce_member_id")

    if assignment_id and plane.workforce_repository is not None:
        assignment = await plane.workforce_repository.get_assignment(workspace_id, assignment_id)
        if assignment is None or assignment.status != "ACTIVE":
            logger.error("assignment %r not found or retired for run_id=%s", assignment_id, run_id)
            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content="Workforce assignment retired or not found — run rejected",
                run_id=run_id,
                status_="failed",
                project_id=project_id,
            )
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": "workforce_assignment_retired"},
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
            )
            return
        if not company_workforce_member_id and assignment.company_workforce_member_id:
            company_workforce_member_id = assignment.company_workforce_member_id

    # Resolve PolicySnapshot TRƯỚC khi tạo run — §10.5 freshness invariant:
    # không xác nhận được current gate/tenant policy thật KHÔNG được coi là
    # ALLOW ngầm.
    try:
        snapshot = await plane.tenant_policy_client.get_snapshot(bearer_token, workspace_id)
        if company_workforce_member_id:
            delegation_token = payload.get("company_delegation_token") or bearer_token
            business_rules = await plane.tenant_policy_client.get_business_policy_rules(
                delegation_token=delegation_token,
                workspace_id=workspace_id,
                workforce_member_id=str(company_workforce_member_id),
            )
            snapshot.business_policy_rules = business_rules
            snapshot.agent_authority = AgentAuthorizationSnapshot(
                authorization_epoch=business_rules.authorization_epoch,
                grants=business_rules.agent_capabilities,
            )
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
            project_id=project_id,
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "policy_snapshot_unavailable"},
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
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
            project_id=project_id,
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "spec_resolution_unavailable"},
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
        )
        return

    await stream_mgr.emit(
        stream_repo,
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="run.started",
        payload={"run_id": run_id, "conversation_id": conversation_id, "goal": user_prompt},
        activity_service=getattr(plane, "project_activity_service", None),
        workspace_id=workspace_id,
        project_id=project_id,
    )
    await stream_mgr.emit(
        stream_repo,
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="reasoning.status",
        payload={"status": "thinking"},
        activity_service=getattr(plane, "project_activity_service", None),
        workspace_id=workspace_id,
        project_id=project_id,
    )
    await stream_mgr.emit(
        stream_repo,
        run_id=run_id,
        conversation_id=conversation_id,
        event_type="message.started",
        payload={"role": "assistant"},
        activity_service=getattr(plane, "project_activity_service", None),
        workspace_id=workspace_id,
        project_id=project_id,
    )

    # Task 5 — forward context egress đã hash vào metadata để
    # ComplianceResolver.resolve_for_run dựng DataAccessClaim thật. Chỉ chứa
    # context đã hash, không có nội dung message thô.
    extra_md: dict[str, Any] = {}
    if company_workforce_member_id:
        extra_md["agent_workforce_member_id"] = str(company_workforce_member_id)
        extra_md["company_workforce_member_id"] = str(company_workforce_member_id)
    if assignment_id:
        extra_md["assignment_id"] = str(assignment_id)
    direct_message_data_access = payload.get("direct_message_data_access")
    if direct_message_data_access is not None:
        extra_md["direct_message_data_access"] = direct_message_data_access

    # Task 10 (plan local-first-enterprise-knowledge) — role_id (nếu caller
    # đã forward, xem apps.cosa.api.conversation_routes) đi vào
    # request.metadata -> context["role_id"] -> InvocationContext.metadata,
    # để capability workspace.context.read resolve đúng role_ids cho
    # retrieve_authorized_citations(). Thiếu -> role_id vắng trong ctx,
    # capability fail-closed về role rỗng (không suy diễn operator).
    role_id = payload.get("role_id")
    if role_id:
        extra_md["role_id"] = role_id

    locale = payload.get("locale") or "vi-VN"
    locale_source = payload.get("locale_source")
    if locale_source:
        extra_md["locale_source"] = locale_source

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
            locale=locale,
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
                project_id=project_id,
            )
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": "compliance_resolver_unavailable"},
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
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
                project_id=project_id,
            )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "compliance_denied", "reason_code": code},
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
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
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
            )

            assistant_msg = await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content=output_text,
                run_id=run_id,
                status_="completed",
                project_id=project_id,
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
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
            )

            # WGA — nếu tin nhắn founder trông như phát biểu mục tiêu tuần,
            # chèn 1 structured `goal_confirm` message (content = JSON object,
            # FE nhận diện qua field `kind`). Founder bấm nút mới ghi goal +
            # chạy phân rã (không tự động, chống nhận nhầm).
            if agent_profile in ("operations", "founder_assistant"):
                with contextlib.suppress(Exception):
                    suggestion = await _weekly_goal_suggestion(plane, user_prompt)
                    if suggestion.should_suggest:
                        await _append_message(
                            plane,
                            conversation_id=conversation_id,
                            role="assistant",
                            content=json.dumps(
                                {
                                    "kind": "goal_confirm",
                                    "normalized_goal": suggestion.normalized_goal,
                                },
                                ensure_ascii=False,
                            ),
                            run_id=run_id,
                            status_="completed",
                            project_id=project_id,
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
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
            )
            # Task 3 — "run.waiting_approval" là 1 fact riêng về Run (Run
            # chuyển sang trạng thái WAITING_APPROVAL), khác "approval.requested"
            # ở trên (fact về chính cái Approval vừa được tạo). Không có
            # event_type SSE tương ứng trong UX_EVENT_TYPES cho fact này (client
            # chỉ cần biết qua approval.required) nên ghi trực tiếp qua
            # ProjectActivityService, cùng pattern với chat.accepted/run.queued
            # ở conversation_routes.py — record SAU KHI canonical fact (run
            # status đã WAITING_APPROVAL, kernel.run() đã return) xác nhận.
            waiting_approval_activity_service = getattr(plane, "project_activity_service", None)
            if waiting_approval_activity_service is not None and project_id:
                await waiting_approval_activity_service.record_runtime_event(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    kind="run.waiting_approval",
                    source_type="run",
                    source_id=run_id,
                    source_version=str(ckpt_ref or appr_id or "1"),
                    correlation_id=run_id,
                    raw_context={
                        "approval_id": appr_id,
                        "checkpoint_ref": ckpt_ref,
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
                project_id=project_id,
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
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
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
            project_id=project_id,
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "internal_error"},
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
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
    # Task 3 — xem comment ở execute_run_task() phía trên cùng lý do.
    project_id = payload.get("project_id")
    bearer_token = payload["delegation_token"]
    stream_repo = plane.stream_event_repository

    # Bug 1.2 fix — KHÔNG dùng blanket "approved": True (approve nhầm mọi tool
    # call khác đang pending trong cùng checkpoint, vi phạm CLAUDE.md rule 5:
    # approval phải bind đúng run_id + tool_call_id + checkpoint_ref). Payload
    # phải mang đúng tool_call_id của approval vừa quyết định
    # (decide_approval::apps/cosa/api/workforce_routes.py).
    tool_call_id = payload.get("tool_call_id")
    if not tool_call_id:
        logger.error("resume task missing tool_call_id for run_id=%s, failing closed", run_id)
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={"error": "missing_tool_call_id_on_resume"},
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
        )
        return
    resume_updates: dict[str, Any] = {"approved_tool_calls": {tool_call_id: True}}
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
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
            )
            return

        # Bug 1.3 fix — verify_and_prepare_resume() (Master Guide §18: re-check
        # tenant/principal ambient governance + target drift TRƯỚC khi cho
        # resume một approval cũ) trước đây tồn tại nhưng không có call site
        # production nào gọi. "APPROVED" không phải bypass token vĩnh viễn —
        # workspace có thể đã bị suspend/principal bị revoke GIỮA lúc approve
        # và lúc resume thật sự chạy.
        verify_result = await plane.approval_service.verify_and_prepare_resume(
            run_id=run_id,
            tool_call_id=tool_call_id,
            checkpoint_ref=checkpoint_ref,
            ambient_context={
                "tenant_status": fresh_snapshot.workspace_status,
                "principal_status": fresh_snapshot.principal_status,
                # emergency_lock: không có ambient signal wired production nào
                # khác cho field này hiện nay — gap đã biết, không phải
                # regression từ fix này.
                "emergency_lock": False,
            },
        )
        if not verify_result.can_resume:
            logger.warning(
                "resume blocked by verify_and_prepare_resume run_id=%s tool_call_id=%s reason=%s",
                run_id,
                tool_call_id,
                verify_result.reason,
            )
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": "resume_verification_failed", "reason": verify_result.reason},
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
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
                project_id=project_id,
            )

        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="message.delta",
            payload={"delta": output_text},
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
        )

        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.completed",
            payload={"output": output_text, "status": "COMPLETED"},
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
        )

        # WGA #1 — nếu đây là resume của 1 task-execution run trong sweep,
        # đóng task tương ứng (advance done). No-op cho resume thường.
        with contextlib.suppress(Exception):
            _sub = str(payload.get("principal") or "0").split(":")[-1]
            await advance_wga_task_after_resume(
                plane, run_id=run_id, workspace_id=workspace_id, sub=_sub
            )


async def _report_schedule_execution_complete(
    schedule_exec_id: str | None,
    *,
    state: str,
    error: str | None,
    conversation_id: str | None,
    run_id: str,
) -> None:
    """Báo hoàn thành (succeeded/failed) 1 schedule execution về control plane.

    Dùng chung cho cả đường thành công/thất bại bình thường (finally block)
    lẫn đường fail-closed sớm khi thiếu project_id snapshot (Finding 1,
    2026-09-14 whole-branch review) — tránh execution kẹt state='queued'
    vĩnh viễn vì không ai báo control plane biết worker đã bỏ chạy.
    """
    if not schedule_exec_id:
        return
    try:
        control_plane_url = resolve_platform_control_plane_url()
        token = os.environ.get("COSA_WORKER_SERVICE_TOKEN")
        headers: dict[str, str] = inject_trace_carrier({})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        complete_payload: dict[str, Any] = {
            "executionId": schedule_exec_id,
            "state": state,
            "runId": run_id,
        }
        if conversation_id is not None:
            complete_payload["conversationId"] = conversation_id
        if error is not None:
            complete_payload["error"] = error
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{control_plane_url}/cosa/schedules/executions/complete",
                json=complete_payload,
                headers=headers,
            )
    except Exception as e:
        logger.warning("Failed to report complete schedule execution %s: %s", schedule_exec_id, e)


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
    # Task 5 (spec #1 schedule-project-scope): project_id giờ luôn đọc từ
    # payload/snapshot thật (được services/cosa gán từ `project_id` bắt buộc
    # lúc tạo schedule — Task 1-4), KHÔNG còn tự "đoán" project đầu tiên của
    # workspace qua Company nữa (đã xoá `_resolve_workspace_project_id` —
    # đó chính là bug: rủi ro chạy nhầm project).
    project_id = payload.get("project_id")

    # If schedule_exec_id is provided, check or fetch execution snapshot from control plane
    if schedule_exec_id:
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
                    workspace_id = (
                        workspace_id
                        or data.get("organizationId")
                        or data.get("workspaceId")
                        or data.get("workspace_id")
                    )
                    prompt_template = (
                        prompt_template
                        or data.get("promptTemplateSnapshot")
                        or data.get("prompt_template_snapshot")
                    )
                    agent_profile = (
                        agent_profile
                        or data.get("agentProfileSnapshot")
                        or data.get("agent_profile_snapshot")
                        or "operations"
                    )
                    snapshot_project_id = data.get("projectIdSnapshot") or data.get(
                        "project_id_snapshot"
                    )
                    if project_id and snapshot_project_id and project_id != snapshot_project_id:
                        error_mismatch = "PROJECT_CONTEXT_MISMATCH"
                        logger.error(
                            "schedule_execution_id=%s project mismatch: payload=%s snapshot=%s",
                            schedule_exec_id,
                            project_id,
                            snapshot_project_id,
                        )
                        await _report_schedule_execution_complete(
                            schedule_exec_id,
                            state="failed",
                            error=error_mismatch,
                            conversation_id=None,
                            run_id=run_id,
                        )
                        raise ValueError(error_mismatch)
                    project_id = snapshot_project_id or project_id
        except ValueError:
            raise
        except Exception as exc:
            logger.warning("Could not fetch execution snapshot from control plane: %s", exc)

    if not (workspace_id and prompt_template):
        raise ValueError(f"Incomplete schedule execution data for {schedule_exec_id}")

    if not project_id:
        # Fail closed: KHÔNG tự chọn project đầu tiên của workspace nữa.
        # Thiếu project_id snapshot nghĩa là schedule execution này đã được
        # tạo/lưu sai (Task 1-4 đã bắt buộc projectId lúc tạo schedule) —
        # từ chối chạy thay vì đoán, tránh chạy nhầm project.
        logger.error(
            "schedule_execution_id=%s missing project_id snapshot — refusing to guess a project",
            schedule_exec_id,
        )
        missing_project_error = (
            f"PROJECT_CONTEXT_REQUIRED: schedule_project_context_missing: {schedule_exec_id}"
        )
        await _report_schedule_execution_complete(
            schedule_exec_id,
            state="failed",
            error=missing_project_error,
            conversation_id=None,
            run_id=run_id,
        )
        raise ValueError(missing_project_error)

    conversation_id = f"conv_sched_{uuid.uuid4().hex[:8]}"
    conv = ConversationRecord(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        project_id=project_id,
        scope_state="PROJECT_SCOPED",
        created_by_principal="service:scheduler",
        active_agent_profile=agent_profile,
        title=f"Scheduled execution: {prompt_template[:30]}",
    )
    await plane.conversation_repository.create_conversation(conv)

    user_msg = MessageRecord(
        conversation_id=conversation_id,
        project_id=project_id,
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
        "project_id": project_id,
        "delegation_token": payload.get("delegation_token") or "scheduled_worker_service_token",
    }

    error_msg = None
    state = "succeeded"
    try:
        run_res = await execute_run_task(plane, stream_mgr, run_payload)
        if run_res and run_res.status == "failed":
            state = "failed"
            error_msg = run_res.error
    except Exception as exc:
        state = "failed"
        error_msg = str(exc)
        raise
    finally:
        await _report_schedule_execution_complete(
            schedule_exec_id,
            state=state,
            error=error_msg,
            conversation_id=conversation_id,
            run_id=run_id,
        )


# ---------------------------------------------------------------------------
# COSA Automation MVP (Task 5) — curated automation run
# ---------------------------------------------------------------------------


async def execute_automation_run_task(
    plane: CosaAgentPlane,
    stream_mgr: CosaEventStreamManager,
    payload: dict[str, Any],
) -> None:
    """Run one curated automation blueprint.

    The manifest is resolved once, hash-verified and persisted insert-once; a
    worker restart reloads it by run_id rather than re-reading a mutable
    definition. Effects go only through the Capability Gateway and only for the
    manifest's declared read/draft/evidence capabilities. A local-only blueprint
    with no eligible local node BLOCKS with LOCAL_RUNTIME_UNAVAILABLE and never
    falls back to cloud.
    """
    from agent.runs.models import RunCheckpointRecord, RunEventRecord, RunRecord
    from agent.workflows.automation_blueprints import (
        BlueprintContext,
        get_blueprint_metadata,
        get_blueprint_spec,
        get_blueprint_step_fn,
    )
    from agent.workflows.automation_manifest import (
        AutomationManifestError,
        resolve_automation_manifest,
    )
    from agent.workflows.models import WorkflowStatus
    from agent.workflows.steps import DeterministicStep

    run_id = str(payload["run_id"])
    workspace_id = str(payload.get("workspace_id", ""))
    # Task 3 — curated automation runs don't currently carry a Project
    # (payload has no "project_id" key yet); kept for forward-compat and
    # consistency with every other stream_mgr.emit() call site in this
    # module — emit() itself no-ops the projection when falsy.
    project_id = payload.get("project_id")
    invocation_id = str(payload.get("invocation_id", ""))
    automation_key = str(payload.get("automation_key", ""))
    correlation_id = str(payload.get("correlation_id", "")) or None
    conversation_id = f"auto:{invocation_id}"

    outcome_client = getattr(plane, "automation_outcome_client", None)
    _seq = {"n": 0}

    async def _emit(event_type: str, body: dict[str, Any]) -> None:
        await plane.run_repository.append_event(
            RunEventRecord(
                run_id=run_id, event_type=event_type, payload=body, correlation_id=correlation_id
            )
        )
        repo = getattr(plane, "stream_event_repository", None)
        if repo is not None:
            with contextlib.suppress(Exception):
                await stream_mgr.emit(
                    repo,
                    run_id=run_id,
                    conversation_id=conversation_id,
                    event_type=event_type,
                    payload=body,
                    correlation_id=correlation_id,
                    activity_service=getattr(plane, "project_activity_service", None),
                    workspace_id=workspace_id,
                    project_id=project_id,
                )

    _mh = {"v": ""}  # manifest hash, set once resolved

    async def _report_state(state: str) -> None:
        if outcome_client is None:
            return
        _seq["n"] += 1
        with contextlib.suppress(Exception):
            await outcome_client.report_state_changed(
                invocation_id=invocation_id,
                run_id=run_id,
                workspace_id=workspace_id,
                state=state,
                sequence=_seq["n"],
                manifest_hash=_mh["v"],
                correlation_id=correlation_id or "",
                observed_at=datetime.now(UTC).isoformat(),
            )

    async def _report_outcome(outcome: str, **kw: Any) -> None:
        if outcome_client is None:
            return
        _seq["n"] += 1
        with contextlib.suppress(Exception):
            await outcome_client.report_outcome(
                invocation_id=invocation_id,
                run_id=run_id,
                workspace_id=workspace_id,
                outcome=outcome,
                sequence=_seq["n"],
                manifest_hash=_mh["v"],
                correlation_id=correlation_id or "",
                observed_at=datetime.now(UTC).isoformat(),
                **kw,
            )

    # 1. Resolve the manifest (no persist yet — its table FKs to agent.runs).
    try:
        spec = get_blueprint_spec(automation_key)
        metadata = get_blueprint_metadata(automation_key)
        manifest = resolve_automation_manifest(
            dispatch_payload=payload, blueprint_spec=spec, blueprint_metadata=metadata
        )
    except (KeyError, AutomationManifestError) as exc:
        await _emit("run.failed", {"error": "automation_manifest_unresolved", "detail": str(exc)})
        raise

    manifest_hash = manifest.compute_hash()
    _mh["v"] = manifest_hash

    def _new_run(status: RunStatus) -> RunRecord:
        return RunRecord(
            run_id=run_id,
            workspace_id=workspace_id,
            principal=f"system:automation:{workspace_id}",
            root_executable_id=automation_key,
            root_executable_kind="workflow",
            root_executable_version=manifest.blueprint_version,
            root_definition_hash=manifest.blueprint_hash,
            correlation_id=correlation_id,
            status=status,
        )

    # 2. Runtime gate — local-only blueprint with no local node BLOCKS.
    if manifest.runtime_requirement == "local_only" and not payload.get(
        "local_runtime_available", False
    ):
        if await plane.run_repository.get_run(run_id) is None:
            await plane.run_repository.create_run(_new_run(RunStatus.FAILED))
        await _emit("run.blocked", {"cause": "LOCAL_RUNTIME_UNAVAILABLE"})
        await _report_outcome("BLOCKED", blocked_cause="LOCAL_RUNTIME_UNAVAILABLE")
        await plane.run_repository.update_run_status(
            run_id, RunStatus.FAILED, error_details={"cause": "LOCAL_RUNTIME_UNAVAILABLE"}
        )
        return

    # 3. Create / load the run FIRST (the manifest table references agent.runs).
    run = await plane.run_repository.get_run(run_id)
    if run is None:
        run = await plane.run_repository.create_run(_new_run(RunStatus.RUNNING))
        await _emit("run.started", {"run_id": run_id, "automation_key": automation_key})
        await _report_state("RUNNING")
    else:
        await plane.run_repository.update_run_status(run_id, RunStatus.RUNNING)

    # 3b. Persist the manifest insert-once (the run row now exists for the FK).
    #     A restart / reclaim runs the persisted manifest, not the current spec.
    persisted = await plane.run_repository.save_automation_manifest(
        run_id, manifest_hash, manifest.model_dump(mode="json")
    )
    if persisted["manifest_hash"] != manifest_hash:
        await _emit(
            "run.failed",
            {
                "error": "automation_manifest_drift",
                "persisted": persisted["manifest_hash"],
                "resolved": manifest_hash,
            },
        )
        await _report_outcome("FAILED", failure_reason="automation_manifest_drift")
        await plane.run_repository.update_run_status(
            run_id, RunStatus.FAILED, error_details={"cause": "manifest_drift"}
        )
        return

    # 4. Execute the pinned blueprint through the WorkflowEngine.
    ctx = BlueprintContext(
        manifest=manifest,
        gateway=plane.gateway,
        run_id=run_id,
        config=dict(payload.get("configuration", {})),
    )

    def _builder(step_spec):
        fn = get_blueprint_step_fn(automation_key, step_spec.id)

        async def _run(state: dict[str, Any]) -> dict[str, Any]:
            return await fn(ctx, state)

        return DeterministicStep(name=step_spec.id, fn=_run)

    custom_builders = {s.id: _builder for s in spec.steps}
    try:
        workflow = await plane.workflow_orchestration.execute_spec(
            spec, initial_state={"config": ctx.config}, custom_step_builders=custom_builders
        )
    except Exception as exc:
        await _emit("run.failed", {"error": "automation_blueprint_error", "detail": str(exc)})
        await plane.run_repository.update_run_status(
            run_id, RunStatus.FAILED, error_details={"detail": str(exc)}
        )
        await _report_outcome("FAILED", failure_reason="automation_blueprint_error")
        raise

    if workflow.status != WorkflowStatus.COMPLETED:
        await _emit(
            "run.failed",
            {"error": "automation_blueprint_not_completed", "status": str(workflow.status)},
        )
        await plane.run_repository.update_run_status(
            run_id, RunStatus.FAILED, error_details={"status": str(workflow.status)}
        )
        await _report_outcome("FAILED", failure_reason="automation_blueprint_not_completed")
        return

    evidence = workflow.state.get("evidence", {})
    # 5. Persist the evidence + manifest snapshot as a checkpoint, then complete.
    await plane.run_repository.save_checkpoint(
        RunCheckpointRecord(
            run_id=run_id,
            sequence_no=1,
            step_name="automation.evidence",
            state_kind="automation",
            serialized_state={"evidence": evidence},
            manifest_snapshot=manifest.model_dump(mode="json"),
        )
    )
    await plane.run_repository.update_run_status(
        run_id, RunStatus.COMPLETED, final_output={"evidence": evidence}
    )
    await _emit("run.completed", {"run_id": run_id, "evidence_keys": sorted(evidence.keys())})
    await _report_outcome("COMPLETED", evidence_refs=sorted(evidence.keys()))
