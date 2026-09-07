"""Task 8 (plan local-first-enterprise-knowledge) — retrieval phải lọc theo
authorization TRƯỚC KHI ranking/limit. Parametrize cả 2 đường:

- `PostgresKnowledgeStore.retrieve_authorized_citations()` — join SQL thật
  với `vault.*` (skip nếu `AGENT_TEST_DATABASE_URL` không set).
- `KnowledgeIngestionService.retrieve_authorized_citations()` compose từ
  `InMemoryKnowledgeStore` + `InMemoryVaultRepository` (luôn chạy) — đường
  fallback cho backend không tự implement join thật.

Cả 2 phải cho CÙNG kết quả với cùng input — leakage test phải PASS ở cả hai.
"""

from __future__ import annotations

import os
import uuid

import pytest
from agent.knowledge.models import KnowledgeChunk, KnowledgeDocument
from agent.knowledge.providers.postgres import PostgresKnowledgeStore
from agent.knowledge.service import KnowledgeIngestionService
from agent.knowledge.store import InMemoryKnowledgeStore
from agent.vault.models import (
    VaultAccessGrant,
    VaultClassification,
    VaultGrantSubjectType,
    VaultPermission,
    VaultVisibility,
)
from agent.vault.repository import InMemoryVaultRepository, PostgresVaultRepository
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

_RAW_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if _RAW_DB_URL and "postgresql+asyncpg://" not in _RAW_DB_URL and "postgresql://" in _RAW_DB_URL:
    TEST_DATABASE_URL = _RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    TEST_DATABASE_URL = _RAW_DB_URL


class _RetrievalHarness:
    """Gộp VaultRepository + KnowledgeStore/Service lại 1 API tiện cho test —
    KHÔNG phải production code, chỉ để 2 backend share cùng 1 bộ test."""

    def __init__(self, *, vault_repository, retrieve_fn) -> None:
        self._vault = vault_repository
        self._retrieve_fn = retrieve_fn

    async def save_published_chunk(
        self,
        workspace_id: str,
        doc_title: str,
        content: str,
        *,
        created_by: str = "founder",
        classification: VaultClassification = VaultClassification.INTERNAL,
        visibility: VaultVisibility = VaultVisibility.PRIVATE,
        grants: list[tuple[str, str, VaultPermission]] | None = None,
    ) -> KnowledgeDocument:
        raise NotImplementedError

    async def retrieve_authorized_citations(
        self, workspace_id, principal_id, role_ids, query, limit=5
    ):
        return await self._retrieve_fn(
            workspace_id=workspace_id,
            principal_id=principal_id,
            role_ids=role_ids,
            query=query,
            limit=limit,
        )


class _InMemoryHarness(_RetrievalHarness):
    def __init__(self) -> None:
        self._vault_repo = InMemoryVaultRepository()
        self._knowledge_store = InMemoryKnowledgeStore()
        self._service = KnowledgeIngestionService(
            store=self._knowledge_store, vault_repository=self._vault_repo
        )
        super().__init__(
            vault_repository=self._vault_repo,
            retrieve_fn=self._service.retrieve_authorized_citations,
        )

    async def save_published_chunk(
        self,
        workspace_id,
        doc_title,
        content,
        *,
        created_by="founder",
        classification=VaultClassification.INTERNAL,
        visibility=VaultVisibility.PRIVATE,
        grants=None,
    ):
        vault_doc = await self._vault_repo.create_draft(
            workspace_id,
            doc_title,
            created_by=created_by,
            classification=classification,
            visibility=visibility,
        )
        version = await self._vault_repo.append_version(
            workspace_id,
            vault_doc.document_id,
            object_ref={"path": f"{doc_title}.md"},
            checksum_sha256="0" * 64,
            size_bytes=len(content),
            source_uri=f"vault://{vault_doc.document_id}",
            created_by=created_by,
        )
        await self._vault_repo.update_document_state(
            workspace_id, vault_doc.document_id, "PUBLISHED"
        )

        for subject_id, subject_type, permission in grants or []:
            await self._vault_repo.grant_access(
                workspace_id,
                vault_doc.document_id,
                VaultAccessGrant(
                    subject_type=VaultGrantSubjectType(subject_type),
                    subject_id=subject_id,
                    permission=permission,
                    granted_by=created_by,
                ),
            )

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        doc = KnowledgeDocument(
            id=doc_id,
            workspace_id=workspace_id,
            title=doc_title,
            ingest_status="published",
            vault_document_id=str(vault_doc.document_id),
            vault_version_id=str(version.version_id),
            access_policy_version=1,
            chunks=[
                KnowledgeChunk(
                    id=f"chk_{doc_id}_0",
                    document_id=doc_id,
                    workspace_id=workspace_id,
                    chunk_index=0,
                    content=content,
                )
            ],
        )
        await self._knowledge_store.save_document(doc)
        return doc


