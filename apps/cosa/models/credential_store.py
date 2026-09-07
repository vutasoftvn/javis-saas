"""Task 2 (plan 2026-09-07-local-first-model-routing) — lưu trữ credential
provider (API key) cục bộ, mã hoá tại chỗ, workspace-scoped.

`models.model_provider_profiles` (Task 1, migration 030) chỉ lưu
`credential_ref` — bảng `models.workspace_credentials` (migration 031) là nơi
ciphertext thật nằm. Không bao giờ lưu/serialize plaintext API key ra ngoài
`LocalCredentialStore.get()` (trả `pydantic.SecretStr`, chưa `.get_secret_value()`
cho tới điểm dùng cuối cùng).

Mã hoá: AES-256-GCM (`cryptography.hazmat.primitives.ciphers.aead.AESGCM`,
đã là dependency của repo — cùng primitive với
`packages/agent/vault/keys.py::WorkspaceKeyManager`), nonce ngẫu nhiên 12 byte
prepend vào ciphertext, AAD = workspace_id (cross-workspace decrypt luôn thất
bại — không có "workspace nào cũng đọc được" ngầm định). ĐÂY LÀ HELPER RIÊNG,
KHÔNG import từ `packages/agent/vault/*` — khác subsystem (DEK tài liệu vault
vs credential provider), khác biến môi trường, khác layout key file (theo
hướng dẫn task).

Key cục bộ đọc 1 lần từ file tại `COSA_LOCAL_SECRETS_KEY_FILE` (KHÔNG phải
giá trị base64 trực tiếp trong biến môi trường như `COSA_VAULT_MASTER_KEY`) —
production/staging bắt buộc: file phải tồn tại, đường dẫn tuyệt đối, không là
symlink, và mode không được có bit group/world (`mode & 0o077 == 0`, tức phải
là 0600 hoặc chặt hơn). Dev/test: nếu chưa cấu hình hoặc file chưa tồn tại thì
tự sinh key ngẫu nhiên 32 byte và ghi bằng `os.open(..., 0o600)` (cùng pattern
`apps/cosa/knowledge_ingestion/workspace_store.py`), rồi verify lại mode sau
khi ghi.
"""

from __future__ import annotations

import base64
import os
import secrets
import stat
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import BaseModel, ConfigDict, SecretStr

__all__ = [
    "CredentialNotFound",
    "CredentialReference",
    "CredentialStoreError",
    "InMemoryCredentialRepository",
    "LocalCredentialStore",
    "PostgresCredentialRepository",
    "load_local_secrets_key",
]

_NONCE_LEN = 12
_KEY_LEN = 32
_CURRENT_KEY_VERSION = 1


class CredentialStoreError(Exception):
    """Lỗi cấu hình/đọc key cục bộ (thiếu file, quyền không an toàn, …)."""


class CredentialNotFound(Exception):
    """Fail-closed: credential không tồn tại, không thuộc đúng workspace, hoặc
    không giải mã được (sai key/AAD/tamper) — không phân biệt lý do cụ thể ra
    ngoài để tránh oracle side-channel, và KHÔNG BAO GIỜ kèm plaintext."""


