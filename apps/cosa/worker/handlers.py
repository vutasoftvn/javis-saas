import contextlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from agent.artifacts import WorkspaceArtifact
from agent.contracts.run import RunStatus
from agent.contracts.spec import AgentSpec
from agent.conversations.models import MessageRecord

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.goal_intent import (
    GoalIntentSuggestion,
    classify_weekly_goal_llm,
    detect_weekly_goal_suggestion,
    looks_like_weekly_goal,
)
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.approvals.summary import capability_id_for_tool, summarize_action
from apps.cosa.assets.workspace_agent import (
    ResolvedWorkspaceAgent,
    WorkspaceAgentError,
    profile_for_spec_id,
    resolve_workspace_agent_spec,
)
from apps.cosa.capabilities.access_matrix import CHAT_T2_CAPABILITIES, MATRIX
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.conversations.history import build_history, history_limits
from apps.cosa.memory.project_facts import list_project_facts
from apps.cosa.observability.logging import log_context
from apps.cosa.observability.metrics import record_model_tokens, record_run_outcome
from apps.cosa.observability.otel import trace_span
from apps.cosa.policies.company_policy_client import CosaTenantPolicyError
from apps.cosa.policies.evaluator import REQUIRE_APPROVAL_CAPABILITIES_KEY
from apps.cosa.policies.snapshot import AgentAuthorizationSnapshot
from apps.cosa.worker.autopilot_run import (
    resume_customer_support_autopilot,
    run_customer_support_autopilot,
)
from apps.cosa.worker.copilot_run import run_customer_support_copilot
from apps.cosa.worker.provider_errors import classify_run_error, user_message_for_code
from apps.cosa.worker.run_core import (
    RunCoreError,
    kernel_for_resume,
    prepare_request,
    record_route_usage,
    resolve_spec,
    run_kernel,
)
from apps.cosa.worker.wga_run import (
    advance_wga_task_after_resume,
    record_agent_chat_message_activity,
)

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
# Profile business chạy trong Project (chat, schedule, event): bắt buộc
# workspace_id + project_id và khớp conversation đã lưu.
PROJECT_SCOPED_RUN_PROFILES = frozenset(STARTUP_TEAM_PROFILE_KEYS)
# Profile được phép vào execute_run_task. customer_support_autopilot là system
# profile do event router dispatch (authority qua trigger rule + gateway).
RUN_ELIGIBLE_PROFILES = PROJECT_SCOPED_RUN_PROFILES | {"customer_support_autopilot"}


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


async def _spec_for_authority(plane: Any, local_spec: Any, pin: Any, *, run_id: str) -> Any | None:
    """Spec đúng như authority của Project pin (id + version + hash).

    Khớp spec đang import -> dùng luôn. Lệch (built-in đã nâng version sau khi
    workspace kích hoạt) -> chạy ĐÚNG version đã pin lấy từ registry bất biến,
    không tự nâng quyền lên version mới (quy tắc 13: không floating latest,
    không tự tăng authority). Không tìm thấy bản pin -> None (fail closed)."""
    if (
        local_spec.id == pin.id
        and local_spec.version == pin.version
        and local_spec.compute_hash() == pin.hash
    ):
        return local_spec
    registry = getattr(plane, "spec_registry", None)
    record = None
    if registry is not None:
        with contextlib.suppress(Exception):
            record = await registry.get(spec_kind="agent", spec_id=pin.id, version=pin.version)
    if record is not None and getattr(record, "definition_hash", None) == pin.hash:
        logger.info(
            "run_id=%s running pinned %s@%s (current built-in is %s)",
            run_id,
            pin.id,
            pin.version,
            local_spec.version,
        )
        return AgentSpec(**record.content)
    logger.error(
        "run_id=%s spec mismatch: local=(%s, %s, %s) authority=(%s, %s, %s), pinned version "
        "not in registry",
        run_id,
        local_spec.id,
        local_spec.version,
        local_spec.compute_hash(),
        pin.id,
        pin.version,
        pin.hash,
    )
    return None


