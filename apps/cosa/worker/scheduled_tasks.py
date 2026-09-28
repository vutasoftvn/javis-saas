"""Worker task chạy theo lịch và automation (tách khỏi `handlers.py`, review
2026-09-27 G-11). `handlers.py` re-export `execute_scheduled_session_task` và
`execute_automation_run_task` để đường import cũ vẫn dùng được."""

import contextlib
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from agent.contracts.run import RunStatus
from agent.conversations.models import ConversationRecord, MessageRecord

from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.auth.jwt import mint_company_delegation
from apps.cosa.capabilities.client import CompanyServiceClient, CompanyServiceError
from apps.cosa.capabilities.connector_grant_client import ConnectorGrantHttpClient
from apps.cosa.capabilities.email_digest_read import EMAIL_CONNECTOR_KEY
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.config.planes import resolve_platform_control_plane_url
from apps.cosa.observability.otel import inject_trace_carrier

logger = logging.getLogger("apps.cosa.worker.handlers")

__all__ = ["execute_automation_run_task", "execute_scheduled_session_task"]

# B5 (Task 6b) — 2 capability duy nhất được phép nằm trong snapshot uỷ quyền
# trước (khớp `PRE_AUTHORIZABLE_CAPABILITY_IDS` phía services/cosa, Task 6).
FOUNDER_NOTIFY_SEND_CAPABILITY_ID = "founder.notify.send"
EMAIL_DIGEST_READ_CAPABILITY_ID = "email.digest.read"

