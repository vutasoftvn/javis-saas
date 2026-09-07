"""Task 5 (plan local-first-enterprise-knowledge) — LocalIngestionRepository:
state machine ingestion cục bộ, thay thế state machine trước đây sống trong
services/cosa (bảng `document_ingestions`, TypeScript/HTTP).

Fencing: `claim()` là CAS nguyên tử (UPDATE ... WHERE state = 'QUEUED' ...
RETURNING) — 2 worker cùng claim 1 upload chỉ đúng 1 bên thắng. Không trả raw
storage ref (quarantine_relative_path) ra ngoài caller API — chỉ dùng nội bộ
pipeline (worker đọc file qua `WorkspaceDocumentStore`), không phải giá trị
trả về cho API caller.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

__all__ = [
    "ClaimResult",
    "InMemoryLocalIngestionRepository",
    "LocalIngestionRepository",
    "LocalIngestionState",
]


class LocalIngestionState(StrEnum):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    CONVERTING = "CONVERTING"
    REVIEW_PENDING = "REVIEW_PENDING"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ClaimResult:
    claimed: bool
    quarantine_relative_path: str | None = None
    declared_media_type: str | None = None
    detected_media_type: str | None = None
    source_sha256: str | None = None
    size_bytes: int | None = None
    reason: str | None = None


def _hash_token(task_token: str) -> str:
    return hashlib.sha256(task_token.encode("utf-8")).hexdigest()


class LocalIngestionRepository:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def _set_workspace(self, session: Any, workspace_id: str) -> None:
        from sqlalchemy import text

        await session.execute(
            text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
            {"workspace_id": workspace_id},
        )

    async def _append_event(
        self,
        session: Any,
        *,
        workspace_id: str,
        upload_id: str,
        old_state: str | None,
        new_state: str,
        reason: str | None,
    ) -> None:
        from sqlalchemy import text

        await session.execute(
            text(
                """
                INSERT INTO agent.local_ingestion_events (
                    workspace_id, upload_id, old_state, new_state, reason
                ) VALUES (:workspace_id, :upload_id, :old_state, :new_state, :reason)
                """
            ),
            {
                "workspace_id": workspace_id,
                "upload_id": upload_id,
                "old_state": old_state,
                "new_state": new_state,
                "reason": reason,
            },
        )

    async def create_queued(
        self,
        workspace_id: str,
        upload_id: str,
        *,
        quarantine_relative_path: str,
        declared_media_type: str | None,
        detected_media_type: str | None,
        source_sha256: str | None,
        size_bytes: int | None,
        created_by: str,
    ) -> None:
        """Tạo attempt record QUEUED — idempotent (ON CONFLICT DO NOTHING):
        gọi lại với cùng (workspace_id, upload_id) không tạo bản ghi thứ hai
        hay reset trạng thái đã tiến triển."""
        from sqlalchemy import text

        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            await session.execute(
                text(
                    """
                    INSERT INTO agent.local_ingestion_attempts (
                        workspace_id, upload_id, state, quarantine_relative_path,
                        declared_media_type, detected_media_type, source_sha256,
                        size_bytes, created_by
                    ) VALUES (
                        :workspace_id, :upload_id, 'QUEUED', :quarantine_relative_path,
                        :declared_media_type, :detected_media_type, :source_sha256,
                        :size_bytes, :created_by
                    )
                    ON CONFLICT (workspace_id, upload_id) DO NOTHING
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "upload_id": upload_id,
                    "quarantine_relative_path": quarantine_relative_path,
                    "declared_media_type": declared_media_type,
                    "detected_media_type": detected_media_type,
                    "source_sha256": source_sha256,
                    "size_bytes": size_bytes,
                    "created_by": created_by,
                },
            )
            await self._append_event(
                session,
                workspace_id=workspace_id,
                upload_id=upload_id,
                old_state=None,
                new_state=LocalIngestionState.QUEUED.value,
                reason=None,
            )
            await session.commit()

    async def claim(self, workspace_id: str, upload_id: str, task_token: str) -> ClaimResult:
        """CAS nguyên tử QUEUED → VALIDATING. `task_token` là claim token của
        scheduler task (fencing) — chỉ lưu SHA-256 hash."""
        from sqlalchemy import text

        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            res = await session.execute(
                text(
                    """
                    UPDATE agent.local_ingestion_attempts
                    SET state = 'VALIDATING', claim_token_hash = :token_hash, updated_at = now()
                    WHERE workspace_id = :workspace_id AND upload_id = :upload_id AND state = 'QUEUED'
                    RETURNING quarantine_relative_path, declared_media_type, detected_media_type,
                              source_sha256, size_bytes
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "upload_id": upload_id,
                    "token_hash": _hash_token(task_token),
                },
            )
            row = res.mappings().first()
            if row is None:
                await session.commit()
                return ClaimResult(claimed=False, reason="not_queued_or_already_claimed")

            await self._append_event(
                session,
                workspace_id=workspace_id,
                upload_id=upload_id,
                old_state=LocalIngestionState.QUEUED.value,
                new_state=LocalIngestionState.VALIDATING.value,
                reason=None,
            )
            await session.commit()
            return ClaimResult(
                claimed=True,
                quarantine_relative_path=row["quarantine_relative_path"],
                declared_media_type=row["declared_media_type"],
                detected_media_type=row["detected_media_type"],
                source_sha256=row["source_sha256"],
                size_bytes=row["size_bytes"],
            )

    async def record_candidate(
        self,
        workspace_id: str,
        upload_id: str,
        knowledge_source_id: str,
        manifest_json: dict[str, Any] | None = None,
    ) -> bool:
        """VALIDATING/CONVERTING → REVIEW_PENDING. Trả `False` (no-op) nếu
        attempt không còn ở trạng thái pending (retry sau khi lần chạy trước
        đã hoàn tất) — KHÔNG raise, để caller (handler) coi đây là idempotent
        success, không phải lỗi."""
        import json as _json

        from sqlalchemy import text

        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            res = await session.execute(
                text(
                    """
                    UPDATE agent.local_ingestion_attempts
                    SET state = 'REVIEW_PENDING', knowledge_source_id = :knowledge_source_id,
                        manifest_json = :manifest_json, updated_at = now()
                    WHERE workspace_id = :workspace_id AND upload_id = :upload_id
                      AND state IN ('VALIDATING', 'CONVERTING')
                    RETURNING state
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "upload_id": upload_id,
                    "knowledge_source_id": knowledge_source_id,
                    "manifest_json": _json.dumps(manifest_json) if manifest_json else None,
                },
            )
            row = res.mappings().first()
            if row is None:
                await session.commit()
                return False

            await self._append_event(
                session,
                workspace_id=workspace_id,
                upload_id=upload_id,
                old_state=None,
                new_state=LocalIngestionState.REVIEW_PENDING.value,
                reason=None,
            )
            await session.commit()
            return True

    async def reject(
        self,
        workspace_id: str,
        upload_id: str,
        failure_code: str,
        *,
        terminal: bool = True,
    ) -> bool:
        """Đánh dấu thất bại. `terminal=True` (mặc định) → REJECTED (không
        retry, đúng semantics cũ: scan/parse lỗi vĩnh viễn). `terminal=False`
        → FAILED (scheduler được retry)."""
        from sqlalchemy import text

        target_state = (
            LocalIngestionState.REJECTED.value if terminal else LocalIngestionState.FAILED.value
        )
        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            res = await session.execute(
                text(
                    """
                    UPDATE agent.local_ingestion_attempts
                    SET state = :target_state, failure_code = :failure_code, updated_at = now()
                    WHERE workspace_id = :workspace_id AND upload_id = :upload_id
                      AND state IN ('QUEUED', 'VALIDATING', 'CONVERTING')
                    RETURNING state
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "upload_id": upload_id,
                    "target_state": target_state,
                    "failure_code": failure_code,
                },
            )
            row = res.mappings().first()
            if row is None:
                await session.commit()
                return False

            await self._append_event(
                session,
                workspace_id=workspace_id,
                upload_id=upload_id,
                old_state=None,
                new_state=target_state,
                reason=failure_code,
            )
            await session.commit()
            return True

    async def publish(
        self,
        workspace_id: str,
        upload_id: str,
        *,
        vault_document_id: str,
        vault_version_id: str,
    ) -> bool:
        """REVIEW_PENDING → PUBLISHED. Caller (Task 6/7 review flow) phải đã
        copy+verify quarantine content vào Vault (WorkspaceDocumentStore.
        promote_to_vault) TRƯỚC khi gọi — method này chỉ ghi nhận state,
        không tự copy file."""
        from sqlalchemy import text

        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            res = await session.execute(
                text(
                    """
                    UPDATE agent.local_ingestion_attempts
                    SET state = 'PUBLISHED', vault_document_id = :vault_document_id,
                        vault_version_id = :vault_version_id, updated_at = now()
                    WHERE workspace_id = :workspace_id AND upload_id = :upload_id
                      AND state = 'REVIEW_PENDING'
                    RETURNING state
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "upload_id": upload_id,
                    "vault_document_id": vault_document_id,
                    "vault_version_id": vault_version_id,
                },
            )
            row = res.mappings().first()
            if row is None:
                await session.commit()
                return False

            await self._append_event(
                session,
                workspace_id=workspace_id,
                upload_id=upload_id,
                old_state=LocalIngestionState.REVIEW_PENDING.value,
                new_state=LocalIngestionState.PUBLISHED.value,
                reason=None,
            )
            await session.commit()
            return True

    async def get_state(self, workspace_id: str, upload_id: str) -> LocalIngestionState | None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            await self._set_workspace(session, workspace_id)
            res = await session.execute(
                text(
                    """
                    SELECT state FROM agent.local_ingestion_attempts
                    WHERE workspace_id = :workspace_id AND upload_id = :upload_id
                    """
                ),
                {"workspace_id": workspace_id, "upload_id": upload_id},
            )
            row = res.mappings().first()
            if row is None:
                return None
            return LocalIngestionState(row["state"])