async def _resolve_workspace_agent_run(
    plane: Any,
    *,
    workspace_id: str,
    project_id: str,
    deployment_id: str,
) -> tuple[ResolvedWorkspaceAgent, dict[str, Any]]:
    """Agent workspace (clone của built-in) chạy qua ProjectAgentDeployment của company.

    Tham chiếu deployment đến từ client nên KHÔNG được tin: authority (state, scope, pin spec,
    AI member) luôn lấy lại từ company; asset phải PUBLISHED đúng version + hash đã pin
    (spec 2026-09-27-agent-clone-executor-design §6). Lỗi -> WorkspaceAgentError có mã ổn định.
    """
    client = getattr(plane, "company_client", None)
    if client is None:
        raise WorkspaceAgentError("deployment_authority_unavailable")
    try:
        authority = await client.get_project_agent_deployment_authority(
            str(workspace_id), str(project_id), str(deployment_id)
        )
    except Exception as exc:
        logger.warning("deployment authority unavailable for %s: %s", deployment_id, exc)
        raise WorkspaceAgentError("deployment_authority_unavailable") from exc
    if not isinstance(authority, dict) or authority.get("state") != "ACTIVE":
        raise WorkspaceAgentError("deployment_not_active")
    if (
        str(authority.get("workspaceId")) != str(workspace_id)
        or str(authority.get("projectId")) != str(project_id)
        or str(authority.get("projectAgentDeploymentId")) != str(deployment_id)
    ):
        raise WorkspaceAgentError("deployment_scope_mismatch")
    pin = authority.get("agentSpec") or {}
    spec_id, version, definition_hash = (
        pin.get("id"),
        pin.get("version"),
        pin.get("definitionHash"),
    )
    if not (spec_id and version and definition_hash):
        raise WorkspaceAgentError("deployment_spec_pin_missing")
    if profile_for_spec_id(spec_id) is not None or any(
        spec.id == spec_id for spec in _AGENT_PROFILE_SPECS.values()
    ):
        # Built-in đi đường agent_profile + run-authority của startup team.
        raise WorkspaceAgentError("deployment_not_workspace_agent")
    if not authority.get("workforceMemberId"):
        raise WorkspaceAgentError("deployment_member_missing")
    resolved = await resolve_workspace_agent_spec(
        asset_repository=getattr(plane, "workspace_asset_repository", None),
        spec_registry=getattr(plane, "spec_registry", None),
        workspace_id=str(workspace_id),
        asset_id=spec_id,
        version=version,
        definition_hash=definition_hash,
    )
    return resolved, authority


async def _load_chat_history(
    plane: CosaAgentPlane, *, conversation_id: str, run_id: str
) -> list[dict[str, str]]:
    """ADR-CONV-002 — các lượt trước của conversation (trừ lượt hiện tại) trong
    ngân sách COSA_CHAT_HISTORY_MESSAGES / COSA_CHAT_HISTORY_MAX_CHARS. Lỗi đọc
    không làm hỏng run: chạy như single-turn và ghi log."""
    max_messages, max_chars = history_limits()
    if max_messages <= 0 or max_chars <= 0:
        return []
    try:
        messages = await plane.conversation_repository.list_messages(conversation_id)
    except Exception:
        logger.warning("run_id=%s load chat history failed", run_id, exc_info=True)
        return []
    return build_history(
        messages, exclude_run_id=run_id, max_messages=max_messages, max_chars=max_chars
    )


async def _load_project_facts(
    plane: CosaAgentPlane, *, workspace_id: str, project_id: str | None
) -> list[str]:
    """Fact dự án founder đã xác nhận (G-8), cũ -> mới. Lỗi đọc -> [] + log."""
    service = getattr(plane, "memory_service", None)
    if service is None or not project_id:
        return []
    try:
        items = await list_project_facts(
            service, workspace_id=workspace_id, project_id=str(project_id)
        )
    except Exception:
        logger.warning("load project facts failed ws=%s", workspace_id, exc_info=True)
        return []
    return [i.content for i in reversed(items)]


