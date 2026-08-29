"""WorkspaceObjectStore — M3 §2/§3/§6.9.

Key layout chuẩn (không đổi giữa local / S3):
    workspaces/<workspace_id>/<kind>/<object_id>/versions/<version_id>/<blob>

Bất biến an toàn (audit §6.9):
- KHÔNG nhận raw absolute path từ caller.
- Canonicalize path; chặn `..`, symlink/hardlink escape ra ngoài workspace root.
- Chặn case-fold collision (Foo vs foo trong cùng thư mục).
- Mọi object metadata chứa `workspace_id` + checksum sha256.
- get/archive/delete bind `(workspace_id, object_id)` — sai workspace ⇒ không tới được blob.
- KHÔNG dedup blob xuyên workspace.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

__all__ = [
    "LocalFilesystemWorkspaceStore",
    "ObjectRef",
    "VaultSecurityError",
    "WorkspaceObjectStore",
]

# Segment (workspace_id / kind / object_id / version_id / blob name) chỉ cho phép
# ký tự an toàn cho path — không `/`, `\`, `..`, null, khoảng trắng đầu/cuối, `.`.
_ALLOWED_SEGMENT = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_MAX_SEGMENT_LEN = 200


class VaultSecurityError(Exception):
    """Vi phạm bất biến an toàn của Vault (path traversal, cross-workspace, …)."""


def _check_segment(name: str, *, field: str) -> str:
    if not name or not isinstance(name, str):
        raise VaultSecurityError(f"{field} rỗng/không hợp lệ")
    if name in (".", ".."):
        raise VaultSecurityError(f"{field} không được là '.' hoặc '..'")
    if len(name) > _MAX_SEGMENT_LEN:
        raise VaultSecurityError(f"{field} quá dài")
    if name.strip() != name:
        raise VaultSecurityError(f"{field} có khoảng trắng đầu/cuối")
    if name.startswith("."):
        raise VaultSecurityError(f"{field} không được bắt đầu bằng '.'")
    bad = set(name) - _ALLOWED_SEGMENT
    if bad:
        raise VaultSecurityError(f"{field} chứa ký tự không cho phép: {''.join(sorted(bad))!r}")
    if "\x00" in name:
        raise VaultSecurityError(f"{field} chứa null byte")
    return name


@dataclass(frozen=True)
class ObjectRef:
    """Tham chiếu chuẩn tới một version của object trong Vault."""

    workspace_id: str
    kind: str
    object_id: str
    version_id: str
    blob_name: str = "blob"
    checksum_sha256: str | None = None

    def key(self) -> str:
        return (
            f"workspaces/{self.workspace_id}/{self.kind}/{self.object_id}"
            f"/versions/{self.version_id}/{self.blob_name}"
        )


class WorkspaceObjectStore(ABC):
    """Business code không ghép raw path — chỉ đi qua interface này."""

    @abstractmethod
    def put(
        self,
        workspace_id: str,
        object_kind: str,
        object_id: str,
        version_id: str,
        data: bytes,
        *,
        blob_name: str = "blob",
    ) -> ObjectRef: ...

    @abstractmethod
    def get(self, workspace_id: str, ref: ObjectRef) -> bytes: ...

    @abstractmethod
    def archive(self, workspace_id: str, ref: ObjectRef) -> None: ...

    @abstractmethod
    def delete_after_retention(self, workspace_id: str, ref: ObjectRef) -> None: ...

    @abstractmethod
    def list_versions(self, workspace_id: str, object_kind: str, object_id: str) -> list[str]: ...


class LocalFilesystemWorkspaceStore(WorkspaceObjectStore):
    """Managed local directory. `data_root` là gốc do host quản lý (COSA_DATA_ROOT)."""

    def __init__(self, data_root: str | os.PathLike[str]) -> None:
        self._root = Path(data_root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    # --- path resolution an toàn ------------------------------------------------

    def _workspace_root(self, workspace_id: str) -> Path:
        _check_segment(workspace_id, field="workspace_id")
        return self._root / "workspaces" / workspace_id

    def _resolve_within(self, workspace_id: str, *segments: str) -> Path:
        ws_root = self._workspace_root(workspace_id)
        target = ws_root
        for seg in segments:
            target = target / seg
        # Canonicalize (theo cả symlink) rồi khẳng định vẫn nằm trong ws_root.
        ws_root_real = ws_root.resolve() if ws_root.exists() else ws_root
        try:
            target_real = target.resolve()
        except (OSError, RuntimeError) as exc:  # symlink loop, …
            raise VaultSecurityError(f"không resolve được path: {exc}") from exc
        if not _is_relative_to(target_real, self._root):
            raise VaultSecurityError("path thoát khỏi data root")
        if not _is_relative_to(
            target_real,
            ws_root_real if ws_root_real.exists() else self._root / "workspaces" / workspace_id,
        ):
            raise VaultSecurityError("path thoát khỏi workspace root (traversal/symlink)")
        return target

    def _version_dir(self, ref: ObjectRef) -> Path:
        _check_segment(ref.kind, field="object_kind")
        _check_segment(ref.object_id, field="object_id")
        _check_segment(ref.version_id, field="version_id")
        _check_segment(ref.blob_name, field="blob_name")
        return self._resolve_within(
            ref.workspace_id,
            ref.kind,
            ref.object_id,
            "versions",
            ref.version_id,
        )

    def _assert_no_casefold_sibling(self, parent: Path, name: str) -> None:
        if not parent.exists():
            return
        lowered = name.casefold()
        for existing in parent.iterdir():
            if existing.name != name and existing.name.casefold() == lowered:
                raise VaultSecurityError(f"case-fold collision: {name!r} đụng {existing.name!r}")

    # --- API -----------------------------------------------------------------

    def put(
        self,
        workspace_id: str,
        object_kind: str,
        object_id: str,
        version_id: str,
        data: bytes,
        *,
        blob_name: str = "blob",
    ) -> ObjectRef:
        if not isinstance(data, (bytes, bytearray)):
            raise VaultSecurityError("data phải là bytes")
        checksum = hashlib.sha256(bytes(data)).hexdigest()
        ref = ObjectRef(
            workspace_id=workspace_id,
            kind=_check_segment(object_kind, field="object_kind"),
            object_id=_check_segment(object_id, field="object_id"),
            version_id=_check_segment(version_id, field="version_id"),
            blob_name=_check_segment(blob_name, field="blob_name"),
            checksum_sha256=checksum,
        )
        vdir = self._version_dir(ref)

        # case-fold collision check ở mọi mức thư mục con của workspace.
        kind_dir = self._resolve_within(workspace_id, ref.kind)
        self._assert_no_casefold_sibling(kind_dir, ref.object_id)
        obj_dir = self._resolve_within(workspace_id, ref.kind, ref.object_id)
        self._assert_no_casefold_sibling(obj_dir / "versions", ref.version_id)

        vdir.mkdir(parents=True, exist_ok=True)
        self._assert_no_casefold_sibling(vdir, ref.blob_name)
        (vdir / ref.blob_name).write_bytes(bytes(data))
        (vdir / "meta.json").write_text(
            json.dumps(
                {
                    "workspace_id": workspace_id,
                    "kind": ref.kind,
                    "object_id": ref.object_id,
                    "version_id": ref.version_id,
                    "blob_name": ref.blob_name,
                    "checksum_sha256": checksum,
                    "size_bytes": len(data),
                    "created_at": datetime.now(UTC).isoformat(),
                    "status": "active",
                },
                indent=2,
            )
        )
        return ref

    def _load_meta(self, vdir: Path) -> dict:
        meta_path = vdir / "meta.json"
        if not meta_path.exists():
            raise VaultSecurityError("object không tồn tại (thiếu meta)")
        return json.loads(meta_path.read_text())

    def get(self, workspace_id: str, ref: ObjectRef) -> bytes:
        if ref.workspace_id != workspace_id:
            # bind (workspace_id, object) — không cho đọc object của workspace khác.
            raise VaultSecurityError("workspace_id không khớp object ref")
        vdir = self._version_dir(ref)
        meta = self._load_meta(vdir)
        if meta.get("workspace_id") != workspace_id:
            raise VaultSecurityError("metadata workspace_id không khớp")
        blob = vdir / ref.blob_name
        if not blob.exists():
            raise VaultSecurityError("blob không tồn tại")
        data = blob.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if meta.get("checksum_sha256") and actual != meta["checksum_sha256"]:
            raise VaultSecurityError("checksum không khớp — blob có thể đã bị sửa")
        return data

    def archive(self, workspace_id: str, ref: ObjectRef) -> None:
        if ref.workspace_id != workspace_id:
            raise VaultSecurityError("workspace_id không khớp object ref")
        vdir = self._version_dir(ref)
        meta = self._load_meta(vdir)
        meta["status"] = "archived"
        meta["archived_at"] = datetime.now(UTC).isoformat()
        (vdir / "meta.json").write_text(json.dumps(meta, indent=2))

    def delete_after_retention(self, workspace_id: str, ref: ObjectRef) -> None:
        if ref.workspace_id != workspace_id:
            raise VaultSecurityError("workspace_id không khớp object ref")
        vdir = self._version_dir(ref)
        if not vdir.exists():
            return
        self._load_meta(vdir)  # xác nhận là version dir hợp lệ trước khi rmtree
        shutil.rmtree(vdir)

    def list_versions(self, workspace_id: str, object_kind: str, object_id: str) -> list[str]:
        _check_segment(object_kind, field="object_kind")
        _check_segment(object_id, field="object_id")
        versions_dir = self._resolve_within(workspace_id, object_kind, object_id, "versions")
        if not versions_dir.exists():
            return []
        return sorted(p.name for p in versions_dir.iterdir() if p.is_dir())


def _is_relative_to(path: Path, root: Path) -> bool:
    # Path.is_relative_to có từ 3.9 nhưng vẫn tự cài để chắc chắn.
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
