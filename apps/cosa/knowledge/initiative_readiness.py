"""Initiative knowledge readiness gate (Task 11, plan 2026-09-28-stage-
adaptive-ai-operating-system).

`assert_initiative_knowledge_allowed(snapshot, request)` intersects the
Initiative's current promotion snapshot (Task 6 —
`apps.cosa.models.ai_initiative_snapshot.AiInitiativePromotionSnapshot`,
carrying `data_readiness_status`/`retrieval_mode` from the Company-side
`AiDataReadinessAssessment`) with the retrieval mode a caller is requesting,
and denies anything the assessment does not cover:

- `NOT_READY` or a missing assessment denies both lexical and semantic.
- `CONDITIONAL`/`READY` permit only the declared `retrieval_mode` or lower —
  a human being able to see the data elsewhere never raises this ceiling
  (spec §10.1: "CONDITIONAL... never permits a higher-risk write action
  merely because a human can see the data elsewhere").
- `semantic` is additionally gated by `semantic_retrieval_wired()` even when
  the assessment says READY+semantic — Task 12's production embedding
  provider selection is a separately ADR-approved gate, not something this
  module (or any assessment) can silently enable.

This module does not call Company or query a database — it is a pure
function over the snapshot COSA already holds (delivered once, at
promotion time, and re-fetched from the durable store per run — see
Task 6/8) and the caller's own request.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

__all__ = [
    "KnowledgeReadinessDecision",
    "assert_initiative_knowledge_allowed",
    "semantic_retrieval_wired",
]

_RETRIEVAL_RANK: dict[str, int] = {"none": 0, "lexical": 1, "semantic": 2}


class KnowledgeReadinessDecision(BaseModel):
    allowed: bool
    code: str
    details: str | None = None
    effective_retrieval_mode: str | None = None


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def semantic_retrieval_wired() -> bool:
    """Task 12 gate: whether a production embedding provider is actually
    instantiated and wired into this deployment.

    Currently always `False`: `apps/cosa/composition/agent_plane.py` never
    constructs an `EmbeddingProvider` (grep confirms zero references outside
    `packages/agent/knowledge/`), and `HashingEmbeddingProvider` is an
    explicit dev/test placeholder (see its own docstring), not a production
    provider. Do not flip this to `True` without Task 12's separate
    ADR-approved provider/residency/evaluation decision — see plan §14
    Phase E and the design's §10.2 knowledge enablement order.
    """
    return False


def assert_initiative_knowledge_allowed(
    snapshot: Any,
    request: Any,
) -> KnowledgeReadinessDecision:
    """`snapshot` is normally an `AiInitiativePromotionSnapshot` (or `None`
    when no promotion snapshot exists for the Initiative yet). `request` is
    any object/dict exposing an optional `retrieval_mode` field — defaults to
    `"lexical"` when absent, matching the assessment's own default retrieval
    posture (spec §10.1: `retrieval_mode` never defaults to `"semantic"`)."""
    if snapshot is None:
        return KnowledgeReadinessDecision(
            allowed=False,
            code="initiative_snapshot_not_found",
            details="No current promotion snapshot for this Initiative; knowledge access denied",
        )

    lifecycle_state = _get_val(snapshot, "lifecycle_state")
    if lifecycle_state in ("PAUSED", "RETIRED"):
        return KnowledgeReadinessDecision(
            allowed=False,
            code=f"initiative_lifecycle_{str(lifecycle_state).lower()}",
            details=f"Initiative is {lifecycle_state}; knowledge access blocked",
        )

    assessment_status = _get_val(snapshot, "data_readiness_status")
    declared_mode = _get_val(snapshot, "retrieval_mode") or "none"
    requested_mode = _get_val(request, "retrieval_mode") or "lexical"

    if assessment_status is None:
        return KnowledgeReadinessDecision(
            allowed=False,
            code="data_readiness_assessment_required",
            details="Initiative has no data readiness assessment on file",
        )

    if assessment_status == "NOT_READY":
        return KnowledgeReadinessDecision(
            allowed=False,
            code="data_readiness_not_ready",
            details="Data readiness assessment is NOT_READY",
        )

    if requested_mode not in _RETRIEVAL_RANK:
        return KnowledgeReadinessDecision(
            allowed=False,
            code="retrieval_mode_invalid",
            details=f"Unknown retrieval mode: {requested_mode}",
        )

    if _RETRIEVAL_RANK[requested_mode] > _RETRIEVAL_RANK.get(declared_mode, 0):
        return KnowledgeReadinessDecision(
            allowed=False,
            code="retrieval_mode_exceeds_assessment",
            details=(
                f"Requested retrieval_mode={requested_mode} exceeds assessed "
                f"retrieval_mode={declared_mode} (status={assessment_status})"
            ),
        )

    if requested_mode == "semantic" and not semantic_retrieval_wired():
        return KnowledgeReadinessDecision(
            allowed=False,
            code="semantic_retrieval_not_ready",
            details="Semantic retrieval has no production embedding provider wired (Task 12)",
        )

    return KnowledgeReadinessDecision(
        allowed=True,
        code="allowed",
        effective_retrieval_mode=requested_mode,
    )
