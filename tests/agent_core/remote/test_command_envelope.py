"""M5 §4 — command envelope: chữ ký, hạn dùng, clock-skew, chống replay."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from agent_core.remote import (
    CommandEnvelope,
    CommandEnvelopeVerifier,
    EnvelopeError,
    NonceReplayCache,
    Principal,
    sign_envelope,
)

KEY = b"relay-signing-key-shared-secret-0001"


def _env(*, nonce="n-1", ttl_sec=120, issued: datetime | None = None, ws="1001") -> CommandEnvelope:
    now = issued or datetime.now(UTC)
    return CommandEnvelope(
        workspace_id=ws,
        principal=Principal("user", "u-42"),
        command={"action": "run_capability", "capability": "daily_brief"},
        nonce=nonce,
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(seconds=ttl_sec)).isoformat(),
    )


def test_valid_envelope_round_trip_returns_trusted_principal():
    signed = sign_envelope(_env(), KEY)
    v = CommandEnvelopeVerifier(KEY)
    out = v.verify(signed)
    assert out.workspace_id == "1001"
    assert out.principal == Principal("user", "u-42")
    assert out.command["capability"] == "daily_brief"


def test_verify_accepts_plain_dict():
    signed = sign_envelope(_env(), KEY).to_dict()
    out = CommandEnvelopeVerifier(KEY).verify(signed)
    assert out.principal.id == "u-42"


def test_tampered_command_fails_signature():
    signed = sign_envelope(_env(), KEY)
    tampered = CommandEnvelope(
        workspace_id=signed.workspace_id,
        principal=signed.principal,
        command={"action": "delete_everything"},
        nonce=signed.nonce,
        issued_at=signed.issued_at,
        expires_at=signed.expires_at,
        signature=signed.signature,
    )
    with pytest.raises(EnvelopeError, match="chữ ký"):
        CommandEnvelopeVerifier(KEY).verify(tampered)


def test_wrong_key_fails_signature():
    signed = sign_envelope(_env(), KEY)
    with pytest.raises(EnvelopeError, match="chữ ký"):
        CommandEnvelopeVerifier(b"different-key").verify(signed)


def test_missing_signature_rejected():
    with pytest.raises(EnvelopeError, match="thiếu signature"):
        CommandEnvelopeVerifier(KEY).verify(_env())


def test_expired_envelope_rejected():
    old = datetime.now(UTC) - timedelta(minutes=10)
    signed = sign_envelope(_env(issued=old, ttl_sec=60), KEY)
    with pytest.raises(EnvelopeError, match="hết hạn"):
        CommandEnvelopeVerifier(KEY).verify(signed)


def test_issued_in_far_future_rejected():
    future = datetime.now(UTC) + timedelta(minutes=5)
    signed = sign_envelope(_env(issued=future), KEY)
    with pytest.raises(EnvelopeError, match="clock-skew"):
        CommandEnvelopeVerifier(KEY).verify(signed)


def test_ttl_over_cap_rejected():
    signed = sign_envelope(_env(ttl_sec=60 * 60), KEY)  # 1h > trần 15m
    with pytest.raises(EnvelopeError, match="TTL"):
        CommandEnvelopeVerifier(KEY).verify(signed)


def test_replay_same_nonce_rejected_second_time():
    v = CommandEnvelopeVerifier(KEY)
    signed = sign_envelope(_env(nonce="dup"), KEY)
    v.verify(signed)
    with pytest.raises(EnvelopeError, match="replay"):
        v.verify(signed)


def test_same_nonce_different_workspace_is_allowed():
    v = CommandEnvelopeVerifier(KEY)
    v.verify(sign_envelope(_env(nonce="shared", ws="1001"), KEY))
    # nonce bind theo (workspace_id, nonce) ⇒ workspace khác không bị chặn
    v.verify(sign_envelope(_env(nonce="shared", ws="2002"), KEY))


def test_nonce_cache_evicts_expired_entries():
    cache = NonceReplayCache()
    cache.check_and_record("1001", "n", expires_at_epoch=100.0, now=50.0)
    assert len(cache) == 1
    # sau khi quá expires ⇒ evict, nonce có thể tái dùng (cửa sổ expires_at đã tự chặn)
    cache.check_and_record("1001", "n", expires_at_epoch=200.0, now=150.0)
    assert len(cache) == 1
