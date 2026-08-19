"""Cryptographic Signing and Verification for COSA Entitlement Snapshots (Phase 3).

Provides tamper-proof offline licensing using canonical payload serialization and HMAC-SHA256 / Ed25519 signing.
Specification: COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md (Section 4, 5)
"""
import base64
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import logging
import os
from typing import Any, Dict, Optional
import uuid

from app.platform.sync.schemas import (
    EntitlementFeatures,
    EntitlementLimits,
    SignedEntitlementSnapshot,
)

logger = logging.getLogger(__name__)

# Default master secret for platform HMAC signing (in production, loaded from environment or HSM/KMS)
DEFAULT_PLATFORM_SIGNING_SECRET = os.getenv("COSA_PLATFORM_SIGNING_SECRET", "cosa_platform_master_signing_key_2026_production")


def canonicalize_entitlement_data(
    company_id: str,
    plan: str,
    limits: Dict[str, Any],
    features: Dict[str, Any],
    issued_at_iso: str,
    valid_until_iso: str,
    grace_period_days: int,
) -> bytes:
    """Produces deterministic canonical UTF-8 bytes for cryptographic signing."""
    canonical_dict = {
        "company_id": str(company_id),
        "plan": str(plan),
        "limits": dict(sorted(limits.items())),
        "features": dict(sorted(features.items())),
        "issued_at": str(issued_at_iso),
        "valid_until": str(valid_until_iso),
        "grace_period_days": int(grace_period_days),
    }
    canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return canonical_json.encode("utf-8")


class EntitlementSigner:
    """Central Control Plane service to issue signed entitlement snapshots."""

    @staticmethod
    def sign_snapshot(
        company_id: uuid.UUID | str,
        plan: str,
        limits: EntitlementLimits,
        features: EntitlementFeatures,
        validity_days: int = 30,
        grace_period_days: int = 7,
        issued_at: Optional[datetime] = None,
        signing_secret: Optional[str] = None,
    ) -> SignedEntitlementSnapshot:
        """Generates a cryptographically signed snapshot for a company."""
        now = issued_at or datetime.utcnow()
        valid_until = now + timedelta(days=validity_days)
        secret = (signing_secret or DEFAULT_PLATFORM_SIGNING_SECRET).encode("utf-8")

        company_id_str = str(company_id)
        limits_dict = limits.model_dump()
        features_dict = features.model_dump()

        data_bytes = canonicalize_entitlement_data(
            company_id=company_id_str,
            plan=plan,
            limits=limits_dict,
            features=features_dict,
            issued_at_iso=now.isoformat(),
            valid_until_iso=valid_until.isoformat(),
            grace_period_days=grace_period_days,
        )

        # Generate HMAC-SHA256 signature
        signature = hmac.new(secret, data_bytes, hashlib.sha256).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8")

        return SignedEntitlementSnapshot(
            company_id=uuid.UUID(company_id_str),
            plan=plan,
            limits=limits,
            features=features,
            issued_at=now,
            valid_until=valid_until,
            grace_period_days=grace_period_days,
            signature=signature_b64,
        )


class EntitlementVerifier:
    """Local verifier to validate cached snapshots without calling Central on every action."""

    @staticmethod
    def verify_signature(
        snapshot: SignedEntitlementSnapshot,
        verification_secret: Optional[str] = None,
    ) -> bool:
        """Verifies if the snapshot signature is genuine and untampered."""
        secret = (verification_secret or DEFAULT_PLATFORM_SIGNING_SECRET).encode("utf-8")

        data_bytes = canonicalize_entitlement_data(
            company_id=str(snapshot.company_id),
            plan=snapshot.plan,
            limits=snapshot.limits.model_dump(),
            features=snapshot.features.model_dump(),
            issued_at_iso=snapshot.issued_at.isoformat(),
            valid_until_iso=snapshot.valid_until.isoformat(),
            grace_period_days=snapshot.grace_period_days,
        )

        expected_signature = hmac.new(secret, data_bytes, hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_signature).decode("utf-8")

        return hmac.compare_digest(snapshot.signature, expected_b64)
