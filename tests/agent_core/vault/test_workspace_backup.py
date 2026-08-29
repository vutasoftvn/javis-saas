"""M3 §9 — per-workspace backup / export / restore + cross-workspace isolation."""

from __future__ import annotations

import base64
import json
import os
import tarfile

import pytest
from agent_core.vault import (
    HostCatalog,
    VaultSecurityError,
    WorkspaceBackup,
    WorkspaceKeyManager,
)


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("COSA_VAULT_MASTER_KEY", base64.b64encode(os.urandom(32)).decode())


@pytest.fixture
def data_root(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def catalog(data_root) -> HostCatalog:
    return HostCatalog(data_root)


@pytest.fixture
def keys(data_root) -> WorkspaceKeyManager:
    return WorkspaceKeyManager(data_root)


@pytest.fixture
def backup(catalog, keys) -> WorkspaceBackup:
    return WorkspaceBackup(catalog, keys)


def _seed_workspace(catalog, keys, data_root, wid: str, *, doc_body: bytes) -> None:
    catalog.register_workspace(wid, slug=f"ws-{wid}")
    keys.ensure_dek(wid)
    doc = data_root / "workspaces" / wid / "vault" / "documents" / "d1.bin"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_bytes(doc_body)
    (data_root / "workspaces" / wid / "sync" / "checkpoints" / "cursor.json").write_text(
        json.dumps({"seq": 7})
    )


def test_export_then_restore_clone_round_trip(backup, catalog, keys, data_root, tmp_path):
    _seed_workspace(catalog, keys, data_root, "1001", doc_body=b"hello-1001")
    pkg = backup.export_workspace("1001", tmp_path / "out")
    assert pkg.exists()

    entry = backup.restore_workspace(pkg, mode="clone", new_workspace_id="3003")
    assert entry.workspace_id == "3003"
    restored = data_root / "workspaces" / "3003" / "vault" / "documents" / "d1.bin"
    assert restored.read_bytes() == b"hello-1001"
    assert (data_root / "workspaces" / "3003" / "sync" / "checkpoints" / "cursor.json").exists()
    # DEK cho clone import được ⇒ decrypt hoạt động.
    blob = keys.encrypt("3003", b"x")
    assert keys.decrypt("3003", blob) == b"x"


def test_export_of_A_contains_no_B_data(backup, catalog, keys, data_root, tmp_path):
    _seed_workspace(catalog, keys, data_root, "1001", doc_body=b"secret-A")
    _seed_workspace(catalog, keys, data_root, "2002", doc_body=b"secret-B")
    pkg = backup.export_workspace("1001", tmp_path / "out")

    with tarfile.open(pkg, "r:*") as tar:
        names = tar.getnames()
        blob = b"".join(tar.extractfile(m).read() for m in tar.getmembers() if m.isfile())
    assert not any("2002" in n for n in names)
    assert b"secret-B" not in blob

    manifest = backup.inspect(pkg)
    assert manifest.workspace_id == "1001"
    assert all("2002" not in rel for rel in manifest.files)


def test_restore_clone_does_not_mutate_original(backup, catalog, keys, data_root, tmp_path):
    _seed_workspace(catalog, keys, data_root, "1001", doc_body=b"original-bytes")
    orig = data_root / "workspaces" / "1001" / "vault" / "documents" / "d1.bin"
    before = orig.read_bytes()
    pkg = backup.export_workspace("1001", tmp_path / "out")
    backup.restore_workspace(pkg, mode="clone", new_workspace_id="3003")
    assert orig.read_bytes() == before  # workspace gốc không bị đụng


def test_tampered_archive_fails_checksum(backup, catalog, keys, data_root, tmp_path):
    _seed_workspace(catalog, keys, data_root, "1001", doc_body=b"clean")
    pkg = backup.export_workspace("1001", tmp_path / "out")

    # Dựng lại archive với 1 file bị sửa nhưng manifest giữ nguyên checksum cũ.
    tampered = tmp_path / "tampered.tar.gz"
    with tarfile.open(pkg, "r:*") as src, tarfile.open(tampered, "w:gz") as dst:
        for m in src.getmembers():
            data = src.extractfile(m).read()
            if m.name.endswith("d1.bin"):
                data = b"TAMPERED"
            m.size = len(data)
            import io

            dst.addfile(m, io.BytesIO(data))

    with pytest.raises(VaultSecurityError, match="checksum"):
        backup.restore_workspace(tampered, mode="clone", new_workspace_id="3003")


def test_path_traversal_member_rejected(backup, catalog, keys, data_root, tmp_path):
    _seed_workspace(catalog, keys, data_root, "1001", doc_body=b"clean")
    pkg = backup.export_workspace("1001", tmp_path / "out")
    evil = tmp_path / "evil.tar.gz"
    with tarfile.open(pkg, "r:*") as src, tarfile.open(evil, "w:gz") as dst:
        for m in src.getmembers():
            dst.addfile(m, src.extractfile(m) if m.isfile() else None)
        import io

        payload = b"pwned"
        info = tarfile.TarInfo(name="data/../../escape.bin")
        info.size = len(payload)
        dst.addfile(info, io.BytesIO(payload))

    with pytest.raises(VaultSecurityError):
        backup.restore_workspace(evil, mode="clone", new_workspace_id="3003")
    assert not (tmp_path / "escape.bin").exists()


def test_same_id_restore_collision_without_overwrite(backup, catalog, keys, data_root, tmp_path):
    _seed_workspace(catalog, keys, data_root, "1001", doc_body=b"live-data")
    pkg = backup.export_workspace("1001", tmp_path / "out")
    with pytest.raises(VaultSecurityError, match="overwrite"):
        backup.restore_workspace(pkg, mode="same")
    # overwrite=True cho phép.
    entry = backup.restore_workspace(pkg, mode="same", overwrite=True)
    assert entry.workspace_id == "1001"


def test_clone_requires_distinct_new_id(backup, catalog, keys, data_root, tmp_path):
    _seed_workspace(catalog, keys, data_root, "1001", doc_body=b"x")
    pkg = backup.export_workspace("1001", tmp_path / "out")
    with pytest.raises(VaultSecurityError, match="new_workspace_id"):
        backup.restore_workspace(pkg, mode="clone", new_workspace_id="1001")
    with pytest.raises(VaultSecurityError, match="new_workspace_id"):
        backup.restore_workspace(pkg, mode="clone")


def test_export_unregistered_workspace_raises(backup):
    with pytest.raises(VaultSecurityError, match="register"):
        backup.export_workspace("9999", "/tmp/whatever")
