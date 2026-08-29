"""M3 §1 — Runtime Host Catalog + per-workspace Vault manifest."""

from __future__ import annotations

import json

import pytest
from agent.vault import HostCatalog, VaultSecurityError


@pytest.fixture
def catalog(tmp_path) -> HostCatalog:
    return HostCatalog(tmp_path / "data")


def test_register_creates_dir_tree_and_manifest(catalog, tmp_path):
    catalog.register_workspace("1001", slug="acme")
    ws_root = tmp_path / "data" / "workspaces" / "1001"
    for sub in ("vault/documents", "vault/sops", "knowledge/snapshots", "sync/outbox", "backup"):
        assert (ws_root / sub).is_dir(), sub
    manifest = catalog.read_manifest("1001")
    assert manifest.workspace_id == "1001"
    assert manifest.schema_version == 1
    assert manifest.slug == "acme"


def test_manifest_holds_key_ref_not_the_key(catalog, tmp_path):
    catalog.register_workspace("1001")
    body = (tmp_path / "data" / "workspaces" / "1001" / "manifest.json").read_text()
    assert "host/keys/1001.dek" in body  # ref, not material
    parsed = json.loads(body)
    for forbidden in ("key", "dek", "secret", "token", "passphrase", "private_key"):
        assert forbidden not in parsed


def test_register_is_idempotent_and_preserves_manifest(catalog, tmp_path):
    catalog.register_workspace("1001", slug="acme")
    created_at = catalog.read_manifest("1001").created_at
    catalog.register_workspace("1001", slug="acme", runtime_mode="cloud")
    assert catalog.read_manifest("1001").created_at == created_at  # not overwritten
    assert catalog.get_workspace("1001").runtime_mode == "cloud"


def test_catalog_lists_and_isolates_per_workspace_modes(catalog):
    catalog.register_workspace("1001", runtime_mode="local", sync_mode="off")
    catalog.register_workspace("2002", runtime_mode="cloud", sync_mode="bidirectional")
    ids = {e.workspace_id for e in catalog.list_workspaces()}
    assert ids == {"1001", "2002"}
    assert catalog.get_workspace("1001").sync_mode == "off"
    assert catalog.get_workspace("2002").sync_mode == "bidirectional"


def test_set_modes_updates_only_target(catalog):
    catalog.register_workspace("1001")
    catalog.register_workspace("2002")
    catalog.set_modes("1001", sync_mode="outbox")
    assert catalog.get_workspace("1001").sync_mode == "outbox"
    assert catalog.get_workspace("2002").sync_mode == "off"


def test_deregister_removes_catalog_entry_but_keeps_files(catalog, tmp_path):
    catalog.register_workspace("1001")
    catalog.deregister_workspace("1001")
    assert catalog.get_workspace("1001") is None
    assert (tmp_path / "data" / "workspaces" / "1001" / "manifest.json").exists()


def test_catalog_survives_new_instance(catalog, tmp_path):
    catalog.register_workspace("1001", slug="acme")
    reopened = HostCatalog(tmp_path / "data")
    assert reopened.get_workspace("1001").slug == "acme"


def test_bad_workspace_id_rejected(catalog):
    with pytest.raises(VaultSecurityError):
        catalog.register_workspace("../evil")


def test_read_manifest_before_register_raises(catalog):
    with pytest.raises(VaultSecurityError):
        catalog.read_manifest("9999")


def test_set_modes_before_register_raises(catalog):
    with pytest.raises(VaultSecurityError):
        catalog.set_modes("9999", runtime_mode="cloud")
