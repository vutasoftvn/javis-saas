from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

from agent.runs.models import ApprovalSubject
from agent.runs.stream_events import RunStreamEventRecord
from agent.skills.candidate_store import InMemorySkillCandidateStore, SkillCandidateStore
from agent.skills.contracts import SkillCandidate, SkillStatus
from pydantic import BaseModel

from apps.cosa.composition.agent_plane import CosaAgentPlane

logger = logging.getLogger("cosa.worker.approval_actions")

__all__ = [
    "ApprovalActionResult",
    "execute_skill_candidate_promotion",
    "relay_approved_actions",
]


class ApprovalActionResult(BaseModel):
    success: bool
    reason_code: str | None = None
    candidate: SkillCandidate | None = None


async def _record_action_event(
    plane: CosaAgentPlane,
    workspace_id: str,
    approval_id: str,
    candidate: SkillCandidate | None,
    event_type: str,
    reason_code: str | None,
) -> None:
    stream_repo = getattr(plane, "stream_event_repository", None)
    if stream_repo is None:
        return
    body: dict[str, Any] = {
        "approval_id": approval_id,
        "action": "promote_skill_candidate",
        "subject_kind": "skill_candidate",
        "subject_ref": candidate.candidate_id if candidate else None,
        "status": "completed" if event_type == "approval.action.completed" else "rejected",
    }
    if reason_code:
        body["reason_code"] = reason_code

    run_id = candidate.parent_run_id if candidate else approval_id
    record = RunStreamEventRecord(
        run_id=run_id,
        event_type=event_type,
        payload=body,
        conversation_id=f"conv_{approval_id}",
        workspace_id=workspace_id,
    )
    with contextlib.suppress(Exception):
        await stream_repo.append(record)


async def relay_approved_actions(
    plane: CosaAgentPlane,
    worker_id: str,
    limit: int = 10,
) -> list[str]:
    """Claim pending/due approval action outbox records and schedule worker tasks."""
    repo = getattr(plane, "run_repository", None) or getattr(plane, "repository", None)
    if repo is None or not hasattr(repo, "claim_approval_actions"):
        return []

    now = datetime.now(UTC)
    claimed = await repo.claim_approval_actions(
        limit=limit,
        worker_id=worker_id,
        now=now,
    )
    scheduled_ids: list[str] = []
    for outbox in claimed:
        payload = {
            "task_type": "approval_action",
            "approval_id": outbox.approval_id,
            "workspace_id": outbox.workspace_id,
            "action": outbox.action,
            "subject_kind": outbox.subject_kind,
            "subject_ref": outbox.subject_ref,
            "subject_hash": outbox.subject_hash,
        }
        coalescing_key = f"approval-action:{outbox.approval_id}"
        await plane.scheduler.schedule(
            target_spec_id="approval_action_handler",
            target_spec_kind="approval_action",
            input_payload=payload,
            coalescing_key=coalescing_key,
        )
        await repo.mark_approval_action_delivered(
            approval_id=outbox.approval_id,
            worker_id=worker_id,
        )
        scheduled_ids.append(outbox.approval_id)
    return scheduled_ids


