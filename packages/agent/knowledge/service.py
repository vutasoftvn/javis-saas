from __future__ import annotations

import hashlib
import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from agent.knowledge.chunking import chunk_text
from agent.knowledge.models import CitationProvenance, KnowledgeChunk, KnowledgeDocument
from agent.knowledge.store import InMemoryKnowledgeStore, KnowledgeStore

if TYPE_CHECKING:
    from agent.vault.repository import VaultRepository

__all__ = ["KnowledgeIngestionService"]

_OPERATOR_ROLES = frozenset({"founder", "co-founder", "admin"})


class KnowledgeIngestionService:
    """Service chịu trách nhiệm ingest, chunk và retrieve Knowledge theo Master Guide §26."""

    def __init__(
        self,
        store: KnowledgeStore | None = None,
        vault_repository: VaultRepository | None = None,
    ) -> None:
        self._store = store or InMemoryKnowledgeStore()
        # Task 8 (plan local-first-enterprise-knowledge) — chỉ cần cho
        # `retrieve_authorized_citations()` khi `store` KHÔNG tự implement nó
        # (InMemoryKnowledgeStore không mang dữ liệu vault) — compose bằng
        # cách lọc qua `VaultRepository.resolve_accessible_document_ids()`.
        # PostgresKnowledgeStore tự làm join thật trong 1 câu SQL, không cần
        # tham số này.
        self._vault_repository = vault_repository

    async def ingest_raw_text(
        self,
        *,
        workspace_id: str,
        title: str,
        text_content: str,
        source_uri: str | None = None,
        media_type: str = "text/plain",
        chunk_size: int = 800,
        overlap: int = 100,
    ) -> KnowledgeDocument:
        checksum = hashlib.sha256(text_content.encode("utf-8")).hexdigest()
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"

        raw_chunks = chunk_text(text_content, chunk_size=chunk_size, overlap=overlap)
        chunk_models = []
        for idx, c_text in enumerate(raw_chunks):
            chunk_models.append(
                KnowledgeChunk(
                    id=f"chk_{doc_id}_{idx}",
                    document_id=doc_id,
                    workspace_id=workspace_id,
                    chunk_index=idx,
                    content=c_text,
                    page_or_section=f"Section {idx + 1}",
                )
            )

        doc = KnowledgeDocument(
            id=doc_id,
            workspace_id=workspace_id,
            title=title,
            source_uri=source_uri,
            media_type=media_type,
            checksum=checksum,
            ingest_status="completed",
            chunks=chunk_models,
        )

        await self._store.save_document(doc)
        return doc

    async def ingest_normalized_document(
        self,
        document: KnowledgeDocument,
    ) -> KnowledgeDocument:
        """Persist a caller-built normalized document without re-chunking.

        Dùng khi document đã được chuẩn hoá, chunked, và đặt trạng thái bên ngoài
        (ví dụ: MarkItDown converter → normalization.py build candidate với chunks
        sẵn, sau đó gọi đây để persist).

        Không tự tạo chunks, không chỉnh đổi status/authority, không ghi đè metadata.
        Chỉ persist document như đã cho.

        Args:
            document: KnowledgeDocument đã sẵn chunks, status, authority_class

        Returns:
            KnowledgeDocument sau khi persist (có thể có ID/metadata được server update)
        """
        await self._store.save_document(document)
        return document

    async def update_document_ingest_status(
        self,
        document_id: str,
        status: str,
        workspace_id: str,
    ) -> KnowledgeDocument:
        """Cập nhật riêng `ingest_status` của một document đã persist.

        Dùng cho luồng review: sau khi người duyệt quyết định, candidate
        review_pending được chuyển sang published/rejected. Không đụng chunks,
        authority_class hay metadata — chỉ đổi trạng thái.

        Raises:
            ValueError: nếu không tìm thấy document.
        """
        document = await self._store.get_document(document_id, workspace_id)
        if document is None:
            raise ValueError(f"knowledge document not found: {document_id}")
        document.ingest_status = status
        await self._store.save_document(document)
        return document

    async def delete_by_vault_document(self, workspace_id: str, vault_document_id: str) -> None:
        """Task 11 — passthrough xoá vĩnh viễn (không phải soft-delete) mọi
        knowledge source/chunk/embedding trỏ về 1 Vault document đã purge."""
        await self._store.delete_by_vault_document(workspace_id, vault_document_id)

    async def retrieve_citations(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int = 5,
    ) -> list[CitationProvenance]:
        return await self._store.search_chunks(
            workspace_id=workspace_id,
            query=query,
            limit=limit,
        )

    async def retrieve_authorized_citations(
        self,
        *,
        workspace_id: str,
        principal_id: str,
        role_ids: set[str],
        query: str,
        limit: int = 5,
    ) -> list[CitationProvenance]:
        """Task 8 (plan local-first-enterprise-knowledge) — filter theo
        authorization TRƯỚC KHI ranking/limit áp dụng cho caller (không trả
        rồi lọc phía trên, tránh 1 caller quên lọc lộ citation bị deny).

        `PostgresKnowledgeStore` tự implement method này bằng 1 câu SQL join
        thật (tránh N+1). Với backend khác (vd. `InMemoryKnowledgeStore` dùng
        cho test/dev) compose bằng `VaultRepository.resolve_accessible_document_ids()`
        — cần `vault_repository` được inject lúc khởi tạo service.
        """
        native = getattr(self._store, "retrieve_authorized_citations", None)
        if native is not None:
            return await native(
                workspace_id=workspace_id,
                principal_id=principal_id,
                role_ids=role_ids,
                query=query,
                limit=limit,
            )

        if self._vault_repository is None:
            raise RuntimeError(
                "retrieve_authorized_citations() cần vault_repository khi store "
                "không tự implement method này (vd. InMemoryKnowledgeStore)."
            )

        is_operator = bool(role_ids & _OPERATOR_ROLES)
        accessible_ids: set[UUID] | None = None
        if not is_operator:
            accessible_ids = await self._vault_repository.resolve_accessible_document_ids(
                workspace_id, principal_id, role_ids
            )
            if not accessible_ids:
                return []

        # Over-fetch trước khi lọc theo authorization — kết quả cuối có thể
        # ít hơn `limit` dù còn match khác chưa authorized bị bỏ qua ở đây
        # (giới hạn đã biết của cách compose 2 bước; PostgresKnowledgeStore
        # không có giới hạn này vì lọc ngay trong SQL trước LIMIT).
        candidates = await self._store.search_chunks(
            workspace_id=workspace_id, query=query, limit=limit * 5
        )

        results: list[CitationProvenance] = []
        for citation in candidates:
            doc = await self._store.get_document(citation.document_id, workspace_id)
            if doc is None or doc.ingest_status != "published" or not doc.vault_document_id:
                continue
            if not is_operator and UUID(doc.vault_document_id) not in (accessible_ids or set()):
                continue
            # Bug tìm thấy trong lúc làm Task 11 (purge): compose fallback
            # trước đây KHÔNG kiểm tra `vault.documents.state` — sau khi
            # `request_purge()`/archive chuyển state khỏi PUBLISHED, citation
            # vẫn lọt qua (chỉ visibility/grant/ownership được xét, không xét
            # trạng thái vault document hiện tại). PostgresKnowledgeStore đã
            # đúng từ đầu (`WHERE d.state = 'PUBLISHED'` trong SQL join) —
            # đường compose này phải khớp cùng luật.
            vault_doc = await self._vault_repository.get_document(
                workspace_id, UUID(doc.vault_document_id)
            )
            if vault_doc is None or vault_doc.state != "PUBLISHED":
                continue
            results.append(citation.model_copy(update={"vault_version_id": doc.vault_version_id}))
            if len(results) >= limit:
                break
        return results
