"""Local Entitlement Manager and Quota Engine for COSA (Phase 3).

Enforces data-driven tier limits and feature gating based on offline cached snapshots.
Specification: COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md (Section 4, 5)
"""
from datetime import datetime
from enum import Enum
import logging
from typing import Dict, Optional, Tuple
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from platform_core.sync.entitlement_crypto import build_local_default_snapshot, verify_snapshot_signature
from platform_core.sync.models import LocalEntitlementSnapshot
from platform_core.sync.schemas import (
    EntitlementFeatures,
    EntitlementLimits,
    SignedEntitlementSnapshot,
)

logger = logging.getLogger(__name__)


def _snapshot_to_row_fields(snapshot: SignedEntitlementSnapshot) -> dict:
    return dict(
        company_id=str(snapshot.company_id),
        plan=snapshot.plan,
        payload_jsonb=snapshot.model_dump(mode="json"),
        signature=snapshot.signature,
        signature_alg=snapshot.signature_alg,
        key_id=snapshot.key_id,
        issued_at=snapshot.issued_at,
        valid_until=snapshot.valid_until,
        grace_period_days=snapshot.grace_period_days,
        verified_at=datetime.utcnow(),
        verification_status="VALID",
        is_current=True,
    )


def persist_current_snapshot(db: Session, snapshot: SignedEntitlementSnapshot) -> None:
    """Persists `snapshot` as the current row for its company (G2 P0.3).

    Runs the "old.is_current=false, insert new" transaction G2 describes —
    never updates a row in place, so verification history stays auditable.
    Caller is responsible for the surrounding commit (matches how the rest
    of this codebase's sync `Session` endpoints work).
    """
    from core.snowflake import generate_snowflake_id

    company_id = str(snapshot.company_id)
    db.execute(
        update(LocalEntitlementSnapshot)
        .where(
            LocalEntitlementSnapshot.company_id == company_id,
            LocalEntitlementSnapshot.is_current.is_(True),
        )
        .values(is_current=False)
    )
    db.add(LocalEntitlementSnapshot(id=generate_snowflake_id(), **_snapshot_to_row_fields(snapshot)))
    db.flush()


def load_current_snapshot_from_db(db: Session, company_id: str) -> Optional[SignedEntitlementSnapshot]:
    """Loads the persisted current snapshot for `company_id`, re-verifying its
    signature before trusting it (a DB row is not inherently trustworthy —
    it must still pass the same crypto check a freshly-received snapshot would)."""
    row = db.execute(
        select(LocalEntitlementSnapshot).where(
            LocalEntitlementSnapshot.company_id == str(company_id),
            LocalEntitlementSnapshot.is_current.is_(True),
        )
    ).scalars().first()
    if row is None:
        return None

    snapshot = SignedEntitlementSnapshot(**row.payload_jsonb)
    if not verify_snapshot_signature(snapshot):
        logger.error(
            "Persisted entitlement snapshot for company %s failed re-verification on load; ignoring.",
            company_id,
        )
        return None
    return snapshot


def load_all_current_snapshots_into_cache(db: Session) -> int:
    """Startup hook (G2 P0.3): reload every persisted current snapshot into
    the in-memory cache before the app serves any request, so a restart
    never silently falls back to Free for a company with a still-valid
    persisted license. Returns the number of snapshots loaded."""
    rows = db.execute(
        select(LocalEntitlementSnapshot).where(LocalEntitlementSnapshot.is_current.is_(True))
    ).scalars().all()

    loaded = 0
    for row in rows:
        try:
            snapshot = SignedEntitlementSnapshot(**row.payload_jsonb)
        except Exception:
            logger.error("Could not deserialize persisted entitlement snapshot id=%s; skipping.", row.id)
            continue
        if not verify_snapshot_signature(snapshot):
            logger.error(
                "Persisted entitlement snapshot for company %s failed re-verification on startup load; skipping.",
                row.company_id,
            )
            continue
        EntitlementManager._cache[str(row.company_id)] = snapshot
        loaded += 1

    logger.info("Loaded %d persisted entitlement snapshot(s) into cache on startup.", loaded)
    return loaded


class EntitlementStatusMode(str, Enum):
    ACTIVE = "ACTIVE"
    GRACE_PERIOD = "GRACE_PERIOD"
    RESTRICTED = "RESTRICTED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"


