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
import logging
import os
import uuid
from typing import Any

from agent.contracts.run import RunStatus
from agent.conversations.models import MessageRecord

from apps.cosa.agents.capability_risk_map import capability_risk
from apps.cosa.agents.goal_decomposition import (
    PlanSchemaError,
    build_decomposition_prompt,
    parse_plan_output,
)
from apps.cosa.agents.specs import (
    COSA_FINANCE_AGENT_SPEC,
    COSA_MARKETING_AGENT_SPEC,
    COSA_OPERATIONS_AGENT_SPEC,
)
from apps.cosa.auth.jwt import mint_company_delegation
from apps.cosa.capabilities.client import CompanyServiceError
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.worker.run_core import RunCoreError, prepare_run, run_kernel

logger = logging.getLogger(__name__)

__all__ = [
    "execute_goal_decomposition_task",
    "execute_workspace_task_sweep_task",
]

_SPEC_BY_PROFILE = {
    "operations": COSA_OPERATIONS_AGENT_SPEC,
    "finance": COSA_FINANCE_AGENT_SPEC,
    "marketing": COSA_MARKETING_AGENT_SPEC,
}

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
) -> None:
    body: dict[str, Any] = {"toStatus": to_status, "runId": run_id}
    if note:
        body["note"] = note[:500]
    with contextlib.suppress(CompanyServiceError):
        await plane.company_client.post(
            f"/operations/tasks/{task_id}/advance",
            json=body,
            headers={"X-Workspace-Id": workspace_id, "Authorization": f"Bearer {token}"},
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

    prompt = build_decomposition_prompt(
        goal_text, {"lifecycle_stage": payload.get("lifecycle_stage") or "unknown"}
    )

    try:
        prep = await prepare_run(
            plane,
            run_id=run_id,
            local_spec=COSA_OPERATIONS_AGENT_SPEC,
            prompt=prompt,
            principal=f"system:wga:{workspace_id}",
            workspace_id=workspace_id,
            conversation_id=f"wga_decomp_{run_id}",
            policy_snapshot=None,
        )
    except RunCoreError as exc:
        logger.error("goal_decomposition prep failed run=%s reason=%s", run_id, exc.reason_code)
        return

    run_result, _ = await run_kernel(plane, prep, workspace_id=workspace_id, run_id=run_id)
    if run_result.status != RunStatus.COMPLETED:
        logger.error("goal_decomposition kernel run=%s status=%s", run_id, run_result.status)
        return

    try:
        items = parse_plan_output(_extract_text(run_result))
    except PlanSchemaError as exc:
        logger.error("goal_decomposition plan_schema_invalid run=%s: %s", run_id, exc)
        return

    token = mint_company_delegation(
        sub=sub,
        workspace_id=workspace_id,
        run_id=run_id,
        capability_ids=[_CAP_EXECUTION_PLAN_CREATE, _CAP_TASK_LIST],
    )
    body = {
        "projectId": project_id,
        "weeklyPlanId": weekly_plan_id,
        "goalText": goal_text,
        "origin": origin,
        "originRef": origin_ref,
        "runId": run_id,
        "items": [
            {
                "title": it.title,
                "decisionReason": it.decision_reason,
                "evidenceRefs": it.evidence_refs,
                "suggestedDomain": it.suggested_domain,
                "expectedCapability": it.expected_capability,
                "capabilityRisk": capability_risk(it.expected_capability),
                # v1: chưa lookup per-workspace tenant policy — classifier phía
                # company vẫn áp FORBIDDEN_RE + risk default (an toàn).
                "tenantPolicyDecision": None,
                "dependsOnTitles": it.depends_on_titles,
                "priority": it.priority,
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
        logger.error("goal_decomposition POST execution-plans failed run=%s: %s", run_id, exc)
        return

    logger.info(
        "goal_decomposition run=%s created plan with %d item(s) for ws=%s",
        run_id,
        len(items),
        workspace_id,
    )

    if origin == "chat" and origin_ref:
        with contextlib.suppress(Exception):
            await plane.conversation_repository.add_message(
                MessageRecord(
                    conversation_id=origin_ref,
                    role="assistant",
                    content=(
                        "Đã lập kế hoạch triển khai từ mục tiêu tuần. "
                        "Mở Command Center để xem và duyệt cả lô."
                    ),
                    run_id=run_id,
                    status="completed",
                )
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

    if depth >= _MAX_SWEEP_DEPTH:
        logger.warning("sweep ws=%s hit max depth %d — stop", workspace_id, _MAX_SWEEP_DEPTH)
        return

    list_token = mint_company_delegation(
        sub=sub, workspace_id=workspace_id, run_id=run_id, capability_ids=[_CAP_TASK_LIST]
    )
    try:
        resp = await plane.company_client.get(
            "/operations/tasks/agent-claimable",
            params={"limit": batch},
            headers={"X-Workspace-Id": workspace_id, "Authorization": f"Bearer {list_token}"},
        )
    except CompanyServiceError as exc:
        logger.error("sweep list failed ws=%s: %s", workspace_id, exc)
        return

    claimable = [t for t in (resp.get("tasks") or []) if t.get("autonomyClass") == "AUTO"]
    if not claimable:
        return

    for t in claimable:
        task_id = str(t["taskId"])
        owner_profile = t.get("ownerAgentProfile") or "operations"
        spec = _SPEC_BY_PROFILE.get(owner_profile, COSA_OPERATIONS_AGENT_SPEC)
        task_run_id = f"{run_id}_{task_id}"

        caps = [_CAP_TASK_ADVANCE, _CAP_TASK_LIST]
        if t.get("expectedCapability"):
            caps.append(t["expectedCapability"])
        adv_token = mint_company_delegation(
            sub=sub, workspace_id=workspace_id, run_id=task_run_id, capability_ids=caps
        )

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
            continue

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
                extra_metadata={"execution_plan_item_id": t.get("planItemId")},
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
            continue

        run_result, _ = await run_kernel(plane, prep, workspace_id=workspace_id, run_id=task_run_id)

        if run_result.status == RunStatus.COMPLETED:
            await _advance_task(
                plane,
                workspace_id=workspace_id,
                task_id=task_id,
                to_status="done",
                run_id=task_run_id,
                token=adv_token,
            )
        elif run_result.status == RunStatus.WAITING_APPROVAL:
            # v1: đường approval-resume cho headless task chưa wire — đánh dấu
            # blocked để founder thấy ở "Việc của bạn" thay vì kẹt in_progress.
            await _advance_task(
                plane,
                workspace_id=workspace_id,
                task_id=task_id,
                to_status="blocked",
                run_id=task_run_id,
                token=adv_token,
                note="cần phê duyệt — luồng resume cho task nền chưa hỗ trợ (v1)",
            )
        else:
            note = run_result.errors[0] if run_result.errors else "run_failed"
            await _advance_task(
                plane,
                workspace_id=workspace_id,
                task_id=task_id,
                to_status="blocked",
                run_id=task_run_id,
                token=adv_token,
                note=note,
            )

    # Còn task chưa xử (batch đầy hoặc dependency mở khoá sau) → re-schedule.
    if len(claimable) >= batch:
        with contextlib.suppress(Exception):
            await plane.scheduler.schedule(
                target_spec_id="cosa.agents.operations",
                input_payload={
                    "task_type": "workspace_task_sweep",
                    "workspace_id": workspace_id,
                    "actor_id": sub,
                    "sweep_depth": depth + 1,
                    "delay_sec": int(os.environ.get("WGA_SWEEP_RESCHEDULE_DELAY_SEC", "15")),
                },
                coalescing_key=f"wga:sweep:{workspace_id}",
            )
