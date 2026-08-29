"""M3 §6 — per-workspace storage quota (tách trục, độc lập giữa workspace)."""

from __future__ import annotations

import pytest
from agent.vault import (
    HostCatalog,
    QuotaExceededError,
    VaultSecurityError,
    WorkspaceStorageQuota,
)


@pytest.fixture
def catalog(tmp_path) -> HostCatalog:
    return HostCatalog(tmp_path / "data")


@pytest.fixture
def quota(catalog) -> WorkspaceStorageQuota:
    return WorkspaceStorageQuota(catalog, default_limit_bytes=1000)


def _write(catalog, wid: str, rel: str, size: int) -> None:
    p = catalog.workspace_root(wid) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x" * size)


def test_usage_counts_vault_tree_excludes_temp(catalog, quota):
    catalog.register_workspace("1001")
    _write(catalog, "1001", "vault/documents/d1.bin", 300)
    _write(catalog, "1001", "knowledge/snapshots/s1.bin", 100)
    _write(catalog, "1001", "temp/scratch.bin", 999)  # không tính
    assert quota.usage_bytes("1001") == 400


def test_check_allows_within_limit_and_blocks_over(catalog, quota):
    catalog.register_workspace("1001")
    _write(catalog, "1001", "vault/documents/d1.bin", 800)
    assert quota.check("1001", 200).allowed is True
    over = quota.check("1001", 201)
    assert over.allowed is False
    assert "vượt hạn mức" in over.reason


def test_assert_within_raises_when_over(catalog, quota):
    catalog.register_workspace("1001")
    _write(catalog, "1001", "vault/documents/d1.bin", 950)
    with pytest.raises(QuotaExceededError):
        quota.assert_within("1001", 100)


def test_quota_is_independent_per_workspace(catalog, quota):
    catalog.register_workspace("1001")
    catalog.register_workspace("2002")
    _write(catalog, "1001", "vault/documents/big.bin", 1000)  # A đầy
    # A vượt hạn nhưng B vẫn ghi được.
    with pytest.raises(QuotaExceededError):
        quota.assert_within("1001", 1)
    assert quota.assert_within("2002", 500).allowed is True


def test_set_limit_overrides_default_and_persists(catalog, tmp_path):
    q = WorkspaceStorageQuota(catalog, default_limit_bytes=1000)
    catalog.register_workspace("1001")
    q.set_limit("1001", 10)
    _write(catalog, "1001", "vault/documents/d1.bin", 20)
    assert q.check("1001", 0).allowed is False  # đã vượt limit 10
    # instance mới đọc lại limit từ file.
    q2 = WorkspaceStorageQuota(catalog, default_limit_bytes=1000)
    assert q2.limit_for("1001") == 10


def test_bad_workspace_id_rejected(quota):
    with pytest.raises(VaultSecurityError):
        quota.check("../etc", 1)


def test_negative_incoming_rejected(catalog, quota):
    catalog.register_workspace("1001")
    with pytest.raises(VaultSecurityError):
        quota.check("1001", -5)


def test_usage_zero_for_unregistered_workspace(quota):
    assert quota.usage_bytes("9999") == 0
