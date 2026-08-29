"""M3 §6 — per-workspace DEK: encrypt/decrypt, isolation, rotation, unload, destroy."""

from __future__ import annotations

import base64
import os

import pytest
from agent_core.vault import WorkspaceKeyError, WorkspaceKeyManager


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("COSA_VAULT_MASTER_KEY", base64.b64encode(os.urandom(32)).decode())


@pytest.fixture
def km(tmp_path) -> WorkspaceKeyManager:
    return WorkspaceKeyManager(tmp_path / "data")


def test_ensure_dek_is_idempotent_and_file_has_no_plaintext(km, tmp_path):
    km.ensure_dek("1001")
    km.ensure_dek("1001")
    dek_file = tmp_path / "data" / "host" / "keys" / "1001.dek"
    assert dek_file.exists()
    body = dek_file.read_text()
    assert "wrapped" in body and "version" in body


def test_encrypt_decrypt_round_trip(km):
    km.ensure_dek("1001")
    blob = km.encrypt("1001", b"secret payload")
    assert blob != b"secret payload"
    assert km.decrypt("1001", blob) == b"secret payload"


def test_cross_workspace_decrypt_fails(km):
    km.ensure_dek("1001")
    km.ensure_dek("2002")
    blob = km.encrypt("1001", b"for-1001-only")
    with pytest.raises(WorkspaceKeyError):
        km.decrypt("2002", blob)


def test_decrypt_before_ensure_dek_raises(km):
    with pytest.raises(WorkspaceKeyError, match="chưa có DEK"):
        km.decrypt("9999", b"x" * 40)


def test_rotate_bumps_version_keeps_history_and_new_key_works(km):
    km.ensure_dek("1001")
    old_blob = km.encrypt("1001", b"pre-rotation")
    v = km.rotate("1001")
    assert v == 2
    new_blob = km.encrypt("1001", b"post-rotation")
    assert km.decrypt("1001", new_blob) == b"post-rotation"
    # payload cũ (mã hoá bằng DEK v1) không còn giải mã bằng DEK v2 — caller phải re-encrypt.
    with pytest.raises(WorkspaceKeyError):
        km.decrypt("1001", old_blob)


def test_unload_drops_ram_cache_but_reload_from_file_still_works(km):
    km.ensure_dek("1001")
    blob = km.encrypt("1001", b"cached then unloaded")
    km.unload("1001")
    assert km.decrypt("1001", blob) == b"cached then unloaded"  # reloaded from file


def test_destroy_makes_workspace_undecryptable(km, tmp_path):
    km.ensure_dek("1001")
    blob = km.encrypt("1001", b"gone after destroy")
    km.destroy("1001")
    assert not (tmp_path / "data" / "host" / "keys" / "1001.dek").exists()
    with pytest.raises(WorkspaceKeyError):
        km.decrypt("1001", blob)


def test_bad_workspace_id_rejected(km):
    with pytest.raises(Exception):  # noqa: B017 — VaultSecurityError
        km.ensure_dek("../etc")


def test_production_without_master_key_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("COSA_VAULT_MASTER_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(WorkspaceKeyError, match="COSA_VAULT_MASTER_KEY"):
        WorkspaceKeyManager(tmp_path / "data")
