"""Internal (service-to-service) AI Initiative promotion snapshot route for Company Plane (Task 6).

Company publishes a promotion snapshot to this endpoint when an AI Initiative
transitions lifecycle stages (DISCOVER -> PILOT -> VALIDATE -> SCALE_CANDIDATE -> SCALED).

Auth: header `X-Cosa-Service-Token` matching `COSA_SERVICE_TOKEN` or `COSA_INTERNAL_SERVICE_TOKEN`.
Fail closed on foreign project, invalid/drifted hash, or missing credentials.
Idempotent: duplicate snapshot delivery with identical decision_id returns 200 without side effects,
and survives process restart via the Postgres-backed
`apps.cosa.models.ai_initiative_snapshot.AiInitiativePromotionSnapshotStore` (see
`CosaAgentPlane.ai_initiative_snapshot_store`) — an in-memory dict here would forget
consumed snapshots on restart and break both idempotent retry and Task 8's
`assert_initiative_run_allowed()`, which reads the current snapshot at run time.

`decision_hash` binds `decision_id:revision:lifecycle_state:workspace_id:project_id`
(see `services/company/operations/services/ai-initiative-cosa.client.ts:computeDecisionHash`,
which Company uses to compute it). Recomputing and comparing it here is the actual
scope/tamper check — a resubmitted decision with a swapped project_id or workspace_id
fails hash verification because those fields are part of the signed input, not because
of any string heuristic on the field's content.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.cosa.models.ai_initiative_snapshot import AiInitiativePromotionSnapshot

router = APIRouter(prefix="/internal/ai-initiatives", tags=["ai-initiatives-internal"])

# Must match the Company-side dev fallback exactly — both sides fall back to
# this value ONLY when COSA_SERVICE_TOKEN/COSA_INTERNAL_SERVICE_TOKEN are
# unset (dev/test convenience). See
# services/company/shared/events/service-identity.ts::DEV_TOKEN — the plan's
# Task 6 design intends these to be the SAME shared secret (Company's
# requireCosaServiceToken() and this check), not two independent tokens that
# happen to have different string values.
_DEV_TOKEN = "local-dev-service-token"


def _require_service_token(token: str | None) -> None:
    expected = (
        os.environ.get("COSA_SERVICE_TOKEN")
        or os.environ.get("COSA_INTERNAL_SERVICE_TOKEN")
        or _DEV_TOKEN
    )
    if not token or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid service token",
        )


def compute_decision_hash(
    decision_id: str,
    revision: int,
    lifecycle_state: str,
    workspace_id: str,
    project_id: str,
) -> str:
    """Must match `computeDecisionHash` in
    `services/company/operations/services/ai-initiative-cosa.client.ts` exactly —
    same field order and `:` separator."""
    return hashlib.sha256(
        f"{decision_id}:{revision}:{lifecycle_state}:{workspace_id}:{project_id}".encode()
    ).hexdigest()


class PromotionSnapshotRequest(BaseModel):
    initiative_id: str
    initiative_revision: int
    workspace_id: str
    project_id: str
    lifecycle_state: str
    risk_tier: str
    autonomy_tier: str
    decision_id: str
    decision_hash: str
    pins: dict[str, Any] = Field(default_factory=dict)
    value_contract_revision: int | None = None
    data_readiness_revision: int | None = None
    budget_policy_revision: int | None = None
    evaluation_suite_revision: int | None = None
    data_readiness_status: str | None = None
    retrieval_mode: str | None = None


class PromotionSnapshotResponse(BaseModel):
    status: str
    accepted: bool
    decision_id: str
    initiative_id: str


def _get_snapshot_store(request: Request) -> Any:
    plane = getattr(request.app.state, "plane", None) or getattr(
        request.app.state, "cosa_agent_plane", None
    )
    store = getattr(plane, "ai_initiative_snapshot_store", None) if plane else None
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ai initiative snapshot store not initialized",
        )
    return store


@router.post("/snapshots", response_model=PromotionSnapshotResponse)
async def consume_promotion_snapshot(
    request: Request,
    body: PromotionSnapshotRequest,
    x_cosa_service_token: str | None = Header(default=None),
) -> PromotionSnapshotResponse:
    # 1. Require internal service token
    _require_service_token(x_cosa_service_token)

    # 2. Required scope identity — fail closed on any missing field instead of
    # silently treating it as "no constraint" (see module docstring: the real
    # scope/tamper check is the hash comparison below, this is just presence).
    for field_name, value in (
        ("workspace_id", body.workspace_id),
        ("project_id", body.project_id),
        ("initiative_id", body.initiative_id),
        ("decision_id", body.decision_id),
    ):
        if not value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{field_name} is required",
            )

    # 3. Recompute and verify decision_hash — the real scope/tamper check.
    # A decision resubmitted under a different project_id/workspace_id, or with
    # a mutated decision_id/revision/lifecycle_state, fails this comparison
    # because all five fields are bound into the hash Company computed.
    expected_hash = compute_decision_hash(
        body.decision_id,
        body.initiative_revision,
        body.lifecycle_state,
        body.workspace_id,
        body.project_id,
    )
    if not body.decision_hash or body.decision_hash != expected_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="decision hash mismatch: scope or lifecycle drift detected",
        )

    # 4. Durable idempotent consume (Postgres-backed; survives restart).
    store = _get_snapshot_store(request)
    idempotency_key = f"{body.workspace_id}:{body.initiative_id}:{body.decision_id}"
    snapshot = AiInitiativePromotionSnapshot(
        workspace_id=body.workspace_id,
        project_id=body.project_id,
        initiative_id=body.initiative_id,
        initiative_revision=body.initiative_revision,
        decision_id=body.decision_id,
        decision_hash=body.decision_hash,
        lifecycle_state=body.lifecycle_state,
        risk_tier=body.risk_tier,
        autonomy_tier=body.autonomy_tier,
        pins=body.pins,
        value_contract_revision=body.value_contract_revision,
        data_readiness_revision=body.data_readiness_revision,
        budget_policy_revision=body.budget_policy_revision,
        evaluation_suite_revision=body.evaluation_suite_revision,
        data_readiness_status=body.data_readiness_status,
        retrieval_mode=body.retrieval_mode,
    )
    _, already_consumed = await store.consume(idempotency_key, snapshot)

    return PromotionSnapshotResponse(
        status="already_consumed" if already_consumed else "accepted",
        accepted=True,
        decision_id=body.decision_id,
        initiative_id=body.initiative_id,
    )
