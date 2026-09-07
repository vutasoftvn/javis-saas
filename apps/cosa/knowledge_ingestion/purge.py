"""Task 11 (plan local-first-enterprise-knowledge) — revoke access và purge
vật lý an toàn, không để retrieval trả kết quả cũ trong lúc dọn dẹp bất đồng
bộ.

Two-stage: `request_purge()` (đồng bộ, ngay trong request) chỉ chuyển
`vault.documents.state` sang `PURGE_PENDING` — `retrieve_authorized_citations()`
(Task 8) đã lọc `d.state = 'PUBLISHED'` từ trước, nên document biến mất khỏi
retrieval NGAY LẬP TỨC dù file vật lý/chunk embedding chưa xoá. Dọn dẹp vật lý
thật (`execute_purge_task()`) chạy sau, qua scheduler — an toàn để retry (mọi
bước đều idempotent, không bước nào có thể "hồi sinh" lại 1 source đã purge).

`revoke_access()`/`set_legal_hold()` KHÔNG tự authorize — caller (route) phải
đã resolve `KnowledgeAuthorization.resolve(identity, document_id).manage`
TRƯỚC khi gọi, cùng pattern với publish/review ở Task 7 (authorization luôn ở
tầng route nơi có đủ AuthenticatedIdentity thật, không nhân đôi logic ở đây)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from agent.knowledge.service import KnowledgeIngestionService
from agent.vault.models import VaultGrantSubjectType
from agent.vault.repository import VaultRepository

from apps.cosa.knowledge_ingestion.workspace_store import WorkspaceDocumentStore

__all__ = ["PurgeBlocked", "PurgeRequest", "VaultPurgeService"]

logger = logging.getLogger("cosa.knowledge_ingestion.purge")


class PurgeBlocked(Exception):
    """Purge bị chặn — message luôn nêu rõ lý do (vd 'legal hold')."""


@dataclass(frozen=True)
class PurgeRequest:
    document_id: UUID
    workspace_id: str
    status: str
    requested_by: str
    requested_at: datetime


class VaultPurgeService:
    def __init__(
        self,
        vault_repository: VaultRepository,
        knowledge_ingestion_service: KnowledgeIngestionService,
        store: WorkspaceDocumentStore,
    ) -> None:
        self._vault_repository = vault_repository
        self._knowledge_service = knowledge_ingestion_service
        self._store = store

    async def revoke_access(
        self,
        workspace_id: str,
        document_id: UUID,
        subject_id: str,
        *,
        subject_type: VaultGrantSubjectType = VaultGrantSubjectType.USER,
        revoked_by: str | None = None,
    ) -> None:
        await self._vault_repository.revoke_access(
            workspace_id, document_id, subject_type, subject_id
        )
        logger.info(
            "vault.access_revoked",
            extra={
                "workspace_id": workspace_id,
                "document_id": str(document_id),
                "subject_type": subject_type.value,
                "subject_id": subject_id,
                "revoked_by": revoked_by,
            },
        )

    async def set_legal_hold(
        self,
        workspace_id: str,
        document_id: UUID,
        legal_hold: bool,
        *,
        set_by: str | None = None,
    ) -> None:
        """Task 11/13 runbook gap đã ghi nhận — trước đây method này không có
        audit trail nào ngoài `updated_at` trên `vault.documents`. Thêm log
        có cấu trúc (workspace/document/giá trị mới/ai đặt) — chưa phải bảng
        audit riêng trong DB (đó vẫn là việc tương lai nếu cần truy vấn lại
        lịch sử), nhưng đủ để trace qua log pipeline hiện có."""
        await self._vault_repository.set_legal_hold(workspace_id, document_id, legal_hold)
        logger.info(
            "vault.legal_hold_changed",
            extra={
                "workspace_id": workspace_id,
                "document_id": str(document_id),
                "legal_hold": legal_hold,
                "set_by": set_by,
            },
        )

    async def request_purge(
        self, workspace_id: str, document_id: UUID, principal_id: str
    ) -> PurgeRequest:
        document = await self._vault_repository.get_document(workspace_id, document_id)
        if document is None:
            raise ValueError("document not found")
        if document.legal_hold:
            raise PurgeBlocked(f"document {document_id} is under legal hold, cannot purge")

        now = datetime.now(UTC)
        await self._vault_repository.update_document_state(
            workspace_id, document_id, "PURGE_PENDING"
        )
        logger.info(
            "vault.purge_requested",
            extra={
                "workspace_id": workspace_id,
                "document_id": str(document_id),
                "requested_by": principal_id,
            },
        )
        return PurgeRequest(
            document_id=document_id,
            workspace_id=workspace_id,
            status="PURGE_PENDING",
            requested_by=principal_id,
            requested_at=now,
        )

    async def execute_purge_task(self, workspace_id: str, document_id: UUID) -> None:
        """Idempotent — an toàn gọi lại nhiều lần (vd sau lỗi giữa chừng, hoặc
        task được reclaim/retry): không raise nếu document đã PURGED hay
        không còn tồn tại, không "hồi sinh" bất cứ thứ gì đã xoá."""
        document = await self._vault_repository.get_document(workspace_id, document_id)
        if document is None or document.state != "PURGE_PENDING":
            return

        await self._knowledge_service.delete_by_vault_document(workspace_id, str(document_id))

        versions = await self._vault_repository.list_versions(workspace_id, document_id)
        for version in versions:
            await self._store.purge_version(workspace_id, str(version.version_id))

        await self._vault_repository.update_document_state(workspace_id, document_id, "PURGED")
        logger.info(
            "vault.purged",
            extra={"workspace_id": workspace_id, "document_id": str(document_id)},
        )