@dataclass
class _Attempt:
    state: LocalIngestionState
    quarantine_relative_path: str
    declared_media_type: str | None
    detected_media_type: str | None
    source_sha256: str | None
    size_bytes: int | None
    knowledge_source_id: str | None = None
    vault_document_id: str | None = None
    vault_version_id: str | None = None
    failure_code: str | None = None


class InMemoryLocalIngestionRepository:
    """Test/dev-only — không persist qua process restart. Dùng khi
    `AGENT_DATABASE_URL` chưa cấu hình (cùng nguyên tắc InMemory* khác trong
    repo) hoặc trong test không cần Postgres thật."""

    def __init__(self) -> None:
        self._attempts: dict[tuple[str, str], _Attempt] = {}

    async def create_queued(
        self,
        workspace_id: str,
        upload_id: str,
        *,
        quarantine_relative_path: str,
        declared_media_type: str | None,
        detected_media_type: str | None,
        source_sha256: str | None,
        size_bytes: int | None,
        created_by: str,
    ) -> None:
        key = (workspace_id, upload_id)
        if key in self._attempts:
            return
        self._attempts[key] = _Attempt(
            state=LocalIngestionState.QUEUED,
            quarantine_relative_path=quarantine_relative_path,
            declared_media_type=declared_media_type,
            detected_media_type=detected_media_type,
            source_sha256=source_sha256,
            size_bytes=size_bytes,
        )

    async def claim(self, workspace_id: str, upload_id: str, task_token: str) -> ClaimResult:
        attempt = self._attempts.get((workspace_id, upload_id))
        if attempt is None or attempt.state != LocalIngestionState.QUEUED:
            return ClaimResult(claimed=False, reason="not_queued_or_already_claimed")
        attempt.state = LocalIngestionState.VALIDATING
        return ClaimResult(
            claimed=True,
            quarantine_relative_path=attempt.quarantine_relative_path,
            declared_media_type=attempt.declared_media_type,
            detected_media_type=attempt.detected_media_type,
            source_sha256=attempt.source_sha256,
            size_bytes=attempt.size_bytes,
        )

    async def record_candidate(
        self,
        workspace_id: str,
        upload_id: str,
        knowledge_source_id: str,
        manifest_json: dict[str, Any] | None = None,
    ) -> bool:
        attempt = self._attempts.get((workspace_id, upload_id))
        if attempt is None or attempt.state not in (
            LocalIngestionState.VALIDATING,
            LocalIngestionState.CONVERTING,
        ):
            return False
        attempt.state = LocalIngestionState.REVIEW_PENDING
        attempt.knowledge_source_id = knowledge_source_id
        return True

    async def reject(
        self,
        workspace_id: str,
        upload_id: str,
        failure_code: str,
        *,
        terminal: bool = True,
    ) -> bool:
        attempt = self._attempts.get((workspace_id, upload_id))
        if attempt is None or attempt.state not in (
            LocalIngestionState.QUEUED,
            LocalIngestionState.VALIDATING,
            LocalIngestionState.CONVERTING,
        ):
            return False
        attempt.state = (
            LocalIngestionState.REJECTED if terminal else LocalIngestionState.FAILED
        )
        attempt.failure_code = failure_code
        return True

    async def publish(
        self,
        workspace_id: str,
        upload_id: str,
        *,
        vault_document_id: str,
        vault_version_id: str,
    ) -> bool:
        attempt = self._attempts.get((workspace_id, upload_id))
        if attempt is None or attempt.state != LocalIngestionState.REVIEW_PENDING:
            return False
        attempt.state = LocalIngestionState.PUBLISHED
        attempt.vault_document_id = vault_document_id
        attempt.vault_version_id = vault_version_id
        return True

    async def get_state(self, workspace_id: str, upload_id: str) -> LocalIngestionState | None:
        attempt = self._attempts.get((workspace_id, upload_id))
        return attempt.state if attempt else None
