"""Local Entitlement Manager and Quota Engine for COSA (Phase 3).

Enforces data-driven tier limits and feature gating based on offline cached snapshots.
Specification: COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md (Section 4, 5)
"""
from datetime import datetime
from enum import Enum
import logging
from typing import Dict, Optional, Tuple
import uuid

from app.platform.sync.entitlement_crypto import EntitlementSigner, EntitlementVerifier
from app.platform.sync.schemas import (
    EntitlementFeatures,
    EntitlementLimits,
    SignedEntitlementSnapshot,
)

logger = logging.getLogger(__name__)


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
        return EntitlementSigner.sign_snapshot(
            company_id=company_id,
            plan="free",
            limits=EntitlementLimits(max_projects=1, max_seats=2, max_scheduled_agents=1),
            features=EntitlementFeatures(marketing=True, crm=True, finance=False, custom_domain=False),
            validity_days=365,
            grace_period_days=30,
        )

    @classmethod
    def save_snapshot(cls, snapshot: SignedEntitlementSnapshot, secret: Optional[str] = None) -> bool:
        """Stores snapshot in local cache after verifying cryptographic integrity."""
        if not EntitlementVerifier.verify_signature(snapshot, verification_secret=secret):
            logger.error(f"Cannot save snapshot for company {snapshot.company_id}: Invalid signature!")
            return False

        cls._cache[str(snapshot.company_id)] = snapshot
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

        if not EntitlementVerifier.verify_signature(snapshot, verification_secret=secret):
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