class CredentialReference(BaseModel):
    """Trả về từ `put()` — chỉ ID/metadata, không bao giờ chứa secret.
    `extra="forbid"` là rào chắn cấu trúc giống `ResolvedModelRoute`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    workspace_id: str
    key_version: int = _CURRENT_KEY_VERSION


# ── Key cục bộ: đọc từ file, hard-fail production nếu thiếu/không an toàn ──


def _is_production_env() -> bool:
    env = (os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or "development").lower()
    return env in ("production", "staging", "prod")


def _default_dev_key_file() -> Path:
    # Dev fallback: state cục bộ dưới home directory của user chạy process
    # (không phải env var provider — chỉ là vị trí file key cục bộ mặc định).
    return Path.home() / ".cosa" / "local" / "local_secrets.key"


def _check_key_file_mode(path: Path) -> None:
    if path.is_symlink():
        raise CredentialStoreError(
            f"key file '{path}' là symlink — không chấp nhận (chống trỏ ra path không cục bộ)."
        )
    mode = stat.S_IMODE(os.stat(path).st_mode)
    if mode & 0o077:
        raise CredentialStoreError(
            f"key file '{path}' có quyền group/world (mode={oct(mode)}) — "
            "phải là 0600 (chỉ owner đọc/ghi)."
        )


def _create_dev_key_file(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_bytes(_KEY_LEN)
    encoded = base64.b64encode(key).decode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(encoded)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    os.chmod(path, 0o600)
    # Verify lại sau khi tạo — không tin umask/hệ điều hành âm thầm nới quyền.
    _check_key_file_mode(path)
    return key


def _read_key_file(path: Path) -> bytes:
    _check_key_file_mode(path)
    raw = path.read_text().strip()
    try:
        key = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise CredentialStoreError(f"key file '{path}' không phải base64 hợp lệ: {exc}") from exc
    if len(key) != _KEY_LEN:
        raise CredentialStoreError(
            f"key file '{path}' phải chứa {_KEY_LEN} byte sau decode, nhận {len(key)}."
        )
    return key


def load_local_secrets_key(explicit_path: str | os.PathLike[str] | None = None) -> bytes:
    """Đọc key cục bộ 32 byte dùng để mã hoá credential. `explicit_path` cho
    test/composition tiêm trực tiếp; mặc định đọc từ env
    `COSA_LOCAL_SECRETS_KEY_FILE`.

    Production/staging: bắt buộc phải cấu hình, path phải tuyệt đối, không
    phải symlink, file phải tồn tại sẵn (không tự tạo), mode không có bit
    group/world. Dev: cho phép fallback + tự tạo file 0600 nếu chưa có.
    """
    configured = (
        explicit_path
        if explicit_path is not None
        else os.environ.get("COSA_LOCAL_SECRETS_KEY_FILE")
    )
    is_prod = _is_production_env()

    if not configured:
        if is_prod:
            raise CredentialStoreError(
                "COSA_LOCAL_SECRETS_KEY_FILE chưa được cấu hình — bắt buộc ở production/staging."
            )
        path = _default_dev_key_file()
    else:
        path = Path(configured)
        if is_prod and not path.is_absolute():
            raise CredentialStoreError(
                f"COSA_LOCAL_SECRETS_KEY_FILE phải là đường dẫn tuyệt đối cục bộ ở "
                f"production/staging, nhận '{path}'."
            )

    if not path.exists():
        if is_prod:
            raise CredentialStoreError(
                f"key file '{path}' không tồn tại — production/staging không tự tạo key, "
                "phải provision trước khi khởi động."
            )
        return _create_dev_key_file(path)

    return _read_key_file(path)


# ── AES-256-GCM helper (workspace_id làm AAD) ──


def _encrypt(key: bytes, workspace_id: str, plaintext: bytes) -> bytes:
    nonce = secrets.token_bytes(_NONCE_LEN)
    ct = AESGCM(key).encrypt(nonce, plaintext, workspace_id.encode("utf-8"))
    return nonce + ct


def _decrypt(key: bytes, workspace_id: str, blob: bytes) -> bytes:
    nonce, ct = blob[:_NONCE_LEN], blob[_NONCE_LEN:]
    try:
        return AESGCM(key).decrypt(nonce, ct, workspace_id.encode("utf-8"))
    except Exception as exc:
        # Không lộ lý do cụ thể (sai key / sai AAD / tamper) và KHÔNG kèm
        # bất kỳ phần plaintext/ciphertext nào vào message lỗi.
        raise CredentialNotFound(
            "credential không giải mã được cho workspace này (sai workspace hoặc dữ liệu hỏng)."
        ) from exc


# ── Repository (Postgres + InMemory, cùng convention apps/cosa/models/repository.py) ──


class PostgresCredentialRepository:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def _set_workspace(self, session: Any, workspace_id: str) -> None:
        from sqlalchemy import text

        await session.execute(
            text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
            {"workspace_id": workspace_id},
        )

    async def put(
        self, workspace_id: str, credential_id: str, ciphertext_b64: str, key_version: int
    ) -> None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            await session.execute(
                text(
                    """
                    INSERT INTO models.workspace_credentials (
                        workspace_id, credential_id, ciphertext, key_version
                    ) VALUES (:workspace_id, :credential_id, :ciphertext, :key_version)
                    ON CONFLICT (workspace_id, credential_id) DO UPDATE SET
                        ciphertext = EXCLUDED.ciphertext,
                        key_version = EXCLUDED.key_version,
                        updated_at = now()
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "credential_id": credential_id,
                    "ciphertext": ciphertext_b64,
                    "key_version": key_version,
                },
            )
            await session.commit()

    async def get(self, workspace_id: str, credential_id: str) -> tuple[str, int] | None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            res = await session.execute(
                text(
                    """
                    SELECT ciphertext, key_version FROM models.workspace_credentials
                    WHERE workspace_id = :workspace_id AND credential_id = :credential_id
                    """
                ),
                {"workspace_id": workspace_id, "credential_id": credential_id},
            )
            row = res.mappings().first()
            if row is None:
                return None
            return row["ciphertext"], row["key_version"]

    async def raw_ciphertext_for_test(self, credential_id: str) -> str:
        raise NotImplementedError(
            "raw_ciphertext_for_test là test-only helper — dùng "
            "InMemoryCredentialRepository trong test, không dùng Postgres thật "
            "(RLS fail-closed chặn đọc không set đúng workspace_id)."
        )


