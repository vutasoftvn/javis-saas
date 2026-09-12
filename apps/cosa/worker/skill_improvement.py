from __future__ import annotations

import contextlib
import logging
from datetime import datetime, timezone
from typing import Any

from agent.skills.improvement_repository import (
    ImprovementOutcome,
    SkillImprovementRepository,
)
from apps.cosa.composition.agent_plane import CosaAgentPlane

logger = logging.getLogger("cosa.worker.skill_improvement")

__all__ = [
    "execute_skill_improvement_task",
    "relay_skill_improvement_outbox",
]


async def relay_skill_improvement_outbox(
    plane: CosaAgentPlane,
    worker_id: str,
    limit: int = 10,
) -> list[str]:
    """Claim pending/due skill improvement outbox records and schedule worker tasks."""
    repo: SkillImprovementRepository | None = getattr(
        plane, "skill_improvement_repository", None
    )
    if repo is None or not hasattr(repo, "claim_improvement_outbox"):
        return []

    now = datetime.now(timezone.utc)
    claimed = await repo.claim_improvement_outbox(
        worker_id=worker_id,
        limit=limit,
        now=now,
    )
    scheduled_ids: list[str] = []
    for item in claimed:
        outbox = item.outbox
        payload = {
            "task_type": "skill_improvement",
            "request_id": outbox.request_id,
            "workspace_id": outbox.workspace_id,
        }
        coalescing_key = f"skill-improvement:{outbox.request_id}"
        try:
            await plane.scheduler.schedule(
                target_spec_id="skill_improvement_handler",
                target_spec_kind="skill_improvement",
                input_payload=payload,
                coalescing_key=coalescing_key,
            )
            await repo.mark_outbox_delivered(
                outbox_id=outbox.outbox_id,
                claim_token=item.claim_token,
                delivered_at=datetime.now(timezone.utc),
            )
            scheduled_ids.append(outbox.request_id)
        except Exception as exc:
            logger.warning(
                "worker=%s failed to schedule/deliver outbox_id=%s request_id=%s: %s",
                worker_id,
                outbox.outbox_id,
                outbox.request_id,
                exc,
            )
            if hasattr(repo, "mark_outbox_failed"):
                with contextlib.suppress(Exception):
                    await repo.mark_outbox_failed(
                        outbox_id=outbox.outbox_id,
                        claim_token=item.claim_token,
                        error=str(exc),
                    )
    return scheduled_ids


async def execute_skill_improvement_task(
    plane: CosaAgentPlane,
    payload: dict[str, Any],
    *,
    worker_id: str | None = None,
) -> ImprovementOutcome:
    """Execute durable, runless skill improvement task under scheduler and repository claim fencing."""
    task_type = payload.get("task_type")
    request_id = payload.get("request_id")
    workspace_id = payload.get("workspace_id")

    if task_type != "skill_improvement" or not request_id or not workspace_id:
        return ImprovementOutcome(
            status="FAILED_REQUIRES_ATTENTION",
            safe_reason_code="INVALID_PAYLOAD",
        )

    repo: SkillImprovementRepository | None = getattr(
        plane, "skill_improvement_repository", None
    )
    if repo is None:
        return ImprovementOutcome(
            status="FAILED_REQUIRES_ATTENTION",
            safe_reason_code="MISSING_REPOSITORY",
        )

    # 1. Fetch request to verify existence
    req = await repo.get_improvement_request(request_id)
    if req is None:
        return ImprovementOutcome(
            status="STALE",
            safe_reason_code="REQUEST_NOT_FOUND",
        )

    if req.status not in ("PENDING", "RUNNING"):
        return ImprovementOutcome(
            status="STALE",
            safe_reason_code="REQUEST_ALREADY_FINISHED",
        )

    # 2. Claim request with repository claim fence
    now = datetime.now(timezone.utc)
    w_id = worker_id or "skill_improvement_worker"
    claimed = await repo.claim_improvement_request(
        request_id=request_id,
        worker_id=w_id,
        now=now,
    )
    if claimed is None:
        return ImprovementOutcome(
            status="STALE",
            safe_reason_code="STALE_CLAIM",
        )

    # 3. Check current source spec identity in spec_registry
    if plane.spec_registry is not None:
        source_rec = await plane.spec_registry.get("skill", req.skill_id, req.skill_version)
        if source_rec is None or source_rec.definition_hash != req.definition_hash:
            stale_outcome = ImprovementOutcome(
                status="STALE",
                safe_reason_code="CHANGED_SOURCE_IDENTITY",
            )
            await repo.finish_improvement_request(
                request_id=request_id,
                claim_token=claimed.claim_token,
                outcome=stale_outcome,
            )
            return stale_outcome

    # 4. Check improvement service
    service = getattr(plane, "skill_improvement_service", None)
    if service is None:
        fail_outcome = ImprovementOutcome(
            status="FAILED_REQUIRES_ATTENTION",
            safe_reason_code="MISSING_IMPROVEMENT_SERVICE",
        )
        await repo.finish_improvement_request(
            request_id=request_id,
            claim_token=claimed.claim_token,
            outcome=fail_outcome,
        )
        return fail_outcome

    # 5. Execute bounded optimization
    outcome = await service.execute(claimed.request)

    # 6. Finish improvement request under claim fence
    finished = await repo.finish_improvement_request(
        request_id=request_id,
        claim_token=claimed.claim_token,
        outcome=outcome,
    )
    if not finished:
        return ImprovementOutcome(
            status="STALE",
            safe_reason_code="CLAIM_FENCE_LOST",
        )

    return outcome
