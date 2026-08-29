"""Runtime Host Catalog + per-workspace Vault manifest — M3 §1.

Layout (audit §6.2):

    <COSA_DATA_ROOT>/
      host/
        catalog/workspaces.json          # registry: workspace nào tồn tại, path root, runtime/sync mode
        keys/<workspace_id>.dek          # (WorkspaceKeyManager — không thuộc file này)
        runtime-node/ logs/
      workspaces/<workspace_id>/
        manifest.json                    # metadata KHÔNG bí mật: schema version, workspace id, key *ref*
        vault/{documents,sops,attachments,artifacts}/
        knowledge/{snapshots,indexes}/
        quarantine/ exports/ temp/
        sync/{outbox,inbox,conflicts,checkpoints}/
        backup/

Bất biến:
- `manifest.json` KHÔNG bao giờ chứa plaintext workspace key/token — chỉ `key_ref`
  (đường dẫn tương đối tới file DEK do `WorkspaceKeyManager` quản lý).
- Host catalog là nguồn sự thật cho "workspace nào tồn tại trên host này" — mỗi
  workspace có runtime/sync mode độc lập.
- Không import `services/*`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from agent_core.vault.object_store import VaultSecurityError, _check_segment

__all__ = [
    "HostCatalog",
    "WorkspaceCatalogEntry",
    "WorkspaceManifest",
]

# Bump khi cấu trúc cây thư mục / manifest thay đổi không tương thích.
MANIFEST_SCHEMA_VERSION = 1

RuntimeMode = Literal["local", "cloud", "hybrid"]
SyncMode = Literal["off", "outbox", "bidirectional"]

# Cây thư mục con cố định của một workspace (tạo sẵn để business code không phải mkdir ad-hoc).
_WORKSPACE_SUBDIRS: tuple[str, ...] = (
    "vault/documents",
    "vault/sops",
    "vault/attachments",
    "vault/artifacts",
    "knowledge/snapshots",
    "knowledge/indexes",
    "quarantine",
    "exports",
    "temp",
    "sync/outbox",
    "sync/inbox",
    "sync/conflicts",
    "sync/checkpoints",
    "backup",
)


@dataclass
class WorkspaceCatalogEntry:
    workspace_id: str
    root: str  # đường dẫn tuyệt đối tới workspaces/<id>
    runtime_mode: RuntimeMode = "local"
    sync_mode: SyncMode = "off"
    slug: str | None = None
    registered_at: str = ""

    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "root": self.root,
            "runtime_mode": self.runtime_mode,
            "sync_mode": self.sync_mode,
            "slug": self.slug,
            "registered_at": self.registered_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> WorkspaceCatalogEntry:
        return cls(
            workspace_id=d["workspace_id"],
            root=d["root"],
            runtime_mode=d.get("runtime_mode", "local"),
            sync_mode=d.get("sync_mode", "off"),
            slug=d.get("slug"),
            registered_at=d.get("registered_at", ""),
        )


@dataclass
class WorkspaceManifest:
    workspace_id: str
    schema_version: int = MANIFEST_SCHEMA_VERSION
    created_at: str = ""
    key_ref: str = ""  # đường dẫn TƯƠNG ĐỐI tới file DEK — KHÔNG phải key
    slug: str | None = None
    subdirs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "key_ref": self.key_ref,
            "slug": self.slug,
            "subdirs": self.subdirs,
        }

    @classmethod
    def from_dict(cls, d: dict) -> WorkspaceManifest:
        return cls(
            workspace_id=d["workspace_id"],
            schema_version=d.get("schema_version", 0),
            created_at=d.get("created_at", ""),
            key_ref=d.get("key_ref", ""),
            slug=d.get("slug"),
            subdirs=d.get("subdirs", []),
        )


# Chuỗi có khả năng là bí mật — nếu xuất hiện trong manifest thì coi là rò rỉ.
_SECRET_MANIFEST_KEYS = {"key", "dek", "secret", "token", "password", "passphrase", "private_key"}


class HostCatalog:
    """Quản lý `host/catalog/workspaces.json` + cây thư mục per-workspace + manifest."""

    def __init__(self, data_root: str | os.PathLike[str]) -> None:
        self._root = Path(data_root).resolve()
        self._catalog_dir = self._root / "host" / "catalog"
        self._catalog_dir.mkdir(parents=True, exist_ok=True)
        (self._root / "host" / "runtime-node").mkdir(parents=True, exist_ok=True)
        (self._root / "host" / "logs").mkdir(parents=True, exist_ok=True)
        self._catalog_file = self._catalog_dir / "workspaces.json"

    # --- catalog I/O ---------------------------------------------------------

    def _read_catalog(self) -> dict[str, WorkspaceCatalogEntry]:
        if not self._catalog_file.exists():
            return {}
        raw = json.loads(self._catalog_file.read_text())
        return {
            wid: WorkspaceCatalogEntry.from_dict(entry)
            for wid, entry in raw.get("workspaces", {}).items()
        }

    def _write_catalog(self, entries: dict[str, WorkspaceCatalogEntry]) -> None:
        payload = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "updated_at": datetime.now(UTC).isoformat(),
            "workspaces": {wid: e.to_dict() for wid, e in sorted(entries.items())},
        }
        tmp = self._catalog_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(self._catalog_file)

    # --- workspace paths --------------------------------------------------

    def workspace_root(self, workspace_id: str) -> Path:
        _check_segment(workspace_id, field="workspace_id")
        return self._root / "workspaces" / workspace_id

    def manifest_path(self, workspace_id: str) -> Path:
        return self.workspace_root(workspace_id) / "manifest.json"

    # --- public API ----------------------------------------------------

    def register_workspace(
        self,
        workspace_id: str,
        *,
        slug: str | None = None,
        runtime_mode: RuntimeMode = "local",
        sync_mode: SyncMode = "off",
    ) -> WorkspaceCatalogEntry:
        """Tạo cây thư mục + manifest + catalog entry. Idempotent — gọi lại chỉ
        cập nhật mode/slug, không ghi đè manifest đã có."""
        _check_segment(workspace_id, field="workspace_id")
        ws_root = self.workspace_root(workspace_id)
        for sub in _WORKSPACE_SUBDIRS:
            (ws_root / sub).mkdir(parents=True, exist_ok=True)

        manifest_path = self.manifest_path(workspace_id)
        if not manifest_path.exists():
            manifest = WorkspaceManifest(
                workspace_id=workspace_id,
                created_at=datetime.now(UTC).isoformat(),
                key_ref=f"host/keys/{workspace_id}.dek",
                slug=slug,
                subdirs=list(_WORKSPACE_SUBDIRS),
            )
            self._write_manifest(manifest_path, manifest)

        entries = self._read_catalog()
        existing = entries.get(workspace_id)
        entry = WorkspaceCatalogEntry(
            workspace_id=workspace_id,
            root=str(ws_root),
            runtime_mode=runtime_mode,
            sync_mode=sync_mode,
            slug=slug if slug is not None else (existing.slug if existing else None),
            registered_at=existing.registered_at if existing else datetime.now(UTC).isoformat(),
        )
        entries[workspace_id] = entry
        self._write_catalog(entries)
        return entry

    def _write_manifest(self, path: Path, manifest: WorkspaceManifest) -> None:
        d = manifest.to_dict()
        self._assert_no_secret(d)
        path.write_text(json.dumps(d, indent=2))

    @staticmethod
    def _assert_no_secret(manifest_dict: dict) -> None:
        for k in manifest_dict:
            if k.lower() in _SECRET_MANIFEST_KEYS:
                raise VaultSecurityError(
                    f"manifest không được chứa field bí mật {k!r} — chỉ key_ref"
                )

    def read_manifest(self, workspace_id: str) -> WorkspaceManifest:
        path = self.manifest_path(workspace_id)
        if not path.exists():
            raise VaultSecurityError(
                f"workspace {workspace_id} chưa được register (thiếu manifest)"
            )
        return WorkspaceManifest.from_dict(json.loads(path.read_text()))

    def get_workspace(self, workspace_id: str) -> WorkspaceCatalogEntry | None:
        return self._read_catalog().get(workspace_id)

    def list_workspaces(self) -> list[WorkspaceCatalogEntry]:
        return list(self._read_catalog().values())

    def set_modes(
        self,
        workspace_id: str,
        *,
        runtime_mode: RuntimeMode | None = None,
        sync_mode: SyncMode | None = None,
    ) -> WorkspaceCatalogEntry:
        entries = self._read_catalog()
        entry = entries.get(workspace_id)
        if entry is None:
            raise VaultSecurityError(f"workspace {workspace_id} chưa được register")
        if runtime_mode is not None:
            entry.runtime_mode = runtime_mode
        if sync_mode is not None:
            entry.sync_mode = sync_mode
        entries[workspace_id] = entry
        self._write_catalog(entries)
        return entry

    def deregister_workspace(self, workspace_id: str) -> None:
        """Bỏ workspace khỏi catalog. KHÔNG xoá file — dùng backup/purge riêng."""
        entries = self._read_catalog()
        if entries.pop(workspace_id, None) is not None:
            self._write_catalog(entries)