class InMemoryCredentialRepository:
    """Test/dev-only — không persist qua process restart, cùng nguyên tắc
    `InMemoryModelRoutingRepository`."""

    def __init__(self) -> None:
        self._rows: dict[tuple[str, str], tuple[str, int]] = {}

    async def put(
        self, workspace_id: str, credential_id: str, ciphertext_b64: str, key_version: int
    ) -> None:
        self._rows[(workspace_id, credential_id)] = (ciphertext_b64, key_version)

    async def get(self, workspace_id: str, credential_id: str) -> tuple[str, int] | None:
        return self._rows.get((workspace_id, credential_id))

    async def raw_ciphertext_for_test(self, credential_id: str) -> str:
        """Test-only: trả ciphertext bất kể workspace nào tạo ra nó — dùng để
        assert plaintext không xuất hiện trong dữ liệu lưu trữ. KHÔNG tồn tại
        trên đường sản phẩm thật."""
        for (_, stored_credential_id), (ciphertext_b64, _) in self._rows.items():
            if stored_credential_id == credential_id:
                return ciphertext_b64
        raise CredentialNotFound(f"credential '{credential_id}' không tồn tại (test helper).")


# ── Store: mã hoá/giải mã + orchestrate repository ──


class LocalCredentialStore:
    def __init__(
        self, repository: Any, key_file_path: str | os.PathLike[str] | None = None
    ) -> None:
        self._repo = repository
        self._key = load_local_secrets_key(key_file_path)
        self._key_version = _CURRENT_KEY_VERSION

    async def put(self, workspace_id: str, plaintext: SecretStr) -> CredentialReference:
        credential_id = f"cred-{secrets.token_hex(16)}"
        secret_bytes = plaintext.get_secret_value().encode("utf-8")
        blob = _encrypt(self._key, workspace_id, secret_bytes)
        ciphertext_b64 = base64.b64encode(blob).decode()
        await self._repo.put(workspace_id, credential_id, ciphertext_b64, self._key_version)
        return CredentialReference(
            id=credential_id, workspace_id=workspace_id, key_version=self._key_version
        )

    async def get(self, workspace_id: str, credential_id: str) -> SecretStr:
        row = await self._repo.get(workspace_id, credential_id)
        if row is None:
            raise CredentialNotFound(
                f"credential '{credential_id}' không tồn tại cho workspace này."
            )
        ciphertext_b64, _key_version = row
        blob = base64.b64decode(ciphertext_b64)
        plaintext = _decrypt(self._key, workspace_id, blob)
        return SecretStr(plaintext.decode("utf-8"))

    async def raw_ciphertext_for_test(self, credential_id: str) -> str:
        return await self._repo.raw_ciphertext_for_test(credential_id)
