"""Per-workspace Data Encryption Key (DEK) — M3 §6.

Mô hình:
- 1 **master key** cấp thiết bị (OS Keychain/Keystore/Secure Enclave khi có; ở
  đây fallback env `COSA_VAULT_MASTER_KEY` base64 32 byte cho local/test).
- Mỗi workspace 1 **DEK** ngẫu nhiên 32 byte, được envelope-encrypt bằng master
  key rồi lưu ở `<data_root>/host/keys/<workspace_id>.dek` — file KHÔNG chứa
  plaintext DEK.
- Object/backup/sync payload mã hoá bằng DEK của đúng workspace (AES-256-GCM,
  nonce ngẫu nhiên 12 byte, prepend nonce).
- `unload(workspace_id)`: xoá DEK khỏi cache RAM khi switch workspace.
- `rotate(workspace_id)`: sinh DEK mới, ghi journal resumable (list version).
- `destroy(workspace_id)`: xoá key sau retention (dữ liệu mã hoá bằng key đó
  thành không giải mã được — đúng ý muốn khi xoá workspace).

Không phụ thuộc `services/*`. Dùng `cryptography` (đã có trong requirements).
"""

from __future__ import annotations

import base64
import json
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from agent_core.vault.object_store import _check_segment

__all__ = ["WorkspaceKeyError", "WorkspaceKeyManager"]

_NONCE_LEN = 12
_KEY_LEN = 32


class WorkspaceKeyError(Exception):
    """Lỗi quản lý key workspace (thiếu master key, DEK không tồn tại, …)."""


def _load_master_key() -> bytes:
    raw = os.environ.get("COSA_VAULT_MASTER_KEY")
    if not raw:
        env = (os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or "development").lower()
        if env in ("production", "staging", "prod"):
            raise WorkspaceKeyError(
                "COSA_VAULT_MASTER_KEY chưa được cấu hình (staging/prod bắt buộc — "
                "device Keychain hoặc secret store)"
            )
        # dev/test: master key deterministic-per-process từ một seed cố định trong repo
        # (không dùng cho dữ liệu thật).
        raw = base64.b64encode(b"cosa-dev-vault-master-key-32bytes").decode()
    try:
        key = base64.b64decode(raw)
    except Exception as exc:
        raise WorkspaceKeyError(f"COSA_VAULT_MASTER_KEY không phải base64 hợp lệ: {exc}") from exc
    if len(key) != _KEY_LEN:
        raise WorkspaceKeyError(f"master key phải {_KEY_LEN} byte, nhận {len(key)}")
    return key


@dataclass
class _DekFile:
    version: int
    wrapped: str  # base64(nonce + AESGCM(master, dek))
    created_at: str
    history: list[str]  # các wrapped DEK version cũ (rotation journal)


