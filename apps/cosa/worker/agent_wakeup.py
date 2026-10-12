"""Handler wakeup (Dự án C): chạy một run CHỈ ĐỌC cho assignment được đánh thức."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from agent.runs.models import RunStatus
from agent.workforce.wakeup import build_wake_prompt, wakeup_enabled

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.policies.evaluator import READ_ONLY_RUN_KEY
from apps.cosa.worker.run_core import RunCoreError, prepare_run, run_kernel
from apps.cosa.worker.wakeup_service import WakeupService, evaluate_wake_target

logger = logging.getLogger(__name__)

__all__ = ["execute_agent_wakeup_task"]


async def execute_agent_wakeup_task(plane: Any, stream_mgr: Any, payload: dict[str, Any]) -> None:
    if not wakeup_enabled():
        return
    ledger = getattr(plane, "wakeup_ledger_repository", None)
    repo = getattr(plane, "workforce_repository", None)
    if ledger is None or repo is None:
        logger.error("agent_wakeup: ledger/workforce repository not configured")
        return

    workspace_id = str(payload.get("workspace_id") or "")
    assignment_id = str(payload.get("assignment_id") or "")
    project_id = str(payload.get("project_id") or "")
    if not (workspace_id and assignment_id and project_id):
        logger.warning(
            "agent_wakeup payload missing workspace_id/assignment_id/project_id: keys=%s",
            sorted(payload),
        )
        return

    entries = await ledger.list_unhandled(workspace_id, assignment_id, project_id)
    if not entries:
        return
    wake_ids = [e.wake_id for e in entries]
    hop = max(e.hop for e in entries)

    profile, reason = await evaluate_wake_target(repo, workspace_id, assignment_id)
    if profile is None:
        logger.info(
            "agent_wakeup skipped ws=%s assignment=%s: %s", workspace_id, assignment_id, reason
        )
        await ledger.mark_handled(workspace_id, wake_ids)
        return

    run_id = f"wake_{assignment_id.replace('-', '')[:8]}_{uuid.uuid4().hex[:8]}"
    failure: str | None = None
    try:
        prep = await prepare_run(
            plane,
            run_id=run_id,
            local_spec=AGENT_PROFILE_SPECS[profile],
            prompt=build_wake_prompt([(e.reason_kind, e.source_ref) for e in entries]),
            principal=f"system:wake:{workspace_id}",
            workspace_id=workspace_id,
            conversation_id=f"wake_{run_id}",
            policy_snapshot=None,
            extra_metadata={READ_ONLY_RUN_KEY: True},
            project_id=project_id,
        )
        result, _ = await run_kernel(plane, prep, workspace_id=workspace_id, run_id=run_id)
        if result.status != RunStatus.COMPLETED:
            failure = f"run_status_{result.status}"
    except RunCoreError as exc:
        failure = f"run_core_error:{getattr(exc, 'reason_code', None) or exc.__class__.__name__}"
    except Exception as exc:
        logger.exception("agent_wakeup run failed ws=%s assignment=%s", workspace_id, assignment_id)
        failure = f"run_error:{exc.__class__.__name__}"

    await ledger.mark_handled(workspace_id, wake_ids)
    if failure is None:
        logger.info(
            "agent_wakeup completed ws=%s assignment=%s run=%s", workspace_id, assignment_id, run_id
        )
        return
    try:
        service = WakeupService(workforce_repo=repo, ledger=ledger, scheduler=plane.scheduler)
        outcome = await service.escalate(
            workspace_id=workspace_id,
            from_assignment_id=assignment_id,
            project_id=project_id,
            reason_kind="wake_failed",
            source_ref=f"run:{run_id}",
            hop=hop,
        )
        logger.warning(
            "agent_wakeup failed (%s) ws=%s assignment=%s -> %s",
            failure,
            workspace_id,
            assignment_id,
            outcome.status,
        )
    except Exception:
        logger.exception(
            "agent_wakeup escalate failed ws=%s assignment=%s", workspace_id, assignment_id
        )