class EntitlementManager:
    """Manages cached company entitlements and evaluates offline access permissions."""

    _cache: Dict[str, SignedEntitlementSnapshot] = {}

    @classmethod
    def get_default_free_snapshot(cls, company_id: str) -> SignedEntitlementSnapshot:
        """Generates the baseline Free / Learning tier snapshot for unlicensed workspaces."""
        return build_local_default_snapshot(
            company_id=company_id,
            plan="free",
            limits=EntitlementLimits(max_projects=1, max_seats=2, max_scheduled_agents=1),
            features=EntitlementFeatures(marketing=True, crm=True, finance=False, custom_domain=False),
            validity_days=365,
            grace_period_days=30,
        )

    @classmethod
    def save_snapshot(
        cls,
        snapshot: SignedEntitlementSnapshot,
        secret: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> bool:
        """Stores snapshot in local cache after verifying cryptographic integrity.

        When `db` is provided, also persists it as the current row in
        `local_entitlement_snapshots` (G2 P0.3) so it survives a restart —
        caller owns the transaction/commit. `db` is optional so this stays a
        drop-in replacement for every existing in-memory-only caller.
        """
        if not verify_snapshot_signature(snapshot, hmac_secret=secret):
            logger.error(f"Cannot save snapshot for company {snapshot.company_id}: Invalid signature!")
            return False

        cls._cache[str(snapshot.company_id)] = snapshot
        if db is not None:
            persist_current_snapshot(db, snapshot)
        logger.info(f"Updated local entitlement cache for company {snapshot.company_id} ({snapshot.plan})")
        return True

    @classmethod
    def get_snapshot(cls, company_id: str) -> SignedEntitlementSnapshot:
        """Gets cached snapshot or fallback to Free baseline."""
        company_key = str(company_id)
        if company_key not in cls._cache:
            cls._cache[company_key] = cls.get_default_free_snapshot(company_key)
        return cls._cache[company_key]

    @classmethod
    def get_status_mode(
        cls, company_id: str, at_time: Optional[datetime] = None, secret: Optional[str] = None
    ) -> EntitlementStatusMode:
        """Calculates current license mode (ACTIVE, GRACE_PERIOD, RESTRICTED, INVALID_SIGNATURE)."""
        snapshot = cls.get_snapshot(company_id)
        now = at_time or datetime.utcnow()

        if not verify_snapshot_signature(snapshot, hmac_secret=secret):
            return EntitlementStatusMode.INVALID_SIGNATURE

        if snapshot.is_valid(now):
            return EntitlementStatusMode.ACTIVE
        elif snapshot.is_within_grace_period(now):
            return EntitlementStatusMode.GRACE_PERIOD
        else:
            return EntitlementStatusMode.RESTRICTED

    @classmethod
    def is_feature_allowed(cls, company_id: str, feature_name: str) -> bool:
        """Checks whether a feature flag is enabled in the current license and not in restricted mode."""
        status = cls.get_status_mode(company_id)
        if status == EntitlementStatusMode.RESTRICTED or status == EntitlementStatusMode.INVALID_SIGNATURE:
            # Restricted mode: Only core features remain accessible in read-only
            if feature_name in ["custom_domain", "priority_sync", "private_intake"]:
                return False

        snapshot = cls.get_snapshot(company_id)
        features_dict = snapshot.features.model_dump()
        return bool(features_dict.get(feature_name, False))

    @classmethod
    def check_quota_allowed(
        cls, company_id: str, quota_name: str, current_count: int
    ) -> Tuple[bool, str]:
        """Checks if creating an object is within the allowed limits."""
        status = cls.get_status_mode(company_id)
        snapshot = cls.get_snapshot(company_id)
        limits_dict = snapshot.limits.model_dump()

        limit = limits_dict.get(quota_name, 1)

        # In Restricted Mode: no new object creation is permitted if at or above Free baseline
        if status in [EntitlementStatusMode.RESTRICTED, EntitlementStatusMode.INVALID_SIGNATURE]:
            if current_count >= 1:
                return (
                    False,
                    f"License is in Restricted Mode (Expired). Maximum allowed is {1}. Please refresh license.",
                )

        if current_count >= limit:
            return (
                False,
                f"Plan limit exceeded for '{quota_name}'. Current: {current_count}, Limit: {limit}. Upgrade required.",
            )

        return True, "Quota OK"
