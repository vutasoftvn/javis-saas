"""FastAPI Router for COSA Platform Sync (Phase 2).

Provides endpoints for Central Ingestion simulation, Outbox manual trigger, and Sync health monitoring.
Specification: COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md
"""
import os
from datetime import datetime
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.workspace_context import WorkspaceContext, get_workspace_context
from app.db.session import get_db
from app.platform.sync.models import PlatformOutbox, PlatformInbox
from app.platform.sync.schemas import PlatformEventEnvelope
from app.platform.sync.sync_worker import PlatformSyncWorker

router = APIRouter(prefix="/sync", tags=["Platform Sync"])

# G2 P0.2 / G3 §9.2: COSA_RUNTIME_PLANE gates control-plane-only endpoints
# (entitlement signing) off of the company/local runtime — a company install
# must never be able to issue its own paid entitlement. Default "company" is
# deliberately the safe default: an unset/misconfigured env var must NOT
# accidentally expose the signing endpoint.
_RUNTIME_PLANE = os.getenv("COSA_RUNTIME_PLANE", "company").strip().lower()


class IngestBatchRequest(BaseModel):
    events: List[PlatformEventEnvelope] = Field(default_factory=list)


class IngestBatchResponse(BaseModel):
    status: str = "ok"
    total_received: int
    acknowledged: Dict[str, bool] = Field(default_factory=dict)


class SyncStatusResponse(BaseModel):
    status: str
    pending_events: int
    failed_events: int
    acknowledged_events: int
    last_synced_at: str | None


@router.post("/ingest", response_model=IngestBatchResponse)
def ingest_platform_events(
    payload: IngestBatchRequest,
    db: Session = Depends(get_db),
) -> IngestBatchResponse:
    """Ingestion endpoint for receiving platform lifecycle events (Idempotent)."""
    acknowledged: Dict[str, bool] = {}
    for event in payload.events:
        event_id_str = str(event.event_id)
        # Idempotency check: in production this writes to Central tables or inbox
        acknowledged[event_id_str] = True

    return IngestBatchResponse(
        status="ok",
        total_received=len(payload.events),
        acknowledged=acknowledged,
    )


@router.post("/outbox/trigger")
def trigger_outbox_sync(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Manually triggers the sync worker to flush pending outbox events."""
    worker = PlatformSyncWorker()
    processed_count = worker.process_outbox_batch(db=db)
    return {
        "status": "success",
        "processed_events": processed_count,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/status", response_model=SyncStatusResponse)
def get_sync_status(
    db: Session = Depends(get_db),
) -> SyncStatusResponse:
    """Gets the current status and metrics of the platform sync queue."""
    pending_count = db.scalar(
        select(func.count()).select_from(PlatformOutbox).where(PlatformOutbox.status == "pending")
    ) or 0

    failed_count = db.scalar(
        select(func.count()).select_from(PlatformOutbox).where(PlatformOutbox.status == "failed")
    ) or 0

    acknowledged_count = db.scalar(
        select(func.count()).select_from(PlatformOutbox).where(PlatformOutbox.status == "acknowledged")
    ) or 0

    last_ack = db.scalar(
        select(PlatformOutbox.acknowledged_at)
        .where(PlatformOutbox.status == "acknowledged")
        .order_by(PlatformOutbox.acknowledged_at.desc())
        .limit(1)
    )

    overall_status = "healthy"
    if failed_count > 0:
        overall_status = "degraded"
    if pending_count > 100:
        overall_status = "backlogged"

    return SyncStatusResponse(
        status=overall_status,
        pending_events=pending_count,
        failed_events=failed_count,
        acknowledged_events=acknowledged_count,
        last_synced_at=last_ack.isoformat() if last_ack else None,
    )


# ============================================================================
# ENTITLEMENTS & SIGNED SNAPSHOTS
# ============================================================================

from app.platform.sync.entitlement_crypto import Ed25519EntitlementSigner
from app.platform.sync.entitlement_manager import EntitlementManager, EntitlementStatusMode
from app.platform.sync.schemas import (
    EntitlementFeatures,
    EntitlementLimits,
    SignedEntitlementSnapshot,
)


class IssueSnapshotRequest(BaseModel):
    company_id: str
    plan: str = "pro"
    limits: EntitlementLimits = Field(default_factory=EntitlementLimits)
    features: EntitlementFeatures = Field(default_factory=EntitlementFeatures)
    validity_days: int = 30
    grace_period_days: int = 7


class CurrentEntitlementResponse(BaseModel):
    company_id: str
    plan: str
    status_mode: EntitlementStatusMode
    is_valid: bool
    is_within_grace_period: bool
    limits: EntitlementLimits
    features: EntitlementFeatures
    valid_until: str
    grace_period_days: int


if _RUNTIME_PLANE == "control":
    @router.post("/entitlement/sign", response_model=SignedEntitlementSnapshot)
    def sign_company_entitlement(
        payload: IssueSnapshotRequest,
    ) -> SignedEntitlementSnapshot:
        """Central Control Plane ONLY endpoint: issues an Ed25519-signed entitlement
        snapshot. Not registered at all unless COSA_RUNTIME_PLANE=control (G2 P0.2) —
        a company/local runtime can never reach this route, so it cannot issue its
        own paid entitlement."""
        return Ed25519EntitlementSigner.sign_snapshot(
            company_id=payload.company_id,
            plan=payload.plan,
            limits=payload.limits,
            features=payload.features,
            validity_days=payload.validity_days,
            grace_period_days=payload.grace_period_days,
        )


@router.post("/entitlement/refresh")
def refresh_local_entitlement(
    snapshot: SignedEntitlementSnapshot,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Local endpoint: Refreshes local cached entitlement with a newly signed snapshot.

    Persists to `local_entitlement_snapshots` (G2 P0.3) so this survives a
    restart — previously cache-only, meaning every restart silently dropped
    back to the Free tier default regardless of a still-valid license.
    """
    success = EntitlementManager.save_snapshot(snapshot, db=db)
    if success:
        db.commit()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cryptographic signature on snapshot.",
        )
    return {
        "status": "success",
        "message": f"Updated entitlement for company {snapshot.company_id} ({snapshot.plan})",
        "mode": EntitlementManager.get_status_mode(str(snapshot.company_id)),
    }


@router.get("/entitlement/current", response_model=CurrentEntitlementResponse)
def get_current_entitlement(
    ctx: WorkspaceContext = Depends(get_workspace_context),
) -> CurrentEntitlementResponse:
    """Frontend (Hologram Hub) endpoint: Retrieves current tier, limits, and license mode.

    `company_id` used to be an unauthenticated query param defaulting to a
    hardcoded test UUID — any caller could read any company's entitlement
    status. Derived from a verified WorkspaceContext now (G2 P0.4).
    """
    company_id = ctx.company_id or str(ctx.workspace_id)
    snapshot = EntitlementManager.get_snapshot(company_id)
    mode = EntitlementManager.get_status_mode(company_id)
    now = datetime.utcnow()

    return CurrentEntitlementResponse(
        company_id=str(snapshot.company_id),
        plan=snapshot.plan,
        status_mode=mode,
        is_valid=snapshot.is_valid(now),
        is_within_grace_period=snapshot.is_within_grace_period(now),
        limits=snapshot.limits,
        features=snapshot.features,
        valid_until=snapshot.valid_until.isoformat(),
        grace_period_days=snapshot.grace_period_days,
    )

