"""WGA worker handlers — headless task run của Weekly Goal → Agent Execution.

- `execute_goal_decomposition_task`: nhận mục tiêu tuần → chạy agent operations
  ra structured plan → POST /operations/execution-plans (draft).
- `execute_workspace_task_sweep_task`: quét task AI đã materialize (class AUTO),
  chạy từng cái, gọi operations.task.advance; tự re-schedule nếu còn.

Cả hai xác thực call sang services/company bằng cosa company-delegation JWT
(`mint_company_delegation`, scoped {workspace_id, run_id, capability_ids}) —
KHÔNG có user session. Không dùng policy_snapshot (headless, kiểu autopilot).

v1 boundary (xem spec §15.2c):
- sweep chỉ chạy autonomy_class == "AUTO"; NEEDS_APPROVAL materialize rồi chờ
  founder (đường approval-resume là follow-up).
- kill-switch = env `WGA_SWEEP_ENABLED`; per-workspace kill-switch qua tenant
  policy là follow-up.
- chống loop = giới hạn độ sâu re-schedule (`sweep_depth`), chưa có DB counter.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import re
import uuid
from typing import Any

from agent.artifacts import WorkspaceArtifact
from agent.contracts.run import RunStatus
from agent.conversations.models import MessageRecord
from agent.verification.models import Verdict

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.capability_risk_map import capability_risk
from apps.cosa.agents.goal_decomposition import (
    OWNER_AGENT_PROFILES,
    PlanSchemaError,
    build_decomposition_prompt,
    parse_plan_output,
    validate_plan_capabilities,
)
from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.auth.jwt import mint_company_delegation
from apps.cosa.capabilities.client import CompanyServiceError
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.policies.evaluator import REQUIRE_APPROVAL_CAPABILITIES_KEY
from apps.cosa.worker.provider_errors import classify_run_error
from apps.cosa.worker.run_core import RunCoreError, prepare_run, run_kernel
from apps.cosa.worker.wga_verify import (
    WGA_TASK_OUTPUT_DISPLAY_NAME,
    WGA_TASK_OUTPUT_REF_TEMPLATE,
    VerificationOutcome,
    verification_enabled,
    verify_task_result,
)

logger = logging.getLogger(__name__)

__all__ = [
    "advance_wga_task_after_resume",
    "execute_goal_decomposition_task",
    "execute_workspace_task_sweep_task",
    "finalize_wga_task_completion",
    "record_agent_chat_message_activity",
    "record_wga_task_evidence",
]

# run_id của task-execution run trong sweep: wga_task_<task_id>_<hex>
_WGA_TASK_RUN_RE = re.compile(r"^wga_task_(\d+)_[0-9a-f]+$")

# Bảng tường minh profile -> spec, dựng từ đúng danh sách company route tới.
# Profile ngoài bảng vẫn fail closed (không fallback về operations).
_SPEC_BY_PROFILE = {p: AGENT_PROFILE_SPECS[p] for p in OWNER_AGENT_PROFILES}


def _capability_catalog() -> dict[str, list[str]]:
    """Capability thật của từng owner profile — nguồn cho prompt và validate."""
    return {p: list(spec.capability_refs) for p, spec in _SPEC_BY_PROFILE.items()}


_CAP_EXECUTION_PLAN_CREATE = "operations.execution_plan.create"
_CAP_TASK_LIST = "operations.task.list"
_CAP_TASK_ADVANCE = "operations.task.advance"

_MAX_SWEEP_DEPTH = 20


def _extract_text(run_result: Any) -> str:
    fo = getattr(run_result, "final_output", None)
    if isinstance(fo, dict):
        return str(fo.get("response", fo))
    return str(fo or "")


async def _advance_task(
    plane: CosaAgentPlane,
    *,
    workspace_id: str,
    task_id: str,
    to_status: str,
    run_id: str,
    token: str,
    note: str | None = None,
    evidence_refs: list[str] | None = None,
) -> bool:
    """Gọi operations.task.advance. Trả False nếu company từ chối (không raise —
    caller quyết định fallback)."""
    body: dict[str, Any] = {"toStatus": to_status, "runId": run_id}
    if note:
        body["note"] = note[:500]
    if evidence_refs:
        body["evidenceRefs"] = evidence_refs
    try:
        await plane.company_client.post(
            f"/operations/tasks/{task_id}/advance",
            json=body,
            headers={"X-Workspace-Id": workspace_id, "Authorization": f"Bearer {token}"},
        )
    except CompanyServiceError as exc:
        logger.warning("advance task=%s to=%s run=%s rejected: %s", task_id, to_status, run_id, exc)
        return False
    return True


async def record_wga_task_evidence(
    plane: CosaAgentPlane,
    *,
    workspace_id: str,
    run_id: str,
    output_text: str,
) -> list[str]:
    """Lưu output của task run thành WorkspaceArtifact và trả evidenceRefs.

    Company chỉ cho agent đóng task khi có ≥1 evidence (IA22/IA23). Không có
    output hoặc lưu artifact thất bại -> trả [] để task giữ `completion_pending`
    (run hoàn tất chưa mặc nhiên là task hoàn tất — R2/F05), không bịa evidence.
    """
    text = (output_text or "").strip()
    repo = getattr(plane, "artifact_repository", None)
    if not text or repo is None:
        return []
    data = text.encode("utf-8")
    try:
        artifact = WorkspaceArtifact(
            workspace_id=workspace_id,
            conversation_id=f"wga_task_{run_id}",
            run_id=run_id,
            artifact_kind="report",
            display_name=WGA_TASK_OUTPUT_DISPLAY_NAME,
            media_type="text/plain",
            object_ref=WGA_TASK_OUTPUT_REF_TEMPLATE.format(run_id=run_id),
            checksum=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
        )
        await repo.create(artifact)
    except Exception as exc:
        logger.warning("record task evidence failed run=%s: %s", run_id, exc)
        return []
    return [f"artifact:{artifact.artifact_id}", f"run:{run_id}"]


async def finalize_wga_task_completion(
    plane: CosaAgentPlane,
    *,
    workspace_id: str,
    task_id: str,
    run_id: str,
    token: str,
    evidence_refs: list[str] | None = None,
    summary: str | None = None,
    note: str = "completion_pending",
) -> bool:
    """Finalizer chung cho task WGA khi run hoàn tất (cả initial lẫn resumed).
    Trả True nếu task đã được đóng 'done'.

    Có evidence -> advance('done') kèm evidenceRefs (company kiểm tra lại).
    Không có evidence hoặc company từ chối -> giữ 'in_progress' + completion_pending
    để founder xác nhận (R2 / F05: run hoàn tất chưa mặc nhiên là task hoàn tất).
    """
    if evidence_refs:
        done = await _advance_task(
            plane,
            workspace_id=workspace_id,
            task_id=task_id,
            to_status="done",
            run_id=run_id,
            token=token,
            note=(summary or "completed_with_evidence"),
            evidence_refs=evidence_refs,
        )
        if done:
            return True
        note = "completion_rejected"

    await _advance_task(
        plane,
        workspace_id=workspace_id,
        task_id=task_id,
        to_status="in_progress",
        run_id=run_id,
        token=token,
        note=note or "completion_pending",
    )
    return False


async def advance_wga_task_after_resume(
    plane: CosaAgentPlane,
    *,
    run_id: str,
    workspace_id: str | None,
    sub: str,
    output_text: str = "",
) -> None:
    """Sau khi founder duyệt checkpoint và `execute_resume_task` chạy xong
    (COMPLETED), lưu evidence từ output rồi gọi finalizer chung."""
    m = _WGA_TASK_RUN_RE.match(run_id or "")
    if not m or not workspace_id:
        return
    task_id = m.group(1)
    token = mint_company_delegation(
        sub=sub or "0",
        workspace_id=workspace_id,
        run_id=run_id,
        capability_ids=[_CAP_TASK_ADVANCE],
    )
    evidence = await record_wga_task_evidence(
        plane, workspace_id=workspace_id, run_id=run_id, output_text=output_text
    )
    await finalize_wga_task_completion(
        plane,
        workspace_id=workspace_id,
        task_id=task_id,
        run_id=run_id,
        token=token,
        evidence_refs=evidence,
        summary=output_text.strip()[:500] or None,
        note="hoàn tất sau khi founder duyệt — chờ xác nhận",
    )


async def execute_goal_decomposition_task(
    plane: CosaAgentPlane,
    stream_mgr: Any,
    payload: dict[str, Any],
) -> None:
    run_id = payload.get("run_id") or f"wga_decomp_{uuid.uuid4().hex[:16]}"
    workspace_id = payload["workspace_id"]
    project_id = payload.get("project_id")
    weekly_plan_id = payload.get("weekly_plan_id")
    goal_text = (payload.get("goal_text") or "").strip()
    origin = payload.get("origin") or "command_center"
    origin_ref = payload.get("origin_ref")
    sub = str(payload.get("actor_id") or "0")

    if not goal_text or not project_id:
        logger.warning("goal_decomposition run=%s missing goal_text/project_id — skip", run_id)
        return

    async def _fail(code: str, attempt_run_id: str, *, user_message: str | None = None) -> None:
        await _report_decomposition_failure(
            plane,
            workspace_id=workspace_id,
            project_id=str(project_id),
            weekly_plan_id=weekly_plan_id,
            run_id=attempt_run_id,
            sub=sub,
            code=code,
            origin=origin,
            origin_ref=origin_ref,
            user_message=user_message,
        )

    catalog = _capability_catalog()
    prompt = build_decomposition_prompt(
        goal_text,
        {
            "lifecycle_stage": payload.get("lifecycle_stage") or "unknown",
            "existing_task_titles": list(payload.get("existing_task_titles") or []),
            "next_best_actions": list(payload.get("next_best_actions") or []),
            "capability_catalog": catalog,
            "goal_ancestry": payload.get("goal_ancestry"),
        },
    )

    items = None
    attempt_run_id = run_id
    last_schema_error: PlanSchemaError | None = None
    for attempt in range(_DECOMPOSITION_MAX_ATTEMPTS):
        attempt_run_id = run_id if attempt == 0 else f"{run_id}_retry{attempt}"
        attempt_prompt = (
            prompt
            if last_schema_error is None
            else _schema_retry_prompt(prompt, str(last_schema_error))
        )
        try:
            prep = await prepare_run(
                plane,
                run_id=attempt_run_id,
                local_spec=COSA_OPERATIONS_AGENT_SPEC,
                prompt=attempt_prompt,
                principal=f"system:wga:{workspace_id}",
                workspace_id=workspace_id,
                conversation_id=f"wga_decomp_{attempt_run_id}",
                policy_snapshot=None,
                project_id=str(project_id),
            )
        except RunCoreError as exc:
            logger.error(
                "goal_decomposition prep failed run=%s reason=%s", attempt_run_id, exc.reason_code
            )
            await _fail(f"prep_failed:{exc.reason_code}", attempt_run_id)
            return

        run_result, _ = await run_kernel(
            plane, prep, workspace_id=workspace_id, run_id=attempt_run_id
        )
        if run_result.status != RunStatus.COMPLETED:
            raw = run_result.errors[0] if run_result.errors else str(run_result.status)
            logger.error("goal_decomposition kernel run=%s failed: %s", attempt_run_id, raw)
            classified = classify_run_error(raw)
            await _fail(classified.code, attempt_run_id, user_message=classified.user_message)
            return

        try:
            items = validate_plan_capabilities(
                parse_plan_output(_extract_text(run_result)), catalog
            )
            break
        except PlanSchemaError as exc:
            logger.warning(
                "goal_decomposition plan_schema_invalid run=%s attempt=%d: %s",
                attempt_run_id,
                attempt + 1,
                exc,
            )
            last_schema_error = exc

    if items is None:
        await _fail("plan_schema_invalid", attempt_run_id)
        return

    token = mint_company_delegation(
        sub=sub,
        workspace_id=workspace_id,
        run_id=attempt_run_id,
        capability_ids=[_CAP_EXECUTION_PLAN_CREATE, _CAP_TASK_LIST],
    )
    body = {
        "projectId": project_id,
        "weeklyPlanId": weekly_plan_id,
        "goalText": goal_text,
        "origin": origin,
        "originRef": origin_ref,
        "runId": attempt_run_id,
        "items": [
            {
                "title": it.title,
                "decisionReason": it.decision_reason,
                "evidenceRefs": it.evidence_refs,
                "suggestedDomain": it.suggested_domain,
                "expectedCapability": it.expected_capability,
                "capabilityRisk": capability_risk(it.expected_capability),
                # tenant policy override do company đọc từ
                # operating.workspace_capability_policy khi classify (WGA #3) —
                # worker không cần lookup.
                "tenantPolicyDecision": None,
                "dependsOnTitles": it.depends_on_titles,
                "priority": it.priority,
                "doneCriteria": it.done_criteria,
            }
            for it in items
        ],
    }

    try:
        await plane.company_client.post(
            "/operations/execution-plans",
            json=body,
            headers={"X-Workspace-Id": workspace_id, "Authorization": f"Bearer {token}"},
        )
    except CompanyServiceError as exc:
        logger.error(
            "goal_decomposition POST execution-plans failed run=%s: %s", attempt_run_id, exc
        )
        await _fail("plan_create_failed", attempt_run_id)
        return

    logger.info(
        "goal_decomposition run=%s created plan with %d item(s) for ws=%s",
        attempt_run_id,
        len(items),
        workspace_id,
    )

    if origin == "chat" and origin_ref:
        await _post_chat_message(
            plane,
            workspace_id=workspace_id,
            conversation_id=origin_ref,
            project_id=str(project_id),
            run_id=attempt_run_id,
            message_kind="plan_created",
            content=(
                "Đã lập kế hoạch triển khai từ mục tiêu tuần. "
                "Mở Command Center để xem và duyệt cả lô."
            ),
        )


_DECOMPOSITION_MAX_ATTEMPTS = 2

_DECOMPOSITION_FAILED_MESSAGE_VI = (
    "Chưa lập được kế hoạch từ mục tiêu tuần (AI trả kết quả không hợp lệ). "
    "Vui lòng thử lại hoặc diễn đạt mục tiêu cụ thể hơn."
)


def _schema_retry_prompt(prompt: str, error: str) -> str:
    """Lượt thử lại duy nhất: đưa lỗi schema cụ thể cho model tự sửa."""
    return (
        f"{prompt}\n\nYOUR PREVIOUS OUTPUT WAS REJECTED: {error[:300]}\n"
        "Fix it and return ONLY the JSON object, no prose, no markdown fences."
    )


async def _post_chat_message(
    plane: CosaAgentPlane,
    *,
    workspace_id: str,
    conversation_id: str,
    project_id: str,
    run_id: str,
    content: str,
    message_kind: str,
) -> None:
    """Chèn 1 assistant message vào conversation gốc, rồi (SAU khi message đã
    persist) ghi Project Activity `agent.chat_message` để chat đang mở nhận qua
    SSE `/agent/projects/{id}/activity/stream` mà không cần tải lại."""
    try:
        stored = await plane.conversation_repository.add_message(
            MessageRecord(
                conversation_id=conversation_id,
                project_id=project_id,
                role="assistant",
                content=content,
                run_id=run_id,
                status="completed",
            )
        )
    except Exception as exc:
        logger.warning("wga chat message failed conv=%s: %s", conversation_id, exc)
        return
    await record_agent_chat_message_activity(
        plane,
        workspace_id=workspace_id,
        project_id=project_id,
        conversation_id=conversation_id,
        message=stored,
        run_id=run_id,
        message_kind=message_kind,
    )


async def record_agent_chat_message_activity(
    plane: Any,
    *,
    workspace_id: str,
    project_id: str | None,
    conversation_id: str,
    message: Any,
    run_id: str,
    message_kind: str,
) -> None:
    activity = getattr(plane, "project_activity_service", None)
    message_id = getattr(message, "message_id", None)
    if activity is None or not project_id or not isinstance(message_id, str):
        return
    try:
        await activity.record_runtime_event(
            workspace_id=workspace_id,
            project_id=project_id,
            kind="agent.chat_message",
            source_type="message",
            source_id=message_id,
            source_version=str(getattr(message, "sequence_no", None) or 0),
            actor_kind="agent",
            actor_id=run_id,
            correlation_id=run_id,
            raw_context={
                "message_id": message_id,
                "conversation_id": conversation_id,
                "message_kind": message_kind,
                "run_id": run_id,
            },
        )
    except Exception as exc:
        logger.warning("record agent.chat_message activity failed msg=%s: %s", message_id, exc)


async def _report_decomposition_failure(
    plane: CosaAgentPlane,
    *,
    workspace_id: str,
    project_id: str,
    weekly_plan_id: str | None,
    run_id: str,
    sub: str,
    code: str,
    origin: str,
    origin_ref: str | None,
    user_message: str | None = None,
) -> None:
    """G6 — lỗi phân rã phải nhìn thấy được: ghi trạng thái 'failed' có mã máy
    vào weekly plan (Command Center dừng chờ và hiện lỗi) và, nếu mục tiêu đến
    từ chat, nhắn lại vào đúng conversation. Chuỗi lỗi thô chỉ ở log."""
    if weekly_plan_id:
        token = mint_company_delegation(
            sub=sub,
            workspace_id=workspace_id,
            run_id=run_id,
            capability_ids=[_CAP_EXECUTION_PLAN_CREATE],
        )
        try:
            await plane.company_client.post(
                f"/operations/weekly-plans/{weekly_plan_id}/decomposition-failure",
                json={"runId": run_id, "errorCode": code[:80]},
                headers={"X-Workspace-Id": workspace_id, "Authorization": f"Bearer {token}"},
            )
        except CompanyServiceError as exc:
            logger.error(
                "goal_decomposition report failure wp=%s run=%s: %s", weekly_plan_id, run_id, exc
            )
    if origin == "chat" and origin_ref:
        await _post_chat_message(
            plane,
            workspace_id=workspace_id,
            conversation_id=origin_ref,
            project_id=project_id,
            run_id=run_id,
            content=user_message or _DECOMPOSITION_FAILED_MESSAGE_VI,
            message_kind="plan_failed",
        )


def _task_execution_prompt(t: dict[str, Any]) -> str:
    return (
        "Complete this operations work item. Use only the capabilities you are "
        "allowed. If it needs a side-effect outside your permissions, stop and "
        "explain what a human must do.\n\n"
        f"TITLE: {t.get('title', '')}\n"
        f"WHY: {t.get('decisionReason', '')}\n"
        f"EVIDENCE: {', '.join(t.get('evidenceRefs') or []) or '(none)'}\n"
    )


class _SweepProgress:
    """G9 — gom kết quả task theo plan trong 1 lượt sweep rồi báo 1 message có
    cấu trúc `{"kind": "plan_progress", ...}` vào conversation gốc của plan
    (origin=chat). FE render thẻ theo `kind`, không parse văn bản (quy tắc 7)."""

    _BUCKETS = ("done", "pending_review", "waiting_approval", "blocked")

    def __init__(self, workspace_id: str) -> None:
        self._workspace_id = workspace_id
        self._plans: dict[str, dict[str, Any]] = {}

    def record(self, t: dict[str, Any], outcome: str) -> None:
        if outcome not in self._BUCKETS:
            return
        if t.get("planOrigin") != "chat" or not t.get("planOriginRef"):
            return
        plan_id = str(t.get("planId") or "")
        if not plan_id:
            return
        entry = self._plans.setdefault(
            plan_id,
            {
                "conversation_id": str(t["planOriginRef"]),
                "project_id": str(t.get("projectId") or ""),
                "workspace_id": str(t.get("workspaceId") or self._workspace_id),
                **{b: [] for b in self._BUCKETS},
            },
        )
        entry[outcome].append(str(t.get("title") or t.get("taskId")))

    async def post_to_origin_chats(self, plane: CosaAgentPlane) -> None:
        for plan_id, entry in self._plans.items():
            content = json.dumps(
                {
                    "kind": "plan_progress",
                    "plan_id": plan_id,
                    **{b: entry[b] for b in self._BUCKETS},
                },
                ensure_ascii=False,
            )
            await _post_chat_message(
                plane,
                workspace_id=entry["workspace_id"],
                conversation_id=entry["conversation_id"],
                project_id=entry["project_id"],
                run_id=f"wga_progress_{plan_id}",
                content=content,
                message_kind="plan_progress",
            )


async def _execute_claimed_task(
    plane: CosaAgentPlane,
    t: dict[str, Any],
    *,
    workspace_id: str,
    sub: str,
    sweep_project_id: str | None,
) -> str:
    """Chạy 1 task claimable; trả kết quả: done | pending_review |
    waiting_approval | blocked | skipped (không claim được)."""
    task_id = str(t["taskId"])
    owner_profile = t.get("ownerAgentProfile") or "operations"
    spec = _SPEC_BY_PROFILE.get(owner_profile)
    # run_id mã hoá task_id để execute_resume_task khôi phục được task nào
    # cần advance(done) sau khi founder duyệt checkpoint (WGA #1).
    task_run_id = f"wga_task_{task_id}_{uuid.uuid4().hex[:8]}"

    caps = [_CAP_TASK_ADVANCE, _CAP_TASK_LIST]
    if t.get("expectedCapability"):
        caps.append(t["expectedCapability"])
    adv_token = mint_company_delegation(
        sub=sub, workspace_id=workspace_id, run_id=task_run_id, capability_ids=caps
    )

    if spec is None:
        # Fail-closed: không có spec tường minh cho profile này thì KHÔNG
        # được âm thầm chạy bằng Operations spec (đúng bug lịch sử đã sửa ở
        # handlers.py::_AGENT_PROFILE_SPECS — wga_run.py trước đây chưa áp
        # dụng cùng nguyên tắc).
        logger.error(
            "unsupported ownerAgentProfile %r for task=%s ws=%s, failing closed",
            owner_profile,
            task_id,
            workspace_id,
        )
        await _advance_task(
            plane,
            workspace_id=workspace_id,
            task_id=task_id,
            to_status="blocked",
            run_id=task_run_id,
            token=adv_token,
            note=f"unsupported_owner_agent_profile_{owner_profile}",
        )
        return "blocked"

    # G5 — agent được giao phải thật sự có capability của item; không thì
    # run chắc chắn thất bại hoặc agent tự làm việc khác. Fail closed.
    expected_cap = t.get("expectedCapability")
    if expected_cap and expected_cap not in spec.capability_refs:
        await _advance_task(
            plane,
            workspace_id=workspace_id,
            task_id=task_id,
            to_status="blocked",
            run_id=task_run_id,
            token=adv_token,
            note=f"capability_not_in_profile:{expected_cap}",
        )
        return "blocked"

    # Quy tắc 14 — run business phải có Project; task lệch Project của
    # sweep (hoặc thiếu Project) fail closed trước khi claim.
    task_project_id = str(t.get("projectId") or "") or None
    if not task_project_id or (sweep_project_id and task_project_id != sweep_project_id):
        await _advance_task(
            plane,
            workspace_id=workspace_id,
            task_id=task_id,
            to_status="blocked",
            run_id=task_run_id,
            token=adv_token,
            note="missing_project_scope" if not task_project_id else "project_scope_mismatch",
        )
        return "blocked"

    try:
        await plane.company_client.post(
            f"/operations/tasks/{task_id}/advance",
            json={"toStatus": "in_progress", "runId": task_run_id},
            headers={
                "X-Workspace-Id": workspace_id,
                "Authorization": f"Bearer {adv_token}",
            },
        )
    except CompanyServiceError as exc:
        logger.warning("sweep could not claim task=%s: %s", task_id, exc)
        return "skipped"

    needs_approval = t.get("autonomyClass") == "NEEDS_APPROVAL"
    extra_metadata: dict[str, Any] = {"execution_plan_item_id": t.get("planItemId")}
    if needs_approval and expected_cap:
        extra_metadata[REQUIRE_APPROVAL_CAPABILITIES_KEY] = [expected_cap]
    # Ngữ cảnh mục tiêu + tiêu chí hoàn thành đi qua metadata của run (không đổi AgentSpec).
    if t.get("goalAncestry"):
        extra_metadata["goal_ancestry"] = t["goalAncestry"]
    if t.get("doneCriteria"):
        extra_metadata["done_criteria"] = t["doneCriteria"]

    try:
        prep = await prepare_run(
            plane,
            run_id=task_run_id,
            local_spec=spec,
            prompt=_task_execution_prompt(t),
            principal=f"system:wga:{workspace_id}",
            workspace_id=workspace_id,
            conversation_id=f"wga_task_{task_run_id}",
            policy_snapshot=None,
            extra_metadata=extra_metadata,
            project_id=task_project_id,
        )
    except RunCoreError as exc:
        await _advance_task(
            plane,
            workspace_id=workspace_id,
            task_id=task_id,
            to_status="blocked",
            run_id=task_run_id,
            token=adv_token,
            note=f"prep_failed:{exc.reason_code}",
        )
        return "blocked"

    run_result, _ = await run_kernel(plane, prep, workspace_id=workspace_id, run_id=task_run_id)

    if run_result.status == RunStatus.COMPLETED:
        output_text = _extract_text(run_result)
        evidence = await record_wga_task_evidence(
            plane, workspace_id=workspace_id, run_id=task_run_id, output_text=output_text
        )
        # Xác minh doneCriteria (sau cờ WGA_VERIFY_ON_COMPLETE; đọc lúc gọi). Chỉ đường AUTO ban đầu:
        # đường resume sau duyệt và task NEEDS_APPROVAL giữ nguyên, không xác minh (quyết định có chủ đích).
        done_criteria = t.get("doneCriteria")
        verification: VerificationOutcome | None = None
        if verification_enabled() and done_criteria and not needs_approval:
            try:
                verification = await verify_task_result(
                    plane,
                    producer_spec=spec,
                    workspace_id=workspace_id,
                    project_id=task_project_id,
                    task_id=task_id,
                    task_run_id=task_run_id,
                    task_title=t.get("title") or "",
                    decision_reason=t.get("decisionReason") or "",
                    done_criteria=done_criteria,
                    run_result=run_result,
                    output_text=output_text,
                )
            except Exception as exc:  # hợp đồng: verify không ném; nếu vẫn ném thì fail-closed
                logger.exception("wga verification crashed task=%s run=%s", task_id, task_run_id)
                verification = VerificationOutcome(
                    Verdict.INCONCLUSIVE,
                    None,
                    f"verification_error:{exc.__class__.__name__}",
                    [],
                )
        # Token ủy quyền sống 600s; run + thẩm phán có thể làm nó hết hạn: cấp lại ngay trước advance.
        adv_token = mint_company_delegation(
            sub=sub, workspace_id=workspace_id, run_id=task_run_id, capability_ids=caps
        )
        # Lưu ý thiết kế: nếu MỌI tiêu chí đều không bắt buộc thì combine() = PASS và task tự đóng.
        if verification is not None and verification.verdict is not Verdict.PASS:
            # FAIL/INCONCLUSIVE: không bao giờ đóng 'done'; giữ in_progress để founder xem lại.
            await _advance_task(
                plane,
                workspace_id=workspace_id,
                task_id=task_id,
                to_status="in_progress",
                run_id=task_run_id,
                token=adv_token,
                note=f"verification_{verification.verdict.value.lower()}: {verification.summary[:300]}",
            )
            return "pending_review"
        if verification is not None and verification.report_id and evidence:
            evidence = [*evidence, f"verification:{verification.report_id}"]
        # NEEDS_APPROVAL mà run xong không qua checkpoint duyệt (agent không
        # gọi capability cần duyệt) -> không tự đóng; founder xác nhận.
        done = await finalize_wga_task_completion(
            plane,
            workspace_id=workspace_id,
            task_id=task_id,
            run_id=task_run_id,
            token=adv_token,
            evidence_refs=None if needs_approval else evidence,
            summary=output_text.strip()[:500] or None,
            note="completion_pending_founder_review" if needs_approval else "completion_pending",
        )
        return "done" if done else "pending_review"
    if run_result.status == RunStatus.WAITING_APPROVAL:
        # Kernel đã tạo bản ghi approval (hiện ở WaitingForYouWidget). Đặt
        # task 'waiting_approval'; founder duyệt -> decide_approval schedule
        # 1 task resume -> execute_resume_task advance(done) (WGA #1).
        await _advance_task(
            plane,
            workspace_id=workspace_id,
            task_id=task_id,
            to_status="waiting_approval",
            run_id=task_run_id,
            token=adv_token,
            note="chờ founder duyệt checkpoint",
        )
        return "waiting_approval"
    # Không gửi chuỗi lỗi thô (litellm/SDK) vào note hiển thị cho founder — chỉ mã.
    raw = run_result.errors[0] if run_result.errors else "run_failed"
    logger.warning("wga task=%s run=%s failed: %s", task_id, task_run_id, raw)
    await _advance_task(
        plane,
        workspace_id=workspace_id,
        task_id=task_id,
        to_status="blocked",
        run_id=task_run_id,
        token=adv_token,
        note=f"run_failed:{classify_run_error(raw).code}",
    )
    return "blocked"


async def execute_workspace_task_sweep_task(
    plane: CosaAgentPlane,
    stream_mgr: Any,
    payload: dict[str, Any],
) -> None:
    if os.environ.get("WGA_SWEEP_ENABLED", "true").lower() in ("0", "false", "no"):
        return

    run_id = payload.get("run_id") or f"wga_sweep_{uuid.uuid4().hex[:12]}"
    workspace_id = payload["workspace_id"]
    sub = str(payload.get("actor_id") or "0")
    depth = int(payload.get("sweep_depth") or 0)
    batch = int(os.environ.get("WGA_EXECUTOR_BATCH", "5"))
    # Project của plan vừa accept (event mang projectId). Có thì chỉ quét task
    # của Project đó; không có (sweep cũ) thì mỗi task tự mang projectId.
    sweep_project_id = str(payload.get("project_id") or "") or None

    if depth >= _MAX_SWEEP_DEPTH:
        logger.warning("sweep ws=%s hit max depth %d — stop", workspace_id, _MAX_SWEEP_DEPTH)
        return

    list_token = mint_company_delegation(
        sub=sub, workspace_id=workspace_id, run_id=run_id, capability_ids=[_CAP_TASK_LIST]
    )
    try:
        resp = await plane.company_client.get(
            "/operations/tasks/agent-claimable",
            params={
                "limit": batch,
                **({"projectId": sweep_project_id} if sweep_project_id else {}),
            },
            headers={"X-Workspace-Id": workspace_id, "Authorization": f"Bearer {list_token}"},
        )
    except CompanyServiceError as exc:
        logger.error("sweep list failed ws=%s: %s", workspace_id, exc)
        return

    # AUTO chạy thẳng; NEEDS_APPROVAL chạy với capability của item bị policy
    # siết thành REQUIRE_APPROVAL (G7) — agent dừng ở checkpoint chờ founder.
    claimable = [
        t for t in (resp.get("tasks") or []) if t.get("autonomyClass") in ("AUTO", "NEEDS_APPROVAL")
    ]
    if not claimable:
        return

    progress = _SweepProgress(workspace_id)
    for t in claimable:
        outcome = await _execute_claimed_task(
            plane, t, workspace_id=workspace_id, sub=sub, sweep_project_id=sweep_project_id
        )
        progress.record(t, outcome)
    await progress.post_to_origin_chats(plane)

    # Còn task chưa xử (batch đầy hoặc dependency mở khoá sau) → re-schedule.
    if len(claimable) >= batch:
        with contextlib.suppress(Exception):
            await plane.scheduler.schedule(
                target_spec_id="cosa.agents.operations",
                input_payload={
                    "task_type": "workspace_task_sweep",
                    "workspace_id": workspace_id,
                    "project_id": sweep_project_id,
                    "actor_id": sub,
                    "sweep_depth": depth + 1,
                    "delay_sec": int(os.environ.get("WGA_SWEEP_RESCHEDULE_DELAY_SEC", "15")),
                },
                coalescing_key=f"wga:sweep:{workspace_id}:{sweep_project_id or '*'}",
            )
