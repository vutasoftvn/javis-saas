"""M3 §2/§3/§6.9 — WorkspaceObjectStore + negative security suite."""
from __future__ import annotations

import json
import os

import pytest
from agent_core.vault import (
    LocalFilesystemWorkspaceStore,
    ObjectRef,
    VaultSecurityError,
)


@pytest.fixture
def store(tmp_path) -> LocalFilesystemWorkspaceStore:
    return LocalFilesystemWorkspaceStore(tmp_path / "cosa-data")


def _put(store, ws="1001", kind="documents", oid="docA", ver="v1", data=b"hello"):
    return store.put(ws, kind, oid, ver, data)


# --- happy path ------------------------------------------------------------

def test_put_get_round_trip_with_checksum(store):
    ref = _put(store, data=b"content-x")
    assert ref.checksum_sha256
    assert store.get("1001", ref) == b"content-x"


def test_put_writes_meta_with_workspace_id_and_checksum(store, tmp_path):
    ref = _put(store, data=b"m")
    meta_path = tmp_path / "cosa-data" / "workspaces" / "1001" / "documents" / "docA" / "versions" / "v1" / "meta.json"
    meta = json.loads(meta_path.read_text())
    assert meta["workspace_id"] == "1001"
    assert meta["checksum_sha256"] == ref.checksum_sha256
    assert meta["size_bytes"] == 1


def test_list_versions_is_workspace_scoped(store):
    store.put("1001", "documents", "d", "v1", b"a")
    store.put("1001", "documents", "d", "v2", b"b")
    store.put("2002", "documents", "d", "v9", b"c")
    assert store.list_versions("1001", "documents", "d") == ["v1", "v2"]
    assert store.list_versions("2002", "documents", "d") == ["v9"]
    assert store.list_versions("3003", "documents", "d") == []


def test_archive_then_delete_after_retention(store):
    ref = _put(store)
    store.archive("1001", ref)
    store.delete_after_retention("1001", ref)
    with pytest.raises(VaultSecurityError):
        store.get("1001", ref)


# --- cross-workspace isolation ------------------------------------------------

def test_get_with_mismatched_workspace_id_is_rejected(store):
    ref = _put(store, ws="1001")
    # cùng blob, nhưng caller khai workspace khác
    with pytest.raises(VaultSecurityError):
        store.get("2002", ref)
    forged = ObjectRef(
        workspace_id="2002",
        kind=ref.kind,
        object_id=ref.object_id,
        version_id=ref.version_id,
        blob_name=ref.blob_name,
    )
    with pytest.raises(VaultSecurityError):
        store.get("2002", forged)


def test_two_workspaces_same_object_id_do_not_collide(store):
    a = store.put("1001", "documents", "shared", "v1", b"A-data")
    b = store.put("2002", "documents", "shared", "v1", b"B-data")
    assert store.get("1001", a) == b"A-data"
    assert store.get("2002", b) == b"B-data"


# --- path traversal / injection --------------------------------------------

@pytest.mark.parametrize(
    "bad",
    ["..", "../x", "a/b", "a\\b", "/etc/passwd", "a/../../b", ".hidden", " lead", "trail ", "", "."],
)
def test_object_id_rejects_traversal_and_separators(store, bad):
    with pytest.raises(VaultSecurityError):
        store.put("1001", "documents", bad, "v1", b"x")


@pytest.mark.parametrize("bad", ["..", "/abs", "a/b", "ws/../other"])
def test_workspace_id_rejects_traversal(store, bad):
    with pytest.raises(VaultSecurityError):
        store.put(bad, "documents", "d", "v1", b"x")


def test_kind_and_version_reject_separators(store):
    with pytest.raises(VaultSecurityError):
        store.put("1001", "docs/../secret", "d", "v1", b"x")
    with pytest.raises(VaultSecurityError):
        store.put("1001", "documents", "d", "../v1", b"x")


# --- symlink escape --------------------------------------------------------

def test_symlink_escape_is_blocked(store, tmp_path):
    _put(store)  # tạo cây workspace 1001
    outside = tmp_path / "outside_secret"
    outside.mkdir()
    (outside / "loot").write_bytes(b"top-secret")

    ws_docs = tmp_path / "cosa-data" / "workspaces" / "1001" / "documents"
    link = ws_docs / "escape"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink không được hỗ trợ ở môi trường này")

    # get qua object_id trỏ vào symlink ⇒ resolve ra ngoài workspace ⇒ chặn.
    ref = ObjectRef(
        workspace_id="1001",
        kind="documents",
        object_id="escape",
        version_id="loot",
        blob_name="blob",
    )
    with pytest.raises(VaultSecurityError):
        store.get("1001", ref)


def test_case_fold_collision_rejected(store):
    store.put("1001", "documents", "Report", "v1", b"a")
    with pytest.raises(VaultSecurityError):
        store.put("1001", "documents", "report", "v1", b"b")


def test_checksum_tamper_detected_on_get(store, tmp_path):
    ref = _put(store, data=b"original")
    blob = tmp_path / "cosa-data" / "workspaces" / "1001" / "documents" / "docA" / "versions" / "v1" / "blob"
    blob.write_bytes(b"tampered!")
    with pytest.raises(VaultSecurityError, match="checksum"):
        store.get("1001", ref)


def test_no_cross_workspace_dedup(store, tmp_path):
    # cùng nội dung, hai workspace ⇒ hai blob vật lý riêng.
    ref_a = store.put("1001", "documents", "d", "v1", b"identical")
    ref_b = store.put("2002", "documents", "d", "v1", b"identical")
    pa = tmp_path / "cosa-data" / "workspaces" / "1001" / "documents" / "d" / "versions" / "v1" / "blob"
    pb = tmp_path / "cosa-data" / "workspaces" / "2002" / "documents" / "d" / "versions" / "v1" / "blob"
    assert pa.exists() and pb.exists()
    assert not pa.samefile(pb)
    assert ref_a.checksum_sha256 == ref_b.checksum_sha256  # cùng hash, khác vị trí