async def _approval_required_payload(
    plane: Any, wait_desc: Any, *, locale: str | None, project_name: str | None
) -> dict[str, Any]:
    """Payload SSE `approval.required` kèm tóm tắt cho thẻ duyệt trong chat (spec
    2026-09-27-chat-business-actions §4.5): capability, bậc T0–T3 và title/detail dựng từ
    tham số tool theo locale — không có ID. Tham số thô KHÔNG đi ra client."""
    appr_id = wait_desc.related_ref if wait_desc else None
    payload: dict[str, Any] = {
        "approval_id": appr_id,
        "checkpoint_ref": wait_desc.checkpoint_ref if wait_desc else None,
        "reason": wait_desc.reason if wait_desc else "Approval required",
    }
    capability_id: str | None = None
    args: dict[str, Any] = {}
    try:
        approval = await plane.repository.get_approval(appr_id) if appr_id else None
        if approval is not None:
            capability_id = capability_id_for_tool(approval.action, MATRIX)
            tool_call = (
                await plane.repository.get_tool_call(approval.tool_call_id)
                if approval.tool_call_id
                else None
            )
            if tool_call is not None and isinstance(tool_call.input_payload, dict):
                args = tool_call.input_payload
    except Exception:
        # Tóm tắt chỉ để hiển thị — thiếu thì thẻ dùng mẫu chung, không làm hỏng run.
        logger.warning("approval summary unavailable", extra={"approval_id": appr_id})
    payload["capability_id"] = capability_id
    payload["tier"] = MATRIX[capability_id].tier.value if capability_id else None
    payload["summary"] = summarize_action(capability_id, args, locale, project_name=project_name)
    return payload


def _is_chat_resume(payload: dict[str, Any]) -> bool:
    """Run chat của founder (có conversation thật), không phải run nền WGA/autopilot."""
    conversation_id = str(payload.get("conversation_id") or "")
    if payload.get("autopilot") is True or payload.get("agent_profile") == (
        "customer_support_autopilot"
    ):
        return False
    return (
        bool(conversation_id)
        and conversation_id != "unknown"
        and not (
            conversation_id.startswith("wga_") or str(payload.get("run_id", "")).startswith("wga_")
        )
    )


async def _verify_rejected_resume(
    plane: Any,
    *,
    run_id: str,
    tool_call_id: str,
    checkpoint_ref: str,
    approval_id: str | None,
    snapshot: Any,
) -> str | None:
    """None nếu được resume với quyết định từ chối; ngược lại trả lý do chặn. Approval phải
    bind đúng run_id + tool_call_id + checkpoint_ref (quy tắc 5) và thật sự đã bị từ chối."""
    if snapshot.workspace_status != "active" or snapshot.principal_status != "active":
        return "tenant_or_principal_inactive"
    approval = await plane.repository.get_approval(approval_id) if approval_id else None
    if approval is None:
        approval = await plane.repository.get_approval_by_tool_call(tool_call_id)
    if (
        approval is None
        or approval.run_id != run_id
        or approval.tool_call_id != tool_call_id
        or approval.checkpoint_ref != checkpoint_ref
    ):
        return "approval_binding_mismatch"
    if approval.status not in ("denied", "rejected"):
        return f"approval_not_rejected:{approval.status}"
    return None


