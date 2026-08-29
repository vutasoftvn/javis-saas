"""M3 §6 wiring — LocalFilesystemWorkspaceStore + DEK encrypt-at-rest + quota gate."""

from __future__ import annotations

import base64
import json
import os

import pytest
from agent_core.vault import (
    HostCatalog,
    LocalFilesystemWorkspaceStore,
    QuotaExceededError,
    VaultSecurityError,
    WorkspaceKeyError,
    WorkspaceKeyManager,
    WorkspaceStorageQuota,
)


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("COSA_VAULT_MASTER_KEY", base64.b64encode(os.urandom(32)).decode())


@pytest.fixture
def data_root(tmp_path):
    return tmp_path / "cosa-data"


@pytest.fixture
def keys(data_root) -> WorkspaceKeyManager:
    km = WorkspaceKeyManager(data_root)
    km.ensure_dek("1001")
    km.ensure_dek("2002")
    return km


def test_blob_on_disk_is_ciphertext_but_get_round_trips(data_root, keys):
    store = LocalFilesystemWorkspaceStore(data_root, keys=keys)
    ref = store.put("1001", "documents", "d", "v1", b"top secret plaintext")

    blob_path = data_root / "workspaces" / "1001" / "documents" / "d" / "versions" / "v1" / "blob"
    on_disk = blob_path.read_bytes()
    assert b"top secret plaintext" not in on_disk  # đã mã hoá
    meta = json.loads(blob_path.with_name("meta.json").read_text())
    assert meta["encrypted"] is True
    assert meta["size_bytes"] == len(b"top secret plaintext")  # plaintext size

    assert store.get("1001", ref) == b"top secret plaintext"


def test_other_workspace_key_cannot_decrypt_blob(data_root, keys):
    store = LocalFilesystemWorkspaceStore(data_root, keys=keys)
    ref = store.put("1001", "documents", "d", "v1", b"for 1001")
    # ép ref sang workspace 2002 → get() từ chối trước cả khi giải mã.
    forged = ref.__class__(**{**ref.__dict__, "workspace_id": "2002"})
    with pytest.raises(VaultSecurityError):
        store.get("2002", forged)


def test_encrypted_blob_needs_key_manager_on_get(data_root, keys):
    LocalFilesystemWorkspaceStore(data_root, keys=keys).put("1001", "documents", "d", "v1", b"x")
    plain_store = LocalFilesystemWorkspaceStore(data_root)  # không có keys
    ref_store = LocalFilesystemWorkspaceStore(data_root, keys=keys)
    ref = ref_store.put("1001", "documents", "d", "v2", b"y")
    with pytest.raises(VaultSecurityError, match="key manager"):
        plain_store.get("1001", ref)


def test_tampered_ciphertext_fails_decrypt(data_root, keys):
    store = LocalFilesystemWorkspaceStore(data_root, keys=keys)
    ref = store.put("1001", "documents", "d", "v1", b"payload")
    blob_path = data_root / "workspaces" / "1001" / "documents" / "d" / "versions" / "v1" / "blob"
    blob_path.write_bytes(blob_path.read_bytes()[:-1] + b"\x00")
    with pytest.raises(WorkspaceKeyError):
        store.get("1001", ref)


def test_quota_gate_blocks_oversized_put(data_root):
    catalog = HostCatalog(data_root)
    catalog.register_workspace("1001")
    quota = WorkspaceStorageQuota(catalog, default_limit_bytes=50)
    store = LocalFilesystemWorkspaceStore(data_root, quota=quota)

    store.put("1001", "documents", "d", "v1", b"x" * 40)
    with pytest.raises(QuotaExceededError):
        store.put("1001", "documents", "d", "v2", b"y" * 20)


def test_default_store_still_plaintext_and_ungated(data_root):
    store = LocalFilesystemWorkspaceStore(data_root)
    ref = store.put("1001", "documents", "d", "v1", b"plain")
    blob_path = data_root / "workspaces" / "1001" / "documents" / "d" / "versions" / "v1" / "blob"
    assert blob_path.read_bytes() == b"plain"
    meta = json.loads(blob_path.with_name("meta.json").read_text())
    assert meta["encrypted"] is False
    assert store.get("1001", ref) == b"plain"
