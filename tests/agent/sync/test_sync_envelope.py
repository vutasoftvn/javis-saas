"""M6 §3 — sync envelope: encrypt-at-rest bằng workspace DEK, verify hash, scope gate."""

from __future__ import annotations

import base64
import os

import pytest
from agent.sync import (
    SyncEnvelope,
    SyncEnvelopeError,
    SyncScopeError,
    build_sync_envelope,
    open_sync_envelope,
)
from agent.vault import WorkspaceKeyManager


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("COSA_VAULT_MASTER_KEY", base64.b64encode(os.urandom(32)).decode())


@pytest.fixture
def keys(tmp_path) -> WorkspaceKeyManager:
    km = WorkspaceKeyManager(tmp_path / "data")
    km.ensure_dek("1001")
    km.ensure_dek("2002")
    return km


def _build(keys, **over):
    kw = dict(
        workspace_id="1001",
        entity_type="task",
        entity_id="t-1",
        revision=2,
        base_revision=1,
        source_runtime_node_id="node-A",
        payload={"title": "ship it", "status": "done"},
        keys=keys,
    )
    kw.update(over)
    return build_sync_envelope(**kw)


def test_round_trip_encrypts_and_verifies(keys):
    env = _build(keys)
    assert env.encryption_key_ref == "workspace-dek:1001"
    # ciphertext không lộ plaintext
    raw = base64.b64decode(env.encrypted_payload)
    assert b"ship it" not in raw
    assert open_sync_envelope(env, keys) == {"title": "ship it", "status": "done"}


def test_dict_round_trip(keys):
    env = _build(keys).to_dict()
    assert open_sync_envelope(env, keys) == {"title": "ship it", "status": "done"}


def test_credentials_scope_refused(keys):
    with pytest.raises(SyncScopeError):
        _build(keys, entity_type="connector_authorization")


def test_transient_scope_refused(keys):
    with pytest.raises(SyncScopeError):
        _build(keys, entity_type="temp_file")


def test_revision_must_exceed_base(keys):
    with pytest.raises(SyncEnvelopeError, match="revision"):
        _build(keys, revision=1, base_revision=1)


def test_cross_workspace_key_cannot_open(keys):
    env = _build(keys)
    # ép workspace_id sang 2002 ⇒ key_ref mismatch
    forged = SyncEnvelope.from_dict({**env.to_dict(), "workspace_id": "2002"})
    with pytest.raises(SyncEnvelopeError):
        open_sync_envelope(forged, keys)


def test_tampered_ciphertext_fails_hash_or_decrypt(keys):
    env = _build(keys)
    raw = bytearray(base64.b64decode(env.encrypted_payload))
    raw[-1] ^= 0x01
    tampered = SyncEnvelope.from_dict(
        {**env.to_dict(), "encrypted_payload": base64.b64encode(bytes(raw)).decode()}
    )
    with pytest.raises(SyncEnvelopeError):
        open_sync_envelope(tampered, keys)


def test_finance_legal_entity_allowed_to_build(keys):
    env = _build(keys, entity_type="financial_transaction", entity_id="ft-9")
    assert open_sync_envelope(env, keys)["title"] == "ship it"
