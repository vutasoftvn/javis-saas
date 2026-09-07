"""Task 3 (plan local-first-enterprise-knowledge) — Local persistent quarantine
store cho document upload trên Workspace Runtime Node.

ADR-LOCAL-FIRST-001 + Global Constraint của plan: KHÔNG dùng S3/MinIO/boto3
làm storage authority cho vault upload — raw file cư trú local, dưới 1 root
tuyệt đối được cấu hình (`COSA_WORKSPACE_STORAGE_ROOT`). Ticket secret chỉ
lưu SHA-256 hash trong `agent.local_upload_tickets`; raw local path/object key
KHÔNG BAO GIỜ trả về client (cùng nguyên tắc `DocumentObjectStore` cũ nhưng
storage thật là local filesystem, không phải S3-compatible presigned URL).
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import secrets
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "InMemoryUploadTicketRepository",
    "LocalObjectRef",
    "LocalUploadTicket",
    "PostgresUploadTicketRepository",
    "QuarantinedLocalObject",
    "UploadTicketExpired",
    "UploadTicketNotFound",
    "UploadTicketRecord",
    "UploadTicketRepository",
    "WorkspaceDocumentStore",
]

_WORKSPACE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_UPLOAD_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_VERSION_ID_RE = _UPLOAD_ID_RE


class UploadTicketNotFound(Exception):
    """Ticket không tồn tại, hoặc workspace_id/secret không khớp — cùng 1 lỗi
    (non-enumerating) để không lộ ticket thuộc workspace khác có tồn tại hay
    không."""


class UploadTicketExpired(Exception):
    pass


@dataclass(frozen=True)
class LocalUploadTicket:
    """Trả về đúng 1 lần cho client lúc issue — `secret` KHÔNG được persist
    dạng plaintext (chỉ SHA-256 hash lưu trong ticket repository)."""

    workspace_id: str
    upload_id: str
    secret: str
    max_bytes: int
    expires_at: datetime


@dataclass(frozen=True)
class QuarantinedLocalObject:
    workspace_id: str
    upload_id: str
    size_bytes: int
    source_sha256: str
    quarantine_relative_path: str


@dataclass(frozen=True)
class LocalObjectRef:
    relative_ref: str


@dataclass(frozen=True)
class UploadTicketRecord:
    workspace_id: str
    upload_id: str
    secret_hash: str
    max_bytes: int
    expires_at: datetime
    quarantine_relative_path: str
    created_at: datetime


@runtime_checkable
class UploadTicketRepository(Protocol):
    async def create(self, record: UploadTicketRecord) -> None: ...

    async def get(self, workspace_id: str, upload_id: str) -> UploadTicketRecord | None: ...

    async def delete(self, workspace_id: str, upload_id: str) -> None: ...


class InMemoryUploadTicketRepository:
    """Test-only — không persist thật, chỉ hợp lệ khi 1 instance được tái sử
    dụng xuyên suốt vòng đời test (không mô phỏng được "process restart" thật,
    xem test_workspace_store cho pattern đúng khi cần verify durability qua
    Postgres thật)."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], UploadTicketRecord] = {}

    async def create(self, record: UploadTicketRecord) -> None:
        self._records[(record.workspace_id, record.upload_id)] = record

    async def get(self, workspace_id: str, upload_id: str) -> UploadTicketRecord | None:
        return self._records.get((workspace_id, upload_id))

    async def delete(self, workspace_id: str, upload_id: str) -> None:
        self._records.pop((workspace_id, upload_id), None)


class PostgresUploadTicketRepository:
    """Backed bởi `agent.local_upload_tickets` (migration 028) — ticket phải
    sống sót qua restart API/worker process thật (Task 13 verify)."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def create(self, record: UploadTicketRecord) -> None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": record.workspace_id},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO agent.local_upload_tickets (
                        workspace_id, upload_id, secret_hash, max_bytes,
                        expires_at, quarantine_relative_path, created_at
                    ) VALUES (
                        :workspace_id, :upload_id, :secret_hash, :max_bytes,
                        :expires_at, :quarantine_relative_path, :created_at
                    )
                    ON CONFLICT (workspace_id, upload_id) DO UPDATE SET
                        secret_hash = EXCLUDED.secret_hash,
                        max_bytes = EXCLUDED.max_bytes,
                        expires_at = EXCLUDED.expires_at,
                        quarantine_relative_path = EXCLUDED.quarantine_relative_path
                    """
                ),
                {
                    "workspace_id": record.workspace_id,
                    "upload_id": record.upload_id,
                    "secret_hash": record.secret_hash,
                    "max_bytes": record.max_bytes,
                    "expires_at": record.expires_at,
                    "quarantine_relative_path": record.quarantine_relative_path,
                    "created_at": record.created_at,
                },
            )
            await session.commit()

    async def get(self, workspace_id: str, upload_id: str) -> UploadTicketRecord | None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            res = await session.execute(
                text(
                    """
                    SELECT workspace_id, upload_id, secret_hash, max_bytes,
                           expires_at, quarantine_relative_path, created_at
                    FROM agent.local_upload_tickets
                    WHERE workspace_id = :workspace_id AND upload_id = :upload_id
                    """
                ),
                {"workspace_id": workspace_id, "upload_id": upload_id},
            )
            row = res.mappings().first()
            if not row:
                return None
            return UploadTicketRecord(
                workspace_id=row["workspace_id"],
                upload_id=row["upload_id"],
                secret_hash=row["secret_hash"],
                max_bytes=row["max_bytes"],
                expires_at=row["expires_at"],
                quarantine_relative_path=row["quarantine_relative_path"],
                created_at=row["created_at"],
            )

    async def delete(self, workspace_id: str, upload_id: str) -> None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            await session.execute(
                text(
                    "DELETE FROM agent.local_upload_tickets "
                    "WHERE workspace_id = :workspace_id AND upload_id = :upload_id"
                ),
                {"workspace_id": workspace_id, "upload_id": upload_id},
            )
            await session.commit()