async def _resume_agent_member_id(
    plane: Any, *, run_id: str, workspace_id: Any, project_id: Any
) -> str | None:
    """AI member đang giữ profile của run trong Project team (None nếu không xác định được)."""
    if not workspace_id or not project_id:
        return None
    try:
        run = await plane.repository.get_run(run_id)
        spec_id = getattr(run, "root_executable_id", None) if run is not None else None
        profile_key = next(
            (key for key, spec in _AGENT_PROFILE_SPECS.items() if spec.id == spec_id), None
        )
        if profile_key not in PROJECT_TEAM_OPERATING_PROFILES:
            return None
        team_client = getattr(plane, "project_team_client", None) or ProjectTeamClient()
        authority = await team_client.get_run_authority(
            workspace_id=str(workspace_id), project_id=str(project_id), profile_key=profile_key
        )
    except Exception:
        logger.warning("resume: project team authority unavailable", extra={"run_id": run_id})
        return None
    return str(authority.agent_workforce_member_id)


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

    async def _fail(error: str, **extra: Any) -> RunTaskResult:
        conversation_id = payload.get("conversation_id")
        stream_repo = getattr(plane, "stream_event_repository", None)
        if stream_repo and conversation_id and stream_mgr:
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id=conversation_id,
                event_type="run.failed",
                payload={"error": error, **extra},
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
            )
        return RunTaskResult(status="failed", error=error, run_id=run_id)

    # Agent workspace (C1): profile của run = profile của agent built-in gốc, không phải giá trị
    # client gửi. Authority lấy từ ProjectAgentDeployment của company, không từ startup team.
    deployment_id = payload.get("project_agent_deployment_id")
    workspace_agent: ResolvedWorkspaceAgent | None = None
    if deployment_id:
        if not workspace_id or not project_id:
            return await _fail("project_context_required")
        try:
            workspace_agent, deployment_authority = await _resolve_workspace_agent_run(
                plane,
                workspace_id=str(workspace_id),
                project_id=str(project_id),
                deployment_id=str(deployment_id),
            )
        except WorkspaceAgentError as exc:
            logger.warning(
                "run_id=%s workspace agent deployment %s rejected: %s",
                run_id,
                deployment_id,
                exc.reason_code,
            )
            return await _fail(exc.reason_code)
        agent_profile = workspace_agent.profile_key
        payload["agent_profile"] = agent_profile
        payload["spec_hash"] = workspace_agent.spec.definition_hash
        payload["agent_workforce_member_id"] = str(deployment_authority["workforceMemberId"])
        payload.pop("copilot", None)

    # Chỉ profile có đường authority cho chat/schedule/event mới được chạy ở đây.
    # Executive/overlay chạy qua deliberation (authority = Project deployment +
    # overlay pin), kickoff chạy qua route riêng — không cho payload tự chọn.
    if agent_profile not in RUN_ELIGIBLE_PROFILES:
        logger.error("run_id=%s agent_profile %r not run-eligible", run_id, agent_profile)
        return await _fail("agent_profile_not_run_eligible")

    if agent_profile in PROJECT_SCOPED_RUN_PROFILES and (not workspace_id or not project_id):
        return await _fail("project_context_required")

    # Project-scoped Founder Hub — defense-in-depth: dù conversation_routes.py
    # đã verify request project_id == conversation.project_id TRƯỚC khi
    # schedule, worker KHÔNG tin payload đã schedule là nguồn sự thật cuối
    # cùng (payload có thể trôi/stale giữa lúc schedule và lúc dispatch thật
    # — rolling deploy, retry, hoặc caller khác của scheduler ngoài HTTP
    # route). Re-check với ConversationRecord ĐÃ LƯU TRƯỚC khi chạm kernel.
    if agent_profile in PROJECT_SCOPED_RUN_PROFILES:
        conversation_id = payload.get("conversation_id")
        conv_repo = getattr(plane, "conversation_repository", None)
        if conversation_id and conv_repo is not None:
            persisted_conv = await conv_repo.get_conversation(conversation_id)
            if (
                persisted_conv is not None
                and persisted_conv.project_id
                and persisted_conv.project_id != project_id
            ):
                logger.error(
                    "run_id=%s project_id mismatch: payload=%r conversation=%r, failing closed",
                    run_id,
                    project_id,
                    persisted_conv.project_id,
                )
                return await _fail("project_context_mismatch")

    if workspace_agent is not None:
        with log_context(run_id=run_id, workspace_id=workspace_id):
            await _execute_run_task_inner(
                plane,
                stream_mgr,
                payload,
                resolved_spec=workspace_agent.spec,
                compliance_spec=workspace_agent.origin_spec,
            )
            return RunTaskResult(status="completed", run_id=run_id)

    if agent_profile in PROJECT_TEAM_OPERATING_PROFILES:
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
            # Không đưa str(exc) ra stream: nó chứa thân response thô của
            # Company. Chỉ trả status code đã phân loại; chi tiết nằm ở log.
            return await _fail("project_team_authority_denied", status_code=exc.status_code)

        if (
            str(authority.workspace_id) != str(workspace_id)
            or str(authority.project_id) != str(project_id)
            or authority.profile_key != agent_profile
        ):
            return await _fail("project_context_mismatch")

        local_spec = _AGENT_PROFILE_SPECS.get(agent_profile)
        if not local_spec:
            # Profile có trong startup-team nhưng không có spec (vd. `crm`):
            # phải phát run.failed, nếu không client chờ stream mãi.
            return await _fail("unknown_agent_profile")

        pinned_spec = await _spec_for_authority(plane, local_spec, authority.spec, run_id=run_id)
        if pinned_spec is None:
            return await _fail("spec_hash_mismatch")
        local_spec = pinned_spec

        if agent_profile == "customer_support" and not authority.policy_snapshot.get(
            "knowledge_gate_passed", False
        ):
            return await _fail("support_knowledge_gate_required")

        payload["assignment_version"] = authority.assignment_version
        payload["spec_hash"] = authority.spec.hash
        # AI member của Project team: gateway xin live authorization ticket cho capability
        # ghi bằng member này (grant do founder cấp ở company quyết định, không phải prompt).
        payload["agent_workforce_member_id"] = str(authority.agent_workforce_member_id)

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
    *,
    resolved_spec: AgentSpec | None = None,
    compliance_spec: AgentSpec | None = None,
) -> None:
    run_id = payload["run_id"]
    conversation_id = payload["conversation_id"]
    agent_profile = payload.get("agent_profile") or "operations"
    principal = payload["principal"]
    workspace_id = payload["workspace_id"]
    # Task 3 — xem comment ở execute_run_task() phía trên cùng lý do.
    project_id = payload.get("project_id")
    stream_repo = plane.stream_event_repository

    async def _reject(content: str, error_payload: dict[str, Any]) -> None:
        """Ghi assistant message `failed` + phát `run.failed` (cùng scope Project)."""
        await _append_message(
            plane,
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            run_id=run_id,
            status_="failed",
            project_id=project_id,
        )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload=error_payload,
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
        )

    # IA24: trước đây payload["user_prompt"] truy cập trực tiếp — một payload
    # event-driven thiếu field này (vd producer/adapter cũ, hoặc lỗi upstream)
    # sẽ raise KeyError chưa được bắt, làm hỏng cả task thay vì fail-closed có
    # kiểm soát như đường thiếu delegation_token ngay bên dưới.
    user_prompt = payload.get("user_prompt")
    if not user_prompt:
        logger.error("run_id=%s missing user_prompt in payload, failing closed", run_id)
        await _reject("Missing user_prompt — run rejected", {"error": "missing_user_prompt"})
        return

    bearer_token = payload.get("delegation_token")
    if not bearer_token:
        await _reject(
            "Missing delegation token — run rejected", {"error": "missing_delegation_token"}
        )
        return

    local_spec = _AGENT_PROFILE_SPECS.get(agent_profile)
    if local_spec is None:
        logger.error(
            "unsupported agent_profile %r for run_id=%s, failing closed",
            agent_profile,
            run_id,
        )
        await _reject(
            f"Unsupported agent profile '{agent_profile}' — run rejected",
            {"error": f"unsupported_agent_profile_{agent_profile}"},
        )
        return

    assignment_id = payload.get("assignment_id")
    company_workforce_member_id = payload.get("company_workforce_member_id")

    if assignment_id and plane.workforce_repository is not None:
        assignment = await plane.workforce_repository.get_assignment(workspace_id, assignment_id)
        if assignment is None or assignment.status != "ACTIVE":
            logger.error("assignment %r not found or retired for run_id=%s", assignment_id, run_id)
            await _reject(
                "Workforce assignment retired or not found — run rejected",
                {"error": "workforce_assignment_retired"},
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
        await _reject(
            "Unable to verify tenant policy — run rejected",
            {"error": "policy_snapshot_unavailable"},
        )
        return

    # Resolve exact spec + dựng request + compliance qua apps/cosa/worker/
    # run_core.py (WGA int. point #2) — lõi dùng chung với headless task
    # goal_decomposition / workspace_task_sweep. Hành vi client-facing của
    # nhánh lỗi giữ nguyên: map RunCoreError.reason_code -> đúng message/event
    # cũ.
    if resolved_spec is not None:
        # Agent workspace: spec hiệu lực đã dựng từ asset PUBLISHED (exact hash) + spec gốc đã pin.
        spec = resolved_spec
    else:
        try:
            spec = await resolve_spec(plane, run_id=run_id, local_spec=local_spec)
        except RunCoreError:
            await _reject(
                "Unable to resolve agent spec from registry — run rejected",
                {"error": "spec_resolution_unavailable"},
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
    elif payload.get("agent_workforce_member_id"):
        extra_md["agent_workforce_member_id"] = str(payload["agent_workforce_member_id"])
    if assignment_id:
        extra_md["assignment_id"] = str(assignment_id)
    for name_key in ("project_name", "workspace_name"):
        if payload.get(name_key):
            extra_md[name_key] = str(payload[name_key])
    # project_id do conversation_routes đặt từ project đã verify, không lấy từ client.
    if project_id:
        extra_md["project_id"] = str(project_id)
    # Chat: mọi hành động T2 (ghi thật vào dữ liệu nội bộ) buộc founder duyệt trước khi chạy
    # (spec 2026-09-27-chat-business-actions §4.1). Policy engine chỉ SIẾT ALLOW thành
    # REQUIRE_APPROVAL — DENY của company/tenant vẫn giữ nguyên.
    extra_md[REQUIRE_APPROVAL_CAPABILITIES_KEY] = sorted(CHAT_T2_CAPABILITIES)
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

    history = await _load_chat_history(plane, conversation_id=conversation_id, run_id=run_id)
    facts = await _load_project_facts(plane, workspace_id=workspace_id, project_id=project_id)
    if facts:
        extra_md["project_facts"] = facts

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
            history=history,
            compliance_spec=compliance_spec,
        )
    except RunCoreError as exc:
        if exc.reason_code == "compliance_resolver_unavailable":
            await _reject(
                "AI compliance resolver not configured — run rejected",
                {"error": "compliance_resolver_unavailable"},
            )
            return
        # compliance_denied — chỉ emit reason code, không leak str(exc).
        code = exc.compliance_code or "UNKNOWN"
        if code != "MISSING_DELEGATION_TOKEN":
            await _reject(
                f"AI compliance check failed — run rejected: {code}",
                {"error": "compliance_denied", "reason_code": code},
            )
        return

    _run_start = time.monotonic()
    try:
        run_result, _ = await run_kernel(plane, prep, workspace_id=workspace_id, run_id=run_id)

        _run_duration = time.monotonic() - _run_start

        # Token/usage được ghi tập trung trong run_core.run_kernel (theo route thật).

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
                        confirm_msg = await _append_message(
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
                        # Chèn SAU run.completed nên client không thấy qua run
                        # stream — báo qua Project Activity stream (WGA G9).
                        await record_agent_chat_message_activity(
                            plane,
                            workspace_id=workspace_id,
                            project_id=project_id,
                            conversation_id=conversation_id,
                            message=confirm_msg,
                            run_id=run_id,
                            message_kind="goal_confirm",
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
                payload=await _approval_required_payload(
                    plane,
                    wait_desc,
                    locale=locale,
                    project_name=payload.get("project_name"),
                ),
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
            classified = classify_run_error(err_msg, locale)
            logger.warning(
                "agent run failed",
                extra={"run_id": run_id, "error_code": classified.code, "error_raw": err_msg},
            )
            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content=classified.user_message,
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
                # `error` giữ cho consumer cũ nhưng chỉ mang mã đã phân loại —
                # chuỗi thô của provider chỉ nằm trong log (`error_raw`).
                payload={
                    "error": classified.code,
                    "error_code": classified.code,
                    "user_message": classified.user_message,
                },
                activity_service=getattr(plane, "project_activity_service", None),
                workspace_id=workspace_id,
                project_id=project_id,
            )

    except RunCoreError as exc:
        # Lỗi có mã ổn định lúc bind route (hết quota/ngân sách, profile sai):
        # báo đúng nguyên nhân thay vì "lỗi không mong muốn".
        _run_duration = time.monotonic() - _run_start
        record_run_outcome("failed", duration_sec=_run_duration)
        logger.warning("run_id=%s blocked: %s (%s)", run_id, exc.reason_code, exc.compliance_code)
        friendly = user_message_for_code(exc.reason_code, payload.get("locale") or "vi-VN")
        await _reject(
            friendly,
            {
                "error": exc.reason_code,
                "error_code": exc.compliance_code or exc.reason_code,
                "user_message": friendly,
            },
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
        await _reject(
            "Đã xảy ra lỗi không mong muốn khi thực thi run. Vui lòng thử lại hoặc liên hệ hỗ trợ.",
            {"error": "internal_error"},
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
    rejected = payload.get("decision") == "rejected"

    if rejected and not _is_chat_resume(payload):
        # Run nền (WGA task, autopilot…) giữ hành vi cũ: từ chối không resume.
        logger.info("rejected approval on non-chat run %s — not resuming", run_id)
        return

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
    resume_updates: dict[str, Any] = {"approved_tool_calls": {tool_call_id: not rejected}}
    # Scope project của run cũng phải có khi resume (context resume dựng từ
    # updates) — để tool tự điền/chặn project_id như lúc chạy lần đầu.
    if project_id:
        resume_updates["project_id"] = str(project_id)
    # Context resume dựng lại từ updates: phải mang lại danh sách T2 buộc duyệt, nếu không
    # hành động T2 kế tiếp trong lượt resume sẽ chạy mà không cần founder duyệt.
    resume_updates[REQUIRE_APPROVAL_CAPABILITIES_KEY] = sorted(CHAT_T2_CAPABILITIES)
    # AI member của Project team cho live authorization ticket khi tool đã duyệt chạy — resolve
    # lại từ authority hiện hành (member bị gỡ khỏi team thì ticket fail closed).
    agent_member_id = await _resume_agent_member_id(
        plane, run_id=run_id, workspace_id=workspace_id, project_id=project_id
    )
    if agent_member_id:
        resume_updates["agent_workforce_member_id"] = agent_member_id
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
        if rejected:
            # Từ chối: tool KHÔNG chạy, SDK trả kết quả "bị từ chối" cho model. Vẫn kiểm
            # approval đúng binding + đã bị từ chối và tenant/principal còn active.
            reject_block = await _verify_rejected_resume(
                plane,
                run_id=run_id,
                tool_call_id=tool_call_id,
                checkpoint_ref=checkpoint_ref,
                approval_id=payload.get("approval_id"),
                snapshot=fresh_snapshot,
            )
            if reject_block is not None:
                logger.warning("rejected resume blocked run_id=%s: %s", run_id, reject_block)
                await stream_mgr.emit(
                    stream_repo,
                    run_id=run_id,
                    conversation_id=conversation_id,
                    event_type="run.failed",
                    payload={"error": "resume_verification_failed", "reason": reject_block},
                    activity_service=getattr(plane, "project_activity_service", None),
                    workspace_id=workspace_id,
                    project_id=project_id,
                )
                return
        else:
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
    resume_route = None
    resume_model = None
    try:
        resume_kernel, resume_route, resume_model = await kernel_for_resume(
            plane, workspace_id=workspace_id, run_id=run_id
        )
        async with trace_span(
            "kernel.resume",
            attributes={
                "run_id": run_id,
                "checkpoint_ref": checkpoint_ref,
                "workspace_id": workspace_id,
            },
        ):
            res = await resume_kernel.resume(
                run_id=run_id,
                checkpoint_ref=checkpoint_ref,
                updates=resume_updates,
            )
    except Exception:
        # Cùng quy tắc Task 6 như `_execute_run_task_inner`: không đưa exception
        # thô ra client, nhưng PHẢI phát run.failed — trước đây lỗi ở đây rò
        # ra worker, client chờ stream mãi.
        record_run_outcome("failed", duration_sec=time.monotonic() - _resume_start)
        logger.exception("agent resume failed", extra={"run_id": run_id})
        if conversation_id != "unknown":
            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content="Đã xảy ra lỗi không mong muốn khi tiếp tục run sau khi duyệt. Vui lòng thử lại.",
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
        return
    _resume_duration = time.monotonic() - _resume_start

    if resume_route is not None:
        await record_route_usage(
            plane,
            route=resume_route,
            model_client=resume_model,
            result=res,
            run_id=run_id,
            workspace_id=resume_route.workspace_id,
            project_id=project_id,
            agent_spec_id=resume_route.agent_spec_id,
        )
    elif getattr(res, "usage", None):
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
        # Từ chối không bao giờ đóng task (chỉ run chat mới resume khi từ chối).
        if not rejected:
            with contextlib.suppress(Exception):
                _sub = str(payload.get("principal") or "0").split(":")[-1]
                await advance_wga_task_after_resume(
                    plane,
                    run_id=run_id,
                    workspace_id=workspace_id,
                    sub=_sub,
                    output_text=output_text,
                )

    elif res.status == RunStatus.WAITING_APPROVAL:
        # Bước kế tiếp sau khi resume lại cần duyệt: phát approval.required như
        # lần chạy đầu, nếu không UI không biết có approval mới và run treo.
        record_run_outcome("waiting_approval", duration_sec=_resume_duration)
        wait_desc = res.interruptions_waits[0] if res.interruptions_waits else None
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="approval.required",
            payload=await _approval_required_payload(
                plane,
                wait_desc,
                locale=payload.get("locale"),
                project_name=payload.get("project_name"),
            ),
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
        )

    else:
        record_run_outcome("failed", duration_sec=_resume_duration)
        err_msg = res.errors[0] if res.errors else "Run failed"
        classified = classify_run_error(err_msg, payload.get("locale") or "vi-VN")
        logger.warning(
            "agent resume failed",
            extra={"run_id": run_id, "error_code": classified.code, "error_raw": err_msg},
        )
        if conversation_id != "unknown":
            await _append_message(
                plane,
                conversation_id=conversation_id,
                role="assistant",
                content=classified.user_message,
                run_id=run_id,
                status_="failed",
                project_id=project_id,
            )
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id=conversation_id,
            event_type="run.failed",
            payload={
                "error": classified.code,
                "error_code": classified.code,
                "user_message": classified.user_message,
            },
            activity_service=getattr(plane, "project_activity_service", None),
            workspace_id=workspace_id,
            project_id=project_id,
        )


# Re-export: task lịch/automation nằm ở scheduled_tasks.py (G-11).
from apps.cosa.worker.scheduled_tasks import (
    execute_automation_run_task,
    execute_scheduled_session_task,
)
