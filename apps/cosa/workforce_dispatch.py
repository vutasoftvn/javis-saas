"""Helper cho router: resolve Outcome Analysis binding và schedule run
(Task 4A). Tách khỏi router.py để test độc lập không cần đầy đủ intake deps.
"""

from __future__ import annotations

from typing import Any

from agent.workforce.outcome_analysis import resolve_outcome_analysis_binding

_ANALYSIS_KIND = "TASK_OUTCOME"


async def resolve_and_schedule_outcome_analysis(deps: Any, env: Any) -> tuple[str, str | None]:
    """Trả về (inbox_outcome, scheduled_task_id).

    - `accepted` + task_id: đã schedule run outcome_analysis.
    - `ignored_manual`: policy MANUAL, không tạo request tự động.
    - `blocked_configuration`: không có binding / binding lệch skill — request
      cần founder cấu hình lại (fail closed, KHÔNG chọn employee generic).
    """
    payload = getattr(env, "payload", {}) or {}
    workspace_id = str(getattr(env, "workspaceId", "") or payload.get("workspaceId", ""))
    task_result_id = str(payload.get("taskResultId") or "")

    repo = getattr(deps, "workforce_repository", None)
    if repo is None:
        return "blocked_configuration", None

    binding = await resolve_outcome_analysis_binding(
        repo, workspace_id, task_result_id, _ANALYSIS_KIND
    )
    if binding is None:
        return "blocked_configuration", None
    if binding.policy == "MANUAL":
        return "ignored_manual", None

    run_id = f"run_{env.eventId[:16]}" if getattr(env, "eventId", None) else None
    task_id = await deps.execution_plane.schedule_platform_task(
        target_spec_id=binding.skill_id,
        task_type="outcome_analysis",
        input_payload={
            "run_id": run_id,
            "workspace_id": workspace_id,
            "request_id": str(payload.get("requestId") or task_result_id),
            "task_result_id": task_result_id,
            "contract_id": str(payload.get("contractId") or ""),
            "agent_instance_id": binding.agent_instance_id,
            "assignment_id": binding.assignment_id,
            "skill_id": binding.skill_id,
            "skill_version": binding.skill_version,
            "definition_hash": binding.definition_hash,
            "agent_profile": "outcome_analysis",
        },
        coalescing_key=f"analysis:{workspace_id}:{task_result_id}",
    )
    return "accepted", task_id
