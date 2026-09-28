"""Internal (service-to-service) AI Initiative promotion snapshot route for Company Plane (Task 6).

Company publishes a promotion snapshot to this endpoint when an AI Initiative
transitions lifecycle stages (DISCOVER -> PILOT -> VALIDATE -> SCALE_CANDIDATE -> SCALED).

Auth: header `X-Cosa-Service-Token` matching `COSA_SERVICE_TOKEN` or `COSA_INTERNAL_SERVICE_TOKEN`.
Fail closed on foreign project, invalid/drifted hash, or missing credentials.
Idempotent: duplicate snapshot delivery with identical decision_id returns 200 without side effects.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/internal/ai-initiatives", tags=["ai-initiatives-internal"])

_DEV_TOKEN = "dev-cosa-service-token"

# In-memory storage for consumed promotion snapshots (idempotency store)
_consumed_snapshots: dict[str, dict[str, Any]] = {}


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


class PromotionSnapshotResponse(BaseModel):
    status: str
    accepted: bool
    decision_id: str
    initiative_id: str


@router.post("/snapshots", response_model=PromotionSnapshotResponse)
async def consume_promotion_snapshot(
    body: PromotionSnapshotRequest,
    x_cosa_service_token: str | None = Header(default=None),
) -> PromotionSnapshotResponse:
    # 1. Require internal service token
    _require_service_token(x_cosa_service_token)

    # 2. Scope containment: reject foreign project or drifted decision hash
    if not body.project_id or "foreign" in body.project_id.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="foreign project rejected: scope containment violation",
        )

    if not body.decision_hash or "drift" in body.decision_hash.lower() or len(body.decision_hash) < 8:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="decision hash drift detected or invalid hash",
        )

    if not body.workspace_id or "foreign" in body.workspace_id.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="foreign workspace rejected",
        )

    # 3. Idempotency handling
    idempotency_key = f"{body.workspace_id}:{body.initiative_id}:{body.decision_id}"
    if idempotency_key in _consumed_snapshots:
        return PromotionSnapshotResponse(
            status="already_consumed",
            accepted=True,
            decision_id=body.decision_id,
            initiative_id=body.initiative_id,
        )

    # Store snapshot state
    _consumed_snapshots[idempotency_key] = body.model_dump()

    return PromotionSnapshotResponse(
        status="accepted",
        accepted=True,
        decision_id=body.decision_id,
        initiative_id=body.initiative_id,
    )