# Mã lỗi preflight founder-notify (Task 3/ADR mục 8) khiến execution
# `blocked_reauth` (founder phải xử lý lại — thu hồi kênh, mất quyền
# founder/co-founder). `founder_channel_ambiguous` KHÔNG nằm trong danh sách
# này — đó là lỗi cấu hình (nhiều kênh, không rõ chọn cái nào), khác hẳn
# "founder cần làm lại" — map sang `failed` (ADR mục 4/Consequences B5).
_FOUNDER_PREFLIGHT_BLOCKED_REAUTH_CODES = (
    "founder_channel_unavailable",
    "founder_owner_not_authorized",
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


class _ScheduledExecutionBlocked(ValueError):
    """B5 (Task 6b) — báo hiệu preflight đã chặn run TRƯỚC khi tạo
    conversation/gọi model; control plane đã được báo hoàn thành
    (`_report_schedule_execution_complete`) TRƯỚC KHI exception này được
    raise — caller không cần (và không nên) báo lại."""


async def _terminate_preflight(
    schedule_exec_id: str | None, *, run_id: str, state: str, error: str
) -> None:
    logger.error("schedule_execution_id=%s preflight blocked run: %s", schedule_exec_id, error)
    await _report_schedule_execution_complete(
        schedule_exec_id, state=state, error=error, conversation_id=None, run_id=run_id
    )
    raise _ScheduledExecutionBlocked(error)


async def _preflight_preauthorized_schedule(
    *,
    schedule_exec_id: str | None,
    run_id: str,
    workspace_id: str,
    pre_authorized_capability_ids: list[str],
    founder_member_id: str | None,
    founder_user_id: str | None,
) -> str:
    """B5 (Task 6b) — lịch nền uỷ quyền trước (snapshot không rỗng, Task 6):
    kiểm TRƯỚC khi tạo conversation/gọi model — không đọc email, không tiêu
    token nếu kênh founder-notify hoặc connector email-read đã hỏng.

    Trả về company delegation token (`sub=founder_user_id`, `aud=company`,
    mint bởi `mint_company_delegation` — cùng cơ chế Task 3/4 dùng cho mọi
    lệnh gọi Company khác của COSA) dùng cho chính các lệnh gọi preflight
    này. Phần còn lại của run (tool call `founder.notify.send`/`email.digest.read`
    giữa lúc chạy) KHÔNG dùng lại token này trực tiếp — `principal` của run
    được set thành `user:<founder_user_id>` (xem `execute_scheduled_session_task`)
    để `ComplianceResolver.resolve_for_run` (Task 3/5) tự mint delegation
    cùng `sub` cho từng tool call, đúng cơ chế chat run của chính founder
    dùng — không phát minh đường mint thứ hai.

    Raise `_ScheduledExecutionBlocked` SAU KHI đã báo control plane (cùng
    idiom với khối kiểm project_id ở `execute_scheduled_session_task`).
    """
    if not founder_user_id or not founder_member_id:
        # Task 6 đã bắt buộc cả 2 field này khi preAuthorizedCapabilityIds
        # không rỗng lúc tạo lịch — snapshot thiếu nghĩa là dữ liệu control
        # plane hỏng/lệch, không phải điều kiện người dùng tự sửa được từ
        # chat; `blocked_reauth` để hiện đúng "cần founder xử lý lại kế
        # hoạch tự động hoá" thay vì gợi ý sai "thử lại là được".
        await _terminate_preflight(
            schedule_exec_id,
            run_id=run_id,
            state="blocked_reauth",
            error=f"preauthorization_snapshot_invalid: schedule_execution_id={schedule_exec_id}",
        )

    delegation_token = mint_company_delegation(
        sub=founder_user_id,  # type: ignore[arg-type]  # đã kiểm not-None ở trên
        workspace_id=workspace_id,
        run_id=run_id,
        capability_ids=pre_authorized_capability_ids,
    )

    if FOUNDER_NOTIFY_SEND_CAPABILITY_ID in pre_authorized_capability_ids:
        try:
            client = CompanyServiceClient()
            await client.get(
                "/identity/founder-notifications/preflight",
                headers={
                    "Authorization": f"Bearer {delegation_token}",
                    "X-Workspace-Id": str(workspace_id),
                },
            )
        except CompanyServiceError as exc:
            message = str(exc)
            if any(code in message for code in _FOUNDER_PREFLIGHT_BLOCKED_REAUTH_CODES):
                await _terminate_preflight(
                    schedule_exec_id, run_id=run_id, state="blocked_reauth", error=message
                )
            else:
                # founder_channel_ambiguous (lỗi cấu hình) hoặc lỗi hạ tầng
                # khác (mạng, 5xx) — `failed`, scheduler tự thử lại lần chạy
                # kế tiếp; không gợi ý sai "cần founder reconnect".
                await _terminate_preflight(
                    schedule_exec_id, run_id=run_id, state="failed", error=message
                )

    if EMAIL_DIGEST_READ_CAPABILITY_ID in pre_authorized_capability_ids:
        connector_client = ConnectorGrantHttpClient()
        try:
            res = await connector_client.assert_usable_for_execution(
                EMAIL_CONNECTOR_KEY,
                workspace_id=workspace_id,
                execution_id=str(schedule_exec_id),
                action=EMAIL_DIGEST_READ_CAPABILITY_ID,
                required_scope="mail:read",
            )
        except Exception as exc:
            # Lỗi hạ tầng gọi control plane (HTTP != 200, mạng) — `failed`,
            # KHÔNG `blocked_reauth` (không phải "founder cần xử lý lại").
            await _terminate_preflight(
                schedule_exec_id,
                run_id=run_id,
                state="failed",
                error=f"connector_preflight_unavailable: {exc}",
            )
        else:
            if not res.get("ok"):
                code = res.get("error") or "connector_reauth_required"
                # Mọi lý do control plane từ chối grant connector ở đây (thiếu
                # snapshot, hết hạn, bị revoke, installation disabled, thiếu
                # scope) đều quy về "founder phải kết nối/cấp lại connector" —
                # cùng nghĩa `blocked_reauth`, khác class với lỗi cấu hình
                # founder-notify (ambiguous) vì connector không có khái niệm
                # "nhiều lựa chọn không rõ chọn cái nào".
                await _terminate_preflight(
                    schedule_exec_id, run_id=run_id, state="blocked_reauth", error=code
                )

    return delegation_token


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
    # B5 (Task 6b) — snapshot uỷ quyền trước (Task 6): rỗng ⇒ lịch cũ, hành vi
    # KHÔNG đổi (nguyên placeholder principal="service:scheduler"). Không
    # rỗng ⇒ lịch đã được founder duyệt kèm capability cụ thể qua thẻ kế
    # hoạch tự động hoá — worker phải mint danh tính founder + preflight
    # trước khi chạm model (xem khối preflight bên dưới).
    pre_authorized_capability_ids: list[str] = []
    founder_member_id: str | None = None
    founder_user_id: str | None = None
    token_budget_per_run: int | None = None

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
                    raw_pre_auth = data.get("preAuthorizedCapabilityIdsSnapshot")
                    if isinstance(raw_pre_auth, list):
                        pre_authorized_capability_ids = [str(c) for c in raw_pre_auth if c]
                    founder_member_id = data.get("founderMemberIdSnapshot") or None
                    founder_user_id = data.get("founderUserIdSnapshot") or None
                    raw_budget = data.get("tokenBudgetPerRunSnapshot")
                    token_budget_per_run = int(raw_budget) if raw_budget is not None else None
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

    if token_budget_per_run is not None:
        # B5 (Task 6b) mục 7 — `tokenBudgetPerRunSnapshot` được đọc từ
        # snapshot nhưng CHƯA áp dụng: chưa tìm thấy cơ chế enforce ngân
        # sách token cho MỘT run cụ thể trong kernel/run hiện có
        # (`packages/agent/governance/budget_gate.py::BudgetGate` chỉ có quota
        # per-tenant đăng ký sẵn qua `_quotas`, không có hook nhận override
        # theo từng RunRequest) — chỉ log để không âm thầm bỏ qua giá trị đã
        # founder duyệt. Không bịa ra một cơ chế enforce mới trong task này.
        logger.info(
            "schedule_execution_id=%s tokenBudgetPerRunSnapshot=%s captured but NOT enforced "
            "(no per-run budget hook wired yet — B5 Task 6b concern)",
            schedule_exec_id,
            token_budget_per_run,
        )

    # B5 (Task 6b) — lịch nền uỷ quyền trước (snapshot không rỗng): preflight
    # TRƯỚC khi tạo conversation/run — kênh founder-notify bị thu hồi hoặc
    # connector email-read thiếu grant thì dừng ở đây, không tạo conversation
    # mồ côi, không đọc email, không tiêu token. Lịch cũ (snapshot rỗng) bỏ
    # qua hoàn toàn khối này — hành vi KHÔNG đổi.
    scheduler_principal = "service:scheduler"
    if pre_authorized_capability_ids:
        await _preflight_preauthorized_schedule(
            schedule_exec_id=schedule_exec_id,
            run_id=run_id,
            workspace_id=workspace_id,
            pre_authorized_capability_ids=pre_authorized_capability_ids,
            founder_member_id=founder_member_id,
            founder_user_id=founder_user_id,
        )
        # Danh tính founder cho phần còn lại của run (mint company delegation
        # theo `sub=founder_user_id` như chat run làm — ComplianceResolver tự
        # mint lại theo `request.principal` cho từng tool call, xem docstring
        # `_preflight_preauthorized_schedule`). `_scheduler_dispatch`/
        # `pre_authorized_capability_ids` trong run_payload (đặt bên dưới) là
        # điều kiện THẬT worker/handlers.py dùng để bỏ approval — không phải
        # giá trị `principal` này (payload chat/API bên ngoài không có 2 key
        # nội bộ đó dù có tự set `principal="user:..."`, xem
        # apps/cosa/worker/handlers.py::_execute_run_task_inner).
        scheduler_principal = f"user:{founder_user_id}"

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

    run_payload: dict[str, Any] = {
        "run_id": run_id,
        "conversation_id": conversation_id,
        "user_prompt": prompt_template,
        "principal": scheduler_principal,
        "workspace_id": workspace_id,
        "agent_name": agent_profile,
        "agent_profile": agent_profile,
        "project_id": project_id,
        "delegation_token": payload.get("delegation_token") or "scheduled_worker_service_token",
    }
    if pre_authorized_capability_ids:
        run_payload["_scheduler_dispatch"] = True
        run_payload["pre_authorized_capability_ids"] = pre_authorized_capability_ids
        # Fix review (Important #2) — handlers.py đưa field này vào
        # metadata/context của run để build_connector_grant_resolver assert
        # connector theo executionId thay vì conversationId (lịch nền không
        # bao giờ có session grant theo conversation).
        run_payload["schedule_execution_id"] = schedule_exec_id
    # Agent workspace (C1): worker kiểm lại deployment với company trước khi chạy.
    if payload.get("project_agent_deployment_id"):
        run_payload["project_agent_deployment_id"] = str(payload["project_agent_deployment_id"])

    error_msg = None
    state = "succeeded"
    try:
        # Import muộn: handlers re-export module này (tránh import vòng).
        from apps.cosa.worker.handlers import execute_run_task

        run_res = await execute_run_task(plane, stream_mgr, run_payload)
        if run_res and run_res.status in ("failed", "blocked_reauth"):
            state = run_res.status
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
