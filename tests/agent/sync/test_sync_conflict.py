"""M6 §4/§5 — conflict recovery: revision reconcile + human-resolve queue."""

from __future__ import annotations

import base64
import json
import os

import pytest
from agent.sync import (
    ConflictResolution,
    SyncConflictError,
    build_sync_envelope,
    resolve_incoming_revision,
    write_conflict_entry,
)
from agent.vault import WorkspaceKeyManager


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("COSA_VAULT_MASTER_KEY", base64.b64encode(os.urandom(32)).decode())


@pytest.fixture
def keys(tmp_path) -> WorkspaceKeyManager:
    km = WorkspaceKeyManager(tmp_path / "data")
    km.ensure_dek("1001")
    return km


def _env(keys, entity_type, revision, base_revision):
    return build_sync_envelope(
        workspace_id="1001",
        entity_type=entity_type,
        entity_id="e-1",
        revision=revision,
        base_revision=base_revision,
        source_runtime_node_id="cloud-1",
        payload={"v": revision},
        keys=keys,
    )


def test_fast_forward_applies(keys):
    env = _env(keys, "task", revision=5, base_revision=4)
    assert resolve_incoming_revision(incoming=env, current_revision=4) == ConflictResolution.APPLY


def test_stale_incoming_ignored(keys):
    env = _env(keys, "task", revision=3, base_revision=1)
    assert (
        resolve_incoming_revision(incoming=env, current_revision=5)
        == ConflictResolution.IGNORE_STALE
    )


def test_optimistic_divergence_applies_with_audit(keys):
    env = _env(keys, "task", revision=6, base_revision=3)
    assert (
        resolve_incoming_revision(incoming=env, current_revision=5)
        == ConflictResolution.APPLY_WITH_AUDIT
    )


def test_finance_legal_divergence_queues_conflict(keys):
    env = _env(keys, "financial_transaction", revision=6, base_revision=3)
    assert (
        resolve_incoming_revision(incoming=env, current_revision=5)
        == ConflictResolution.QUEUE_CONFLICT
    )


def test_never_scope_raises(keys):
    # build_sync_envelope sẽ chặn, nên dựng envelope thủ công cho entity credentials
    from agent.sync import SyncEnvelope

    env = SyncEnvelope(
        workspace_id="1001",
        entity_type="connector_authorization",
        entity_id="c-1",
        revision=2,
        base_revision=1,
        source_runtime_node_id="x",
        occurred_at="2026-08-29T00:00:00+00:00",
        idempotency_key="k",
        payload_hash="h",
        encryption_key_ref="workspace-dek:1001",
        encrypted_payload="",
    )
    with pytest.raises(SyncConflictError):
        resolve_incoming_revision(incoming=env, current_revision=1)


def test_write_conflict_entry_no_plaintext(keys, tmp_path):
    env = _env(keys, "legal_verification_approval", revision=4, base_revision=2)
    conflicts = tmp_path / "sync" / "conflicts"
    path = write_conflict_entry(
        conflicts, incoming=env, current_revision=3, local_payload_hash="localhash"
    )
    assert path.exists()
    rec = json.loads(path.read_text())
    assert rec["status"] == "AWAITING_HUMAN_RESOLVE"
    assert rec["incoming_revision"] == 4
    assert rec["current_revision"] == 3
    assert rec["local_payload_hash"] == "localhash"
    # chỉ hash + metadata, KHÔNG plaintext payload
    assert "encrypted_payload" not in rec
    assert "v" not in rec