def _validate_id(value: str, pattern: re.Pattern[str], label: str) -> None:
    if not pattern.match(value):
        raise ValueError(f"invalid {label}: {value!r}")


class WorkspaceDocumentStore:
    """Local persistent quarantine + vault object storage trên Workspace
    Runtime Node. KHÔNG BAO GIỜ nhận S3/boto client — chỉ 1 `root: Path`
    tuyệt đối và 1 `UploadTicketRepository` để ticket sống sót qua restart."""

    def __init__(self, root: Path, upload_ticket_repository: UploadTicketRepository) -> None:
        root = Path(root)
        if not root.is_absolute():
            raise ValueError(f"WorkspaceDocumentStore root must be an absolute path, got {root!r}")
        if root.exists() and root.is_symlink():
            raise ValueError(f"WorkspaceDocumentStore root must not be a symlink: {root!r}")
        root.mkdir(parents=True, exist_ok=True)
        self._root = root.resolve(strict=True)
        self._tickets = upload_ticket_repository

    def _resolve_within_root(self, *parts: str) -> Path:
        """Resolve `root/parts...` and reject anything that escapes `root`
        (symlink hoặc `..` traversal) — kiểm tra SAU khi resolve, không tin
        chuỗi path thô."""
        candidate = self._root.joinpath(*parts)
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self._root)
        except ValueError as e:
            raise ValueError(f"path escapes workspace storage root: {candidate!r}") from e
        return resolved

    def _quarantine_dir(self, workspace_id: str, upload_id: str) -> Path:
        return self._resolve_within_root("quarantine", workspace_id, upload_id)

    def _vault_dir(self, workspace_id: str) -> Path:
        return self._resolve_within_root("vault", workspace_id)

    async def issue_ticket(
        self, workspace_id: str, upload_id: str, max_bytes: int
    ) -> LocalUploadTicket:
        _validate_id(workspace_id, _WORKSPACE_ID_RE, "workspace_id")
        _validate_id(upload_id, _UPLOAD_ID_RE, "upload_id")
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")

        secret = secrets.token_urlsafe(32)
        secret_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        random_name = secrets.token_hex(16)
        quarantine_dir = self._quarantine_dir(workspace_id, upload_id)
        relative_path = str(
            (quarantine_dir / random_name).relative_to(self._root)
        )
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        await self._tickets.create(
            UploadTicketRecord(
                workspace_id=workspace_id,
                upload_id=upload_id,
                secret_hash=secret_hash,
                max_bytes=max_bytes,
                expires_at=expires_at,
                quarantine_relative_path=relative_path,
                created_at=datetime.now(UTC),
            )
        )

        return LocalUploadTicket(
            workspace_id=workspace_id,
            upload_id=upload_id,
            secret=secret,
            max_bytes=max_bytes,
            expires_at=expires_at,
        )

    async def _authorize(self, workspace_id: str, upload_id: str, secret: str) -> UploadTicketRecord:
        record = await self._tickets.get(workspace_id, upload_id)
        if record is None:
            raise UploadTicketNotFound(f"no upload ticket for {workspace_id}/{upload_id}")
        secret_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        # So sánh hằng thời gian — tránh timing side-channel dò secret_hash.
        if not secrets.compare_digest(secret_hash, record.secret_hash):
            raise UploadTicketNotFound(f"no upload ticket for {workspace_id}/{upload_id}")
        if datetime.now(UTC) > record.expires_at:
            raise UploadTicketExpired(f"upload ticket expired for {workspace_id}/{upload_id}")
        return record

    async def write_upload_stream(
        self,
        workspace_id: str,
        upload_id: str,
        secret: str,
        chunks: Any,
    ) -> None:
        """`chunks`: iterable đồng bộ of bytes (danh sách hoặc generator).
        Caller async (vd. FastAPI `request.stream()`) tự thu gom thành list
        trước khi gọi — kích thước document đã bị chặn bởi `MIME_TYPE_LIMITS`
        nên giữ nguyên đồng bộ ở tầng ghi đĩa cho đơn giản, không mất
        streaming thật ở tầng nhận request. Ghi vào `<quarantine_path>.partial`,
        enforce `max_bytes` khi đang ghi, fsync, rồi `os.replace` atomic vào
        path cuối cùng."""
        record = await self._authorize(workspace_id, upload_id, secret)
        final_path = self._root / record.quarantine_relative_path
        final_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = final_path.with_suffix(final_path.suffix + ".partial")
        chunk_list = list(chunks)

        def _write_sync() -> None:
            written = 0
            fd = os.open(partial_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                with os.fdopen(fd, "wb") as f:
                    for chunk in chunk_list:
                        written += len(chunk)
                        if written > record.max_bytes:
                            raise ValueError(
                                f"upload exceeds max_bytes={record.max_bytes} for {upload_id}"
                            )
                        f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())
            except BaseException:
                partial_path.unlink(missing_ok=True)
                raise
            os.replace(partial_path, final_path)
            os.chmod(final_path, 0o600)

        await asyncio.to_thread(_write_sync)

    async def finalize_upload(
        self, workspace_id: str, upload_id: str
    ) -> QuarantinedLocalObject:
        record = await self._tickets.get(workspace_id, upload_id)
        if record is None:
            raise UploadTicketNotFound(f"no upload ticket for {workspace_id}/{upload_id}")
        final_path = self._root / record.quarantine_relative_path
        if not final_path.exists():
            raise ValueError(f"upload not completed for {workspace_id}/{upload_id}")

        def _hash_and_size() -> tuple[str, int]:
            h = hashlib.sha256()
            size = 0
            with final_path.open("rb") as f:
                for block in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(block)
                    size += len(block)
            return h.hexdigest(), size

        sha256_hex, size_bytes = await asyncio.to_thread(_hash_and_size)
        if size_bytes > record.max_bytes:
            raise ValueError(f"upload size {size_bytes} exceeds max {record.max_bytes} bytes")

        return QuarantinedLocalObject(
            workspace_id=workspace_id,
            upload_id=upload_id,
            size_bytes=size_bytes,
            source_sha256=sha256_hex,
            quarantine_relative_path=record.quarantine_relative_path,
        )

    async def promote_to_vault(
        self, workspace_id: str, version_id: str, quarantine_ref: str
    ) -> LocalObjectRef:
        """Copy 1 object đã quarantine sang khu vực vault bất biến — recompute
        SHA-256 SAU khi copy, reject nếu lệch trước khi coi version là
        publishable (chống race/corruption giữa lúc quarantine và lúc
        promote)."""
        _validate_id(workspace_id, _WORKSPACE_ID_RE, "workspace_id")
        _validate_id(version_id, _VERSION_ID_RE, "version_id")

        source = self._resolve_within_root(*Path(quarantine_ref).parts)
        if not source.exists():
            raise ValueError(f"quarantine object not found: {quarantine_ref!r}")

        expected_sha256 = await asyncio.to_thread(self._sha256_of, source)

        target_dir = self._vault_dir(workspace_id)
        target = target_dir / version_id

        def _copy_sync() -> None:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            os.chmod(target, 0o600)

        await asyncio.to_thread(_copy_sync)

        actual_sha256 = await asyncio.to_thread(self._sha256_of, target)
        if actual_sha256 != expected_sha256:
            target.unlink(missing_ok=True)
            raise ValueError(
                f"checksum mismatch promoting {quarantine_ref!r} to vault version {version_id!r}"
            )

        return LocalObjectRef(relative_ref=str(target.relative_to(self._root)))

    async def read_quarantine_object(self, workspace_id: str, quarantine_relative_path: str) -> bytes:
        """Task 5 — đọc bytes 1 object đã quarantine (dùng cho conversion
        pipeline: preflight → scanner → converter). `quarantine_relative_path`
        phải resolve về đúng workspace này (không tin path thô từ caller)."""
        _validate_id(workspace_id, _WORKSPACE_ID_RE, "workspace_id")
        resolved = self._resolve_within_root(*Path(quarantine_relative_path).parts)
        expected_prefix = self._root / "quarantine" / workspace_id
        try:
            resolved.relative_to(expected_prefix)
        except ValueError as e:
            raise ValueError(
                f"quarantine object {quarantine_relative_path!r} does not belong to workspace "
                f"{workspace_id!r}"
            ) from e
        if not resolved.exists():
            raise ValueError(f"quarantine object not found: {quarantine_relative_path!r}")

        def _read() -> bytes:
            return resolved.read_bytes()

        return await asyncio.to_thread(_read)

    async def purge_version(self, workspace_id: str, version_id: str) -> None:
        _validate_id(workspace_id, _WORKSPACE_ID_RE, "workspace_id")
        _validate_id(version_id, _VERSION_ID_RE, "version_id")
        target = self._vault_dir(workspace_id) / version_id

        def _unlink() -> None:
            target.unlink(missing_ok=True)

        await asyncio.to_thread(_unlink)

    @staticmethod
    def _sha256_of(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()
