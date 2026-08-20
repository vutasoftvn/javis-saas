"""Unit tests for Ed25519 entitlement signing/verification (G2 P0.1 / G3 §9.1).

Central holds the private key and signs; Local only ever holds public
key(s) and verifies. These tests assert the asymmetry holds: a party with
only the public key material can verify but cannot forge a signature, and
verification correctly rejects tampering, a wrong/absent key_id, and a
missing key catalog — matching G2 §23.1's required license test list
(valid signature; invalid signature; wrong key; local cannot sign).
"""
import base64
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.platform.sync.entitlement_crypto import (
    Ed25519EntitlementSigner,
    Ed25519EntitlementVerifier,
    MissingEd25519KeyError,
    verify_snapshot_signature,
)
from app.platform.sync.schemas import EntitlementFeatures, EntitlementLimits


def _make_keypair() -> tuple[str, str]:
    """Returns (private_key_b64, public_key_b64) for a fresh Ed25519 keypair."""
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_b64 = base64.urlsafe_b64encode(
        private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    ).decode("utf-8")
    public_b64 = base64.urlsafe_b64encode(
        public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode("utf-8")
    return private_b64, public_b64


def test_ed25519_signing_and_verification_integrity(monkeypatch):
    """Central signs with the private key; Local verifies with only the public key."""
    private_b64, public_b64 = _make_keypair()
    key_id = "2026-01"
    monkeypatch.setenv("COSA_ENTITLEMENT_PRIVATE_KEY_B64", private_b64)
    monkeypatch.setenv("COSA_ENTITLEMENT_KEY_ID", key_id)

    company_id = uuid.uuid4()
    snapshot = Ed25519EntitlementSigner.sign_snapshot(
        company_id=company_id,
        plan="pro",
        limits=EntitlementLimits(max_projects=10, max_seats=5),
        features=EntitlementFeatures(marketing=True, crm=True, finance=True, custom_domain=True),
    )
    assert snapshot.signature_alg == "ED25519"
    assert snapshot.key_id == key_id

    # Local only ever holds the public key — verify without any private key present.
    catalog = {key_id: public_b64}
    assert Ed25519EntitlementVerifier.verify_signature(snapshot, public_key_catalog=catalog) is True
    assert verify_snapshot_signature(snapshot, public_key_catalog=catalog) is True


def test_ed25519_tamper_detection(monkeypatch):
    private_b64, public_b64 = _make_keypair()
    key_id = "2026-01"
    monkeypatch.setenv("COSA_ENTITLEMENT_KEY_ID", key_id)
    catalog = {key_id: public_b64}

    snapshot = Ed25519EntitlementSigner.sign_snapshot(
        company_id=uuid.uuid4(),
        plan="pro",
        limits=EntitlementLimits(),
        features=EntitlementFeatures(),
        private_key_b64=private_b64,
    )
    assert Ed25519EntitlementVerifier.verify_signature(snapshot, public_key_catalog=catalog) is True

    tampered = snapshot.model_copy(update={"plan": "enterprise"})
    assert Ed25519EntitlementVerifier.verify_signature(tampered, public_key_catalog=catalog) is False


def test_ed25519_verification_fails_with_wrong_key(monkeypatch):
    """A snapshot signed by one keypair must not verify against a different public key."""
    private_a, _ = _make_keypair()
    _, public_b = _make_keypair()
    key_id = "2026-01"
    monkeypatch.setenv("COSA_ENTITLEMENT_KEY_ID", key_id)

    snapshot = Ed25519EntitlementSigner.sign_snapshot(
        company_id=uuid.uuid4(),
        plan="pro",
        limits=EntitlementLimits(),
        features=EntitlementFeatures(),
        private_key_b64=private_a,
    )

    wrong_catalog = {key_id: public_b}
    assert Ed25519EntitlementVerifier.verify_signature(snapshot, public_key_catalog=wrong_catalog) is False


def test_ed25519_verification_fails_with_unknown_key_id(monkeypatch):
    private_b64, public_b64 = _make_keypair()
    monkeypatch.setenv("COSA_ENTITLEMENT_KEY_ID", "signing-key-id")

    snapshot = Ed25519EntitlementSigner.sign_snapshot(
        company_id=uuid.uuid4(),
        plan="pro",
        limits=EntitlementLimits(),
        features=EntitlementFeatures(),
        private_key_b64=private_b64,
    )

    catalog = {"a-completely-different-key-id": public_b64}
    assert Ed25519EntitlementVerifier.verify_signature(snapshot, public_key_catalog=catalog) is False


def test_local_cannot_sign_without_private_key(monkeypatch):
    """The defining property of P0.1: a runtime holding only public key material
    must not be able to produce a valid signature at all."""
    monkeypatch.delenv("COSA_ENTITLEMENT_PRIVATE_KEY_B64", raising=False)
    monkeypatch.delenv("COSA_ENTITLEMENT_KEY_ID", raising=False)

    with pytest.raises(MissingEd25519KeyError):
        Ed25519EntitlementSigner.sign_snapshot(
            company_id=uuid.uuid4(),
            plan="pro",
            limits=EntitlementLimits(),
            features=EntitlementFeatures(),
        )


def test_local_default_snapshot_always_verifies():
    """The unsigned Free-tier baseline (build_local_default_snapshot) must
    verify without any key material configured — it grants no privilege
    beyond what every unlicensed workspace already gets."""
    from app.platform.sync.entitlement_manager import EntitlementManager

    snapshot = EntitlementManager.get_default_free_snapshot(str(uuid.uuid4()))
    assert snapshot.signature_alg == "LOCAL_DEFAULT"
    assert verify_snapshot_signature(snapshot) is True
