"""M5 §4 — relay command gate: audit ghi cả accepted lẫn rejected."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from agent_core.remote import (
    CommandEnvelope,
    CommandEnvelopeVerifier,
    EnvelopeError,
    InMemoryAuditSink,
    Principal,
    RelayCommandGate,
    sign_envelope,
)

KEY = b"relay-key-0002"


def _signed(nonce="n", ttl=120, ws="1001"):
    now = datetime.now(UTC)
    env = CommandEnvelope(
        workspace_id=ws,
        principal=Principal("workforce_member", "wm-7"),
        command={"action": "sync_now"},
        nonce=nonce,
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(seconds=ttl)).isoformat(),
    )
    return sign_envelope(env, KEY)


def _gate():
    sink = InMemoryAuditSink()
    return RelayCommandGate(CommandEnvelopeVerifier(KEY), sink), sink


def test_accepted_command_is_audited_with_verified_principal():
    gate, sink = _gate()
    out = gate.accept(_signed())
    assert out.principal == Principal("workforce_member", "wm-7")
    assert len(sink.entries) == 1
    e = sink.entries[0]
    assert e.outcome == "accepted"
    assert e.source == "remote_relay"
    assert e.principal == Principal("workforce_member", "wm-7")
    assert e.reject_reason is None


def test_rejected_command_is_still_audited():
    gate, sink = _gate()
    bad = _signed().to_dict()
    bad["signature"] = "deadbeef"
    with pytest.raises(EnvelopeError):
        gate.accept(bad)
    assert len(sink.entries) == 1
    e = sink.entries[0]
    assert e.outcome == "rejected"
    assert "chữ ký" in (e.reject_reason or "")
    # principal thô vẫn được ghi để truy vết, dù không tin
    assert e.principal == Principal("workforce_member", "wm-7")


def test_replayed_command_audited_as_rejected_on_second_attempt():
    gate, sink = _gate()
    env = _signed(nonce="dup")
    gate.accept(env)
    with pytest.raises(EnvelopeError, match="replay"):
        gate.accept(env)
    assert [x.outcome for x in sink.entries] == ["accepted", "rejected"]


def test_malformed_envelope_audited_without_crashing():
    gate, sink = _gate()
    with pytest.raises(EnvelopeError):
        gate.accept({"garbage": True})
    assert len(sink.entries) == 1
    assert sink.entries[0].outcome == "rejected"
    assert sink.entries[0].workspace_id == "?"