class _PostgresHarness(_RetrievalHarness):
    def __init__(self) -> None:
        engine = create_async_engine(TEST_DATABASE_URL)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        self._vault_repo = PostgresVaultRepository(factory)
        self._knowledge_store = PostgresKnowledgeStore(db_session_factory=factory)
        super().__init__(
            vault_repository=self._vault_repo,
            retrieve_fn=self._knowledge_store.retrieve_authorized_citations,
        )

    async def save_published_chunk(
        self,
        workspace_id,
        doc_title,
        content,
        *,
        created_by="founder",
        classification=VaultClassification.INTERNAL,
        visibility=VaultVisibility.PRIVATE,
        grants=None,
    ):
        vault_doc = await self._vault_repo.create_draft(
            workspace_id,
            doc_title,
            created_by=created_by,
            classification=classification,
            visibility=visibility,
        )
        version = await self._vault_repo.append_version(
            workspace_id,
            vault_doc.document_id,
            object_ref={"path": f"{doc_title}.md"},
            checksum_sha256="0" * 64,
            size_bytes=len(content),
            source_uri=f"vault://{vault_doc.document_id}",
            created_by=created_by,
        )
        await self._vault_repo.update_document_state(
            workspace_id, vault_doc.document_id, "PUBLISHED"
        )

        for subject_id, subject_type, permission in grants or []:
            await self._vault_repo.grant_access(
                workspace_id,
                vault_doc.document_id,
                VaultAccessGrant(
                    subject_type=VaultGrantSubjectType(subject_type),
                    subject_id=subject_id,
                    permission=permission,
                    granted_by=created_by,
                ),
            )

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        doc = KnowledgeDocument(
            id=doc_id,
            workspace_id=workspace_id,
            title=doc_title,
            ingest_status="published",
            vault_document_id=str(vault_doc.document_id),
            vault_version_id=str(version.version_id),
            access_policy_version=1,
            chunks=[
                KnowledgeChunk(
                    id=f"chk_{doc_id}_0",
                    document_id=doc_id,
                    workspace_id=workspace_id,
                    chunk_index=0,
                    content=content,
                )
            ],
        )
        await self._knowledge_store.save_document(doc)
        return doc


@pytest.fixture(params=["in_memory", "postgres"])
def store(request):
    if request.param == "postgres":
        if not TEST_DATABASE_URL:
            pytest.skip("AGENT_TEST_DATABASE_URL not set")
        return _PostgresHarness()
    return _InMemoryHarness()


@pytest.mark.asyncio
async def test_retrieval_never_returns_restricted_chunk_to_member(store):
    workspace_id = f"ws-a-{uuid.uuid4().hex[:8]}"
    await store.save_published_chunk(
        workspace_id,
        "restricted",
        "quarterly salary table",
        created_by="founder",
        classification=VaultClassification.RESTRICTED,
        visibility=VaultVisibility.WORKSPACE,
    )

    results = await store.retrieve_authorized_citations(
        workspace_id, "member-1", {"member"}, "salary", 5
    )
    assert results == []


@pytest.mark.asyncio
async def test_member_with_explicit_grant_can_read_restricted_chunk(store):
    workspace_id = f"ws-a-{uuid.uuid4().hex[:8]}"
    await store.save_published_chunk(
        workspace_id,
        "restricted",
        "quarterly salary table",
        created_by="founder",
        classification=VaultClassification.RESTRICTED,
        visibility=VaultVisibility.WORKSPACE,
        grants=[("member-1", "user", VaultPermission.READ)],
    )

    results = await store.retrieve_authorized_citations(
        workspace_id, "member-1", {"member"}, "salary", 5
    )
    assert len(results) == 1
    assert "salary" in results[0].snippet


@pytest.mark.asyncio
async def test_founder_receives_citation_with_version_provenance(store):
    workspace_id = f"ws-a-{uuid.uuid4().hex[:8]}"
    await store.save_published_chunk(
        workspace_id, "handbook", "salary policy overview", created_by="founder-1"
    )

    results = await store.retrieve_authorized_citations(
        workspace_id, "founder-1", {"founder"}, "salary", 5
    )
    assert len(results) == 1
    assert results[0].vault_version_id is not None


@pytest.mark.asyncio
async def test_member_cannot_read_private_document_of_another_member(store):
    workspace_id = f"ws-a-{uuid.uuid4().hex[:8]}"
    await store.save_published_chunk(
        workspace_id,
        "private notes",
        "salary negotiation notes",
        created_by="member-owner",
        visibility=VaultVisibility.PRIVATE,
    )

    results = await store.retrieve_authorized_citations(
        workspace_id, "member-2", {"member"}, "salary", 5
    )
    assert results == []


@pytest.mark.asyncio
async def test_workspace_visible_non_restricted_document_readable_by_any_member(store):
    workspace_id = f"ws-a-{uuid.uuid4().hex[:8]}"
    await store.save_published_chunk(
        workspace_id,
        "handbook",
        "salary bands are published quarterly",
        created_by="founder",
        classification=VaultClassification.INTERNAL,
        visibility=VaultVisibility.WORKSPACE,
    )

    results = await store.retrieve_authorized_citations(
        workspace_id, "member-1", {"member"}, "salary", 5
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_retrieval_never_crosses_workspace_boundary(store):
    ws_a = f"ws-a-{uuid.uuid4().hex[:8]}"
    ws_b = f"ws-b-{uuid.uuid4().hex[:8]}"
    await store.save_published_chunk(
        ws_a,
        "handbook",
        "salary bands are public here",
        created_by="founder",
        visibility=VaultVisibility.WORKSPACE,
    )

    results = await store.retrieve_authorized_citations(ws_b, "founder", {"founder"}, "salary", 5)
    assert results == []
