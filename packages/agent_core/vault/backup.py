"""Per-workspace backup / export / restore — M3 §9.

Một backup package (`<workspace_id>-<ts>.cosa-backup.tar.gz`) chứa:
- `backup-manifest.json`: schema version, workspace id, slug, thời điểm, bản sao
  `manifest.json` nguồn, checksum sha256 từng file, và **wrapped DEK** (envelope-
  encrypt bởi master key — không phải plaintext).
- `data/…`: các cây con của workspace (`vault/`, `knowledge/`, `sync/checkpoints/`).

Bất biến (audit §10.3):
- Export/restore một workspace KHÔNG đọc/list/ghi workspace khác — mọi path khi
  giải nén phải nằm trong `workspaces/<target_id>/`.
- Restore cùng ID: phát hiện collision (đã có dữ liệu) trừ khi `overwrite=True`.
- Clone: bắt buộc `new_workspace_id` khác ID gốc; tạo Snowflake ID mới do caller
  cấp, rewrite `workspace_id` trong manifest đích.
- File bị sửa trong archive ⇒ sha256 lệch ⇒ `VaultSecurityError`.
- Không import `services/*`.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agent_core.vault.host_catalog import HostCatalog, WorkspaceCatalogEntry
from agent_core.vault.keys import WorkspaceKeyError, WorkspaceKeyManager
from agent_core.vault.object_store import VaultSecurityError, _check_segment, _is_relative_to

__all__ = ["BackupManifest", "WorkspaceBackup"]

BACKUP_SCHEMA_VERSION = 1

# Cây con được đưa vào backup — bỏ transient (`temp/`, `quarantine/`, sync outbox/inbox).
_BACKED_UP_SUBTREES: tuple[str, ...] = (
    "vault",
    "knowledge",
    "sync/checkpoints",
)


@dataclass
class BackupManifest:
    schema_version: int
    workspace_id: str
    slug: str | None
    created_at: str
    files: dict[str, str]  # relpath (dưới data/) -> sha256
    key_wrapped: str
    source_manifest: dict

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "workspace_id": self.workspace_id,
            "slug": self.slug,
            "created_at": self.created_at,
            "files": self.files,
            "key_wrapped": self.key_wrapped,
            "source_manifest": self.source_manifest,
        }

    @classmethod
    def from_dict(cls, d: dict) -> BackupManifest:
        return cls(
            schema_version=d["schema_version"],
            workspace_id=d["workspace_id"],
            slug=d.get("slug"),
            created_at=d.get("created_at", ""),
            files=d.get("files", {}),
            key_wrapped=d["key_wrapped"],
            source_manifest=d.get("source_manifest", {}),
        )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class WorkspaceBackup:
    def __init__(self, catalog: HostCatalog, keys: WorkspaceKeyManager) -> None:
        self._catalog = catalog
        self._keys = keys

    # --- export -----------------------------------------------------------

    def export_workspace(self, workspace_id: str, dest_dir: str | os.PathLike[str]) -> Path:
        _check_segment(workspace_id, field="workspace_id")
        entry = self._catalog.get_workspace(workspace_id)
        if entry is None:
            raise VaultSecurityError(f"workspace {workspace_id} chưa được register")
        ws_root = self._catalog.workspace_root(workspace_id)

        # Thu thập file + checksum. relpath luôn tương đối so với ws_root.
        files: dict[str, str] = {}
        members: list[tuple[str, bytes]] = []
        for subtree in _BACKED_UP_SUBTREES:
            base = ws_root / subtree
            if not base.exists():
                continue
            for path in sorted(base.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(ws_root).as_posix()
                blob = path.read_bytes()
                files[rel] = _sha256(blob)
                members.append((f"data/{rel}", blob))

        manifest = BackupManifest(
            schema_version=BACKUP_SCHEMA_VERSION,
            workspace_id=workspace_id,
            slug=entry.slug,
            created_at=datetime.now(UTC).isoformat(),
            files=files,
            key_wrapped=self._keys.export_wrapped_dek(workspace_id),
            source_manifest=self._catalog.read_manifest(workspace_id).to_dict(),
        )

        dest_dir_p = Path(dest_dir)
        dest_dir_p.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        pkg = dest_dir_p / f"{workspace_id}-{ts}.cosa-backup.tar.gz"

        with tarfile.open(pkg, "w:gz") as tar:
            self._add_bytes(
                tar, "backup-manifest.json", json.dumps(manifest.to_dict(), indent=2).encode()
            )
            for name, blob in members:
                self._add_bytes(tar, name, blob)
        return pkg

    @staticmethod
    def _add_bytes(tar: tarfile.TarFile, name: str, blob: bytes) -> None:
        info = tarfile.TarInfo(name=name)
        info.size = len(blob)
        info.mtime = 0
        info.mode = 0o600
        tar.addfile(info, io.BytesIO(blob))

    # --- inspect --------------------------------------------------------

    def inspect(self, package_path: str | os.PathLike[str]) -> BackupManifest:
        with tarfile.open(package_path, "r:*") as tar:
            return BackupManifest.from_dict(
                json.loads(self._read_member(tar, "backup-manifest.json"))
            )

    @staticmethod
    def _read_member(tar: tarfile.TarFile, name: str) -> bytes:
        try:
            f = tar.extractfile(name)
        except KeyError:
            f = None
        if f is None:
            raise VaultSecurityError(f"backup thiếu member {name!r}")
        return f.read()

    # --- restore -------------------------------------------------------

    def restore_workspace(
        self,
        package_path: str | os.PathLike[str],
        *,
        mode: str = "same",
        new_workspace_id: str | None = None,
        overwrite: bool = False,
    ) -> WorkspaceCatalogEntry:
        if mode not in ("same", "clone"):
            raise VaultSecurityError("mode phải là 'same' hoặc 'clone'")

        with tarfile.open(package_path, "r:*") as tar:
            manifest = BackupManifest.from_dict(
                json.loads(self._read_member(tar, "backup-manifest.json"))
            )
            if mode == "same":
                target_id = manifest.workspace_id
            else:
                if not new_workspace_id or new_workspace_id == manifest.workspace_id:
                    raise VaultSecurityError("clone bắt buộc new_workspace_id khác ID gốc")
                target_id = new_workspace_id
            _check_segment(target_id, field="target_workspace_id")

            target_root = self._catalog.workspace_root(target_id).resolve()

            # collision: đã có dữ liệu vault ở target và không cho overwrite.
            if not overwrite and (target_root / "vault").exists():
                has_content = any(p.is_file() for p in (target_root / "vault").rglob("*"))
                if has_content:
                    raise VaultSecurityError(
                        f"workspace {target_id} đã có dữ liệu — restore cần overwrite=True"
                    )

            self._catalog.register_workspace(target_id, slug=manifest.slug)

            # DEK: clone/restore mới thì import wrapped; đã có DEK thì giữ nguyên
            # (restore đè lên workspace đang sống — không ghi đè key đang dùng).
            with contextlib.suppress(WorkspaceKeyError):
                self._keys.import_wrapped_dek(target_id, manifest.key_wrapped)

            # Giải nén từng file: sanitize path, chặn traversal, verify sha256.
            for member in tar.getmembers():
                if member.name == "backup-manifest.json":
                    continue
                if not member.isfile():
                    raise VaultSecurityError(f"member không phải file thường: {member.name!r}")
                if not member.name.startswith("data/"):
                    raise VaultSecurityError(f"member ngoài data/: {member.name!r}")
                rel = member.name[len("data/") :]
                if not rel or rel.startswith("/") or ".." in Path(rel).parts:
                    raise VaultSecurityError(f"path traversal trong backup: {member.name!r}")
                dest = (target_root / rel).resolve()
                if not _is_relative_to(dest, target_root):
                    raise VaultSecurityError(f"member thoát khỏi workspace root: {member.name!r}")

                extracted = tar.extractfile(member)
                blob = extracted.read() if extracted else b""
                expected = manifest.files.get(rel)
                if expected is None:
                    raise VaultSecurityError(f"file không có trong manifest: {rel!r}")
                if _sha256(blob) != expected:
                    raise VaultSecurityError(f"checksum lệch — backup có thể bị sửa: {rel!r}")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(blob)

        entry = self._catalog.get_workspace(target_id)
        assert entry is not None  # register_workspace vừa tạo
        return entry