class WorkspaceKeyManager:
    def __init__(self, data_root: str | os.PathLike[str]) -> None:
        self._keys_dir = Path(data_root).resolve() / "host" / "keys"
        self._keys_dir.mkdir(parents=True, exist_ok=True)
        self._master = _load_master_key()
        self._cache: dict[str, bytes] = {}  # workspace_id -> plaintext DEK (RAM only)

    # --- envelope helpers -------------------------------------------------

    def _wrap(self, dek: bytes) -> str:
        nonce = secrets.token_bytes(_NONCE_LEN)
        ct = AESGCM(self._master).encrypt(nonce, dek, None)
        return base64.b64encode(nonce + ct).decode()

    def _unwrap(self, wrapped: str) -> bytes:
        blob = base64.b64decode(wrapped)
        nonce, ct = blob[:_NONCE_LEN], blob[_NONCE_LEN:]
        return AESGCM(self._master).decrypt(nonce, ct, None)

    def _path(self, workspace_id: str) -> Path:
        _check_segment(workspace_id, field="workspace_id")
        return self._keys_dir / f"{workspace_id}.dek"

    def _read_file(self, workspace_id: str) -> _DekFile | None:
        p = self._path(workspace_id)
        if not p.exists():
            return None
        d = json.loads(p.read_text())
        return _DekFile(
            version=d["version"],
            wrapped=d["wrapped"],
            created_at=d["created_at"],
            history=d.get("history", []),
        )

    def _write_file(self, workspace_id: str, f: _DekFile) -> None:
        self._path(workspace_id).write_text(
            json.dumps(
                {
                    "version": f.version,
                    "wrapped": f.wrapped,
                    "created_at": f.created_at,
                    "history": f.history,
                },
                indent=2,
            )
        )

    # --- public API ----------------------------------------------------

    def ensure_dek(self, workspace_id: str) -> None:
        """Tạo DEK cho workspace nếu chưa có (idempotent)."""
        if self._read_file(workspace_id) is not None:
            return
        dek = secrets.token_bytes(_KEY_LEN)
        self._write_file(
            workspace_id,
            _DekFile(
                version=1,
                wrapped=self._wrap(dek),
                created_at=datetime.now(UTC).isoformat(),
                history=[],
            ),
        )

    def _dek(self, workspace_id: str) -> bytes:
        if workspace_id in self._cache:
            return self._cache[workspace_id]
        f = self._read_file(workspace_id)
        if f is None:
            raise WorkspaceKeyError(f"workspace {workspace_id} chưa có DEK — gọi ensure_dek()")
        dek = self._unwrap(f.wrapped)
        self._cache[workspace_id] = dek
        return dek

    def encrypt(self, workspace_id: str, plaintext: bytes) -> bytes:
        nonce = secrets.token_bytes(_NONCE_LEN)
        ct = AESGCM(self._dek(workspace_id)).encrypt(nonce, plaintext, workspace_id.encode())
        return nonce + ct

    def decrypt(self, workspace_id: str, blob: bytes) -> bytes:
        nonce, ct = blob[:_NONCE_LEN], blob[_NONCE_LEN:]
        try:
            return AESGCM(self._dek(workspace_id)).decrypt(nonce, ct, workspace_id.encode())
        except Exception as exc:
            raise WorkspaceKeyError(
                f"không giải mã được payload của workspace {workspace_id} "
                f"(sai key / cross-workspace / tamper): {exc}"
            ) from exc

    def rotate(self, workspace_id: str) -> int:
        """Sinh DEK mới, giữ wrapped-DEK cũ trong `history` (rotation journal
        resumable). Trả về version mới. LƯU Ý: payload cũ mã hoá bằng DEK cũ vẫn
        cần re-encrypt bởi caller — journal cho phép tiếp tục nếu gián đoạn."""
        f = self._read_file(workspace_id)
        if f is None:
            raise WorkspaceKeyError(f"workspace {workspace_id} chưa có DEK")
        new_dek = secrets.token_bytes(_KEY_LEN)
        f.history.append(f.wrapped)
        f.wrapped = self._wrap(new_dek)
        f.version += 1
        f.created_at = datetime.now(UTC).isoformat()
        self._write_file(workspace_id, f)
        self._cache[workspace_id] = new_dek
        return f.version

    def export_wrapped_dek(self, workspace_id: str) -> str:
        """Trả về wrapped DEK (base64, envelope-encrypt bởi master key) để đưa vào
        backup manifest. KHÔNG phải plaintext DEK — chỉ giải được bởi host có cùng
        master key."""
        f = self._read_file(workspace_id)
        if f is None:
            raise WorkspaceKeyError(f"workspace {workspace_id} chưa có DEK")
        return f.wrapped

    def import_wrapped_dek(self, workspace_id: str, wrapped: str) -> None:
        """Ghi DEK cho workspace từ wrapped blob (restore/clone). Từ chối nếu
        workspace đã có DEK (tránh ghi đè key đang dùng). Xác minh unwrap được
        bằng master key hiện tại trước khi ghi."""
        if self._read_file(workspace_id) is not None:
            raise WorkspaceKeyError(f"workspace {workspace_id} đã có DEK — không ghi đè")
        try:
            self._unwrap(wrapped)
        except Exception as exc:
            raise WorkspaceKeyError(
                f"wrapped DEK không unwrap được bằng master key hiện tại: {exc}"
            ) from exc
        self._write_file(
            workspace_id,
            _DekFile(
                version=1,
                wrapped=wrapped,
                created_at=datetime.now(UTC).isoformat(),
                history=[],
            ),
        )

    def unload(self, workspace_id: str) -> None:
        """Xoá DEK khỏi cache RAM (gọi khi switch workspace)."""
        self._cache.pop(workspace_id, None)

    def unload_all(self) -> None:
        self._cache.clear()

    def destroy(self, workspace_id: str) -> None:
        """Xoá key file + cache sau retention/recovery window. Payload cũ trở nên
        không giải mã được — đúng ý muốn khi xoá workspace."""
        self._cache.pop(workspace_id, None)
        p = self._path(workspace_id)
        if p.exists():
            p.unlink()
