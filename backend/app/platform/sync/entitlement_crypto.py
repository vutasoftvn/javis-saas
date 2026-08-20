"""Cryptographic Signing and Verification for COSA Entitlement Snapshots (Phase 3).

Provides tamper-proof offline licensing using canonical payload serialization.

G2 P0.1 / G3 §9.1: the local runtime used to hold the SAME symmetric HMAC
secret used to sign entitlement snapshots — i.e. any local install able to
verify its own license was, by construction, also able to forge one. This is
replaced by Ed25519: Central holds the private key and signs; Local only ever
holds the public key(s) and can verify but never sign.

`signature_alg` on `SignedEntitlementSnapshot` distinguishes the two schemes
during the transition period: Central now only ever issues `ED25519`
snapshots; `HMAC_SHA256` verification is kept only so already-cached legacy
snapshots keep working until they naturally expire/refresh, and requires
`COSA_PLATFORM_SIGNING_SECRET` to be explicitly configured — there is no
hardcoded fallback secret any more (the previous default was a fixed string
committed to source, which is exactly the kind of forgeable secret P0.1
removes).
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

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from app.platform.sync.schemas import (
    EntitlementFeatures,
    EntitlementLimits,
    SignedEntitlementSnapshot,
)

logger = logging.getLogger(__name__)

def _default_platform_signing_secret() -> Optional[str]:
    """Legacy HMAC signing secret — transition-only, must be explicitly
    configured via env. No hardcoded default: a fixed value committed to
    source is not a secret. Read live (not cached at import time) so
    processes/tests that set the env var after import still pick it up —
    the same live-read pattern `runtime_config.py` already uses."""
    return os.getenv("COSA_PLATFORM_SIGNING_SECRET") or None


class MissingSigningSecretError(RuntimeError):
    """Raised when legacy HMAC signing/verification is attempted without a configured secret."""


class MissingEd25519KeyError(RuntimeError):
    """Raised when an Ed25519 signing or verification key is not configured."""


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


def _canonicalize_snapshot_fields(
    company_id: uuid.UUID | str,
    plan: str,
    limits: EntitlementLimits,
    features: EntitlementFeatures,
    issued_at: datetime,
    valid_until: datetime,
    grace_period_days: int,
) -> bytes:
    return canonicalize_entitlement_data(
        company_id=str(company_id),
        plan=plan,
        limits=limits.model_dump(),
        features=features.model_dump(),
        issued_at_iso=issued_at.isoformat(),
        valid_until_iso=valid_until.isoformat(),
        grace_period_days=grace_period_days,
    )


class EntitlementSigner:
    """Legacy HMAC signer — transition-only. New issuance should use `Ed25519EntitlementSigner`."""

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
        """Generates an HMAC-signed snapshot for a company (legacy transition path)."""
        secret_str = signing_secret or _default_platform_signing_secret()
        if not secret_str:
            raise MissingSigningSecretError(
                "COSA_PLATFORM_SIGNING_SECRET is not configured; legacy HMAC signing is unavailable. "
                "Use Ed25519EntitlementSigner for new snapshot issuance."
            )
        secret = secret_str.encode("utf-8")

        now = issued_at or datetime.utcnow()
        valid_until = now + timedelta(days=validity_days)
        company_id_str = str(company_id)

        data_bytes = _canonicalize_snapshot_fields(
            company_id_str, plan, limits, features, now, valid_until, grace_period_days
        )

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
            signature_alg="HMAC_SHA256",
            key_id=None,
        )


class EntitlementVerifier:
    """Legacy HMAC verifier — transition-only, for already-cached HMAC_SHA256 snapshots."""

    @staticmethod
    def verify_signature(
        snapshot: SignedEntitlementSnapshot,
        verification_secret: Optional[str] = None,
    ) -> bool:
        """Verifies if the snapshot HMAC signature is genuine and untampered.

        Returns False (never raises) when no secret is configured — this
        runs on the hot path of every entitlement check, so a missing secret
        must degrade to "treat as invalid" rather than crash the request.
        Signing (`EntitlementSigner.sign_snapshot`), a deliberate one-off
        action, raises instead — see `MissingSigningSecretError` there.
        """
        secret_str = verification_secret or _default_platform_signing_secret()
        if not secret_str:
            logger.error(
                "COSA_PLATFORM_SIGNING_SECRET is not configured; cannot verify legacy HMAC_SHA256 "
                "snapshot for company %s — treating as invalid.", snapshot.company_id,
            )
            return False
        secret = secret_str.encode("utf-8")

        data_bytes = _canonicalize_snapshot_fields(
            snapshot.company_id, snapshot.plan, snapshot.limits, snapshot.features,
            snapshot.issued_at, snapshot.valid_until, snapshot.grace_period_days,
        )

        expected_signature = hmac.new(secret, data_bytes, hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_signature).decode("utf-8")

        return hmac.compare_digest(snapshot.signature, expected_b64)


class Ed25519EntitlementSigner:
    """Central Control Plane service to issue Ed25519-signed entitlement snapshots.

    Requires `COSA_ENTITLEMENT_PRIVATE_KEY_B64` (raw Ed25519 private key,
    urlsafe-base64 encoded) and `COSA_ENTITLEMENT_KEY_ID`. This private key
    must NEVER be present on a company/local runtime — see P0.2 / G3 §9.2
    (the signing endpoint is gated to the control plane only).
    """

    @staticmethod
    def _load_private_key(private_key_b64: Optional[str] = None) -> tuple[Ed25519PrivateKey, str]:
        key_b64 = private_key_b64 or os.getenv("COSA_ENTITLEMENT_PRIVATE_KEY_B64")
        key_id = os.getenv("COSA_ENTITLEMENT_KEY_ID")
        if not key_b64 or not key_id:
            raise MissingEd25519KeyError(
                "COSA_ENTITLEMENT_PRIVATE_KEY_B64 / COSA_ENTITLEMENT_KEY_ID must be configured "
                "on the control plane to sign entitlement snapshots."
            )
        try:
            raw = base64.urlsafe_b64decode(key_b64.encode("utf-8"))
            private_key = Ed25519PrivateKey.from_private_bytes(raw)
        except Exception as exc:
            raise MissingEd25519KeyError(f"COSA_ENTITLEMENT_PRIVATE_KEY_B64 is not a valid Ed25519 key: {exc}")
        return private_key, key_id

    @classmethod
    def sign_snapshot(
        cls,
        company_id: uuid.UUID | str,
        plan: str,
        limits: EntitlementLimits,
        features: EntitlementFeatures,
        validity_days: int = 30,
        grace_period_days: int = 7,
        issued_at: Optional[datetime] = None,
        private_key_b64: Optional[str] = None,
    ) -> SignedEntitlementSnapshot:
        private_key, key_id = cls._load_private_key(private_key_b64)

        now = issued_at or datetime.utcnow()
        valid_until = now + timedelta(days=validity_days)
        company_id_str = str(company_id)

        data_bytes = _canonicalize_snapshot_fields(
            company_id_str, plan, limits, features, now, valid_until, grace_period_days
        )

        signature = private_key.sign(data_bytes)
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
            signature_alg="ED25519",
            key_id=key_id,
        )


def _load_public_key_catalog() -> Dict[str, str]:
    """key_id -> urlsafe-base64 Ed25519 public key, from env.

    Supports either a single active key (`COSA_ENTITLEMENT_KEY_ID` +
    `COSA_ENTITLEMENT_PUBLIC_KEY_B64`) or a rotation catalog
    (`COSA_ENTITLEMENT_PUBLIC_KEYS` as a JSON object) so an old snapshot
    signed under a previous key_id still verifies during rotation.
    """
    catalog: Dict[str, str] = {}
    raw_catalog = (os.getenv("COSA_ENTITLEMENT_PUBLIC_KEYS") or "").strip()
    if raw_catalog:
        try:
            parsed = json.loads(raw_catalog)
            if isinstance(parsed, dict):
                catalog.update({str(k): str(v) for k, v in parsed.items()})
        except (json.JSONDecodeError, TypeError):
            logger.error("COSA_ENTITLEMENT_PUBLIC_KEYS is not valid JSON; ignoring.")

    single_key_id = (os.getenv("COSA_ENTITLEMENT_KEY_ID") or "").strip()
    single_key_b64 = (os.getenv("COSA_ENTITLEMENT_PUBLIC_KEY_B64") or "").strip()
    if single_key_id and single_key_b64:
        catalog.setdefault(single_key_id, single_key_b64)

    return catalog


class Ed25519EntitlementVerifier:
    """Local verifier — validates Ed25519-signed snapshots using only public key material."""

    @staticmethod
    def verify_signature(
        snapshot: SignedEntitlementSnapshot,
        public_key_catalog: Optional[Dict[str, str]] = None,
    ) -> bool:
        catalog = public_key_catalog if public_key_catalog is not None else _load_public_key_catalog()
        key_id = snapshot.key_id
        if not key_id or key_id not in catalog:
            return False

        try:
            raw = base64.urlsafe_b64decode(catalog[key_id].encode("utf-8"))
            public_key = Ed25519PublicKey.from_public_bytes(raw)
        except Exception:
            return False

        data_bytes = _canonicalize_snapshot_fields(
            snapshot.company_id, snapshot.plan, snapshot.limits, snapshot.features,
            snapshot.issued_at, snapshot.valid_until, snapshot.grace_period_days,
        )

        try:
            signature = base64.urlsafe_b64decode(snapshot.signature.encode("utf-8"))
            public_key.verify(signature, data_bytes)
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False


LOCAL_DEFAULT_SIGNATURE_ALG = "LOCAL_DEFAULT"
LOCAL_DEFAULT_SIGNATURE_MARKER = "unsigned-local-free-default"


def build_local_default_snapshot(
    company_id: uuid.UUID | str,
    plan: str,
    limits: EntitlementLimits,
    features: EntitlementFeatures,
    validity_days: int,
    grace_period_days: int,
    issued_at: Optional[datetime] = None,
) -> SignedEntitlementSnapshot:
    """Builds the offline baseline (Free tier) snapshot every unlicensed
    workspace falls back to. Deliberately NOT cryptographically signed —
    forging "you get the same baseline everyone already gets by default"
    grants no privilege, so it doesn't need `COSA_PLATFORM_SIGNING_SECRET`
    (which must stay unset-by-default per P0.1) or an Ed25519 key to exist.
    """
    now = issued_at or datetime.utcnow()
    return SignedEntitlementSnapshot(
        company_id=uuid.UUID(str(company_id)),
        plan=plan,
        limits=limits,
        features=features,
        issued_at=now,
        valid_until=now + timedelta(days=validity_days),
        grace_period_days=grace_period_days,
        signature=LOCAL_DEFAULT_SIGNATURE_MARKER,
        signature_alg=LOCAL_DEFAULT_SIGNATURE_ALG,
        key_id=None,
    )


def verify_snapshot_signature(
    snapshot: SignedEntitlementSnapshot,
    hmac_secret: Optional[str] = None,
    public_key_catalog: Optional[Dict[str, str]] = None,
) -> bool:
    """Signature-algorithm-aware dispatcher (G3 §9.1 step 4-5).

    `EntitlementManager` should call this instead of either verifier
    directly, so it transparently supports `ED25519` (current),
    `HMAC_SHA256` (legacy, already-cached snapshots) and the unsigned local
    default without the caller needing to know which one a given snapshot
    used.
    """
    if snapshot.signature_alg == LOCAL_DEFAULT_SIGNATURE_ALG:
        return snapshot.signature == LOCAL_DEFAULT_SIGNATURE_MARKER
    if snapshot.signature_alg == "ED25519":
        return Ed25519EntitlementVerifier.verify_signature(snapshot, public_key_catalog=public_key_catalog)
    if snapshot.signature_alg == "HMAC_SHA256":
        logger.warning(
            "Verifying a legacy HMAC_SHA256 entitlement snapshot for company %s — "
            "expected to disappear once it next refreshes from Central as ED25519.",
            snapshot.company_id,
        )
        return EntitlementVerifier.verify_signature(snapshot, verification_secret=hmac_secret)
    logger.error("Unknown entitlement signature_alg=%r; treating as invalid.", snapshot.signature_alg)
    return False