async def execute_skill_candidate_promotion(
    plane: CosaAgentPlane,
    payload: dict[str, Any],
) -> ApprovalActionResult:
    """Execute durable skill promotion after Founder approval."""
    action = payload.get("action")
    subject_kind = payload.get("subject_kind")
    if action != "promote_skill_candidate" or subject_kind != "skill_candidate":
        return ApprovalActionResult(
            success=False,
            reason_code="UNSUPPORTED_APPROVAL_ACTION",
        )

    workspace_id = payload.get("workspace_id")
    approval_id = payload.get("approval_id")
    candidate_id = payload.get("subject_ref")
    expected_hash = payload.get("subject_hash")

    if not workspace_id or not approval_id or not candidate_id or not expected_hash:
        return ApprovalActionResult(
            success=False,
            reason_code="INVALID_PAYLOAD",
        )

    cand_store: SkillCandidateStore | None = getattr(plane, "skill_candidate_store", None)
    if cand_store is None:
        cand_store = InMemorySkillCandidateStore()
        plane.skill_candidate_store = cand_store

    cand = await cand_store.get_candidate(workspace_id, candidate_id)
    if cand is None:
        await _record_action_event(
            plane,
            workspace_id,
            approval_id,
            None,
            "approval.action.rejected",
            "CANDIDATE_NOT_FOUND",
        )
        return ApprovalActionResult(
            success=False,
            reason_code="CANDIDATE_NOT_FOUND",
        )

    # Idempotent replay: already published with same approval and hash
    if cand.status == SkillStatus.PUBLISHED:
        if cand.promotion_approval_id == approval_id and expected_hash in (
            cand.promotion_definition_hash,
            cand.definition_hash,
        ):
            await _record_action_event(
                plane, workspace_id, approval_id, cand, "approval.action.completed", None
            )
            return ApprovalActionResult(
                success=True,
                reason_code="ALREADY_PUBLISHED",
                candidate=cand,
            )
        else:
            await _record_action_event(
                plane,
                workspace_id,
                approval_id,
                cand,
                "approval.action.rejected",
                "ALREADY_PUBLISHED_DIFFERENT_APPROVAL",
            )
            return ApprovalActionResult(
                success=False,
                reason_code="ALREADY_PUBLISHED_DIFFERENT_APPROVAL",
                candidate=cand,
            )

    # Recompute candidate definition hash
    computed_hash = f"sha256:{cand.proposed_skill.compute_hash()}"
    if computed_hash != expected_hash:
        await _record_action_event(
            plane,
            workspace_id,
            approval_id,
            cand,
            "approval.action.rejected",
            "APPROVAL_SUBJECT_STALE",
        )
        return ApprovalActionResult(
            success=False,
            reason_code="APPROVAL_SUBJECT_STALE",
            candidate=cand,
        )

    # Call approval_service.verify_change_execution
    subject = ApprovalSubject(
        kind=subject_kind,
        ref=candidate_id,
        definition_hash=expected_hash,
    )
    verify_res = await plane.approval_service.verify_change_execution(
        approval_id=approval_id,
        workspace_id=workspace_id,
        action=action,
        subject=subject,
    )
    if not verify_res.can_execute:
        await _record_action_event(
            plane,
            workspace_id,
            approval_id,
            cand,
            "approval.action.rejected",
            verify_res.reason_code,
        )
        return ApprovalActionResult(
            success=False,
            reason_code=verify_res.reason_code,
            candidate=cand,
        )

    # Validate candidate status and eval score
    if cand.status != SkillStatus.EVALUATED:
        await _record_action_event(
            plane,
            workspace_id,
            approval_id,
            cand,
            "approval.action.rejected",
            "CANDIDATE_NOT_EVALUATED",
        )
        return ApprovalActionResult(
            success=False,
            reason_code="CANDIDATE_NOT_EVALUATED",
            candidate=cand,
        )

    if cand.eval_score < 0.7:
        await _record_action_event(
            plane,
            workspace_id,
            approval_id,
            cand,
            "approval.action.rejected",
            "EVAL_SCORE_BELOW_THRESHOLD",
        )
        return ApprovalActionResult(
            success=False,
            reason_code="EVAL_SCORE_BELOW_THRESHOLD",
            candidate=cand,
        )

    # Validate required capabilities exist in registry
    if plane.capability_registry is not None:
        available_caps = {spec.id for spec in plane.capability_registry.list_specs()}
        unknown_caps = [
            cap for cap in cand.proposed_skill.required_capabilities if cap not in available_caps
        ]
        if unknown_caps:
            await _record_action_event(
                plane,
                workspace_id,
                approval_id,
                cand,
                "approval.action.rejected",
                "UNKNOWN_CAPABILITIES",
            )
            return ApprovalActionResult(
                success=False,
                reason_code="UNKNOWN_CAPABILITIES",
                candidate=cand,
            )

    # Publish via CAS
    ok, reason, published_cand = await cand_store.publish_candidate_if_approved(
        workspace_id=workspace_id,
        candidate_id=candidate_id,
        approval_id=approval_id,
        expected_definition_hash=expected_hash,
    )
    if not ok:
        await _record_action_event(
            plane,
            workspace_id,
            approval_id,
            cand,
            "approval.action.rejected",
            reason,
        )
        return ApprovalActionResult(
            success=False,
            reason_code=reason,
            candidate=published_cand or cand,
        )

    await _record_action_event(
        plane,
        workspace_id,
        approval_id,
        published_cand,
        "approval.action.completed",
        None,
    )
    return ApprovalActionResult(
        success=True,
        reason_code=reason,
        candidate=published_cand,
    )
