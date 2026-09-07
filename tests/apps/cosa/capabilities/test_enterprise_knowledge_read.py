"""Task 8 (plan local-first-enterprise-knowledge) — capability
`knowledge.enterprise.read` phải lọc theo authorization TRƯỚC KHI trả citation
cho model, và KHÔNG BAO GIỜ suy diễn role operator/founder từ ctx hiện tại
(role_ids mặc định rỗng — xem docstring apps.cosa.capabilities.enterprise_knowledge_read)."""

from __future__ import annotations

import uuid

import pytest
from agent.knowledge.models import KnowledgeChunk, KnowledgeDocument
from agent.knowledge.service import KnowledgeIngestionService
from agent.knowledge.store import InMemoryKnowledgeStore
from agent.vault.models import VaultClassification, VaultVisibility
from agent.vault.repository import InMemoryVaultRepository

from apps.cosa.capabilities.enterprise_knowledge_read import (
    ENTERPRISE_KNOWLEDGE_READ_SPEC,
    create_enterprise_knowledge_read_handler,
)


def test_enterprise_knowledge_read_spec_properties():
    assert ENTERPRISE_KNOWLEDGE_READ_SPEC.id == "knowledge.enterprise.read"
    assert ENTERPRISE_KNOWLEDGE_READ_SPEC.input_schema["required"] == ["query"]


async def _seed_published_doc(
    vault_repo: InMemoryVaultRepository,
    store: InMemoryKnowledgeStore,
    workspace_id: str,
    *,
    created_by: str,
    classification: VaultClassification = VaultClassification.INTERNAL,
    visibility: VaultVisibility = VaultVisibility.PRIVATE,
    content: str = "salary bands overview",
) -> None:
    vault_doc = await vault_repo.create_draft(
        workspace_id,
        "handbook",
        created_by=created_by,
        classification=classification,
        visibility=visibility,
    )
    version = await vault_repo.append_version(
        workspace_id,
        vault_doc.document_id,
        object_ref={"path": "handbook.md"},
        checksum_sha256="0" * 64,
        size_bytes=len(content),
        source_uri=f"vault://{vault_doc.document_id}",
        created_by=created_by,
    )
    await vault_repo.update_document_state(workspace_id, vault_doc.document_id, "PUBLISHED")

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    doc = KnowledgeDocument(
        id=doc_id,
        workspace_id=workspace_id,
        title="handbook",
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
    await store.save_document(doc)


@pytest.mark.asyncio
async def test_handler_denies_member_without_grant_even_with_valid_input():
    vault_repo = InMemoryVaultRepository()
    knowledge_store = InMemoryKnowledgeStore()
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    await _seed_published_doc(
        vault_repo,
        knowledge_store,
        workspace_id,
        created_by="founder",
        visibility=VaultVisibility.PRIVATE,
    )
    service = KnowledgeIngestionService(store=knowledge_store, vault_repository=vault_repo)
    handler = create_enterprise_knowledge_read_handler(service)

    result = await handler(
        {"query": "salary"}, {"workspace_id": workspace_id, "principal": "member-1"}
    )
    assert result["citations"] == []


@pytest.mark.asyncio
async def test_handler_returns_workspace_visible_citation_to_member():
    vault_repo = InMemoryVaultRepository()
    knowledge_store = InMemoryKnowledgeStore()
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    await _seed_published_doc(
        vault_repo,
        knowledge_store,
        workspace_id,
        created_by="founder",
        visibility=VaultVisibility.WORKSPACE,
        classification=VaultClassification.INTERNAL,
    )
    service = KnowledgeIngestionService(store=knowledge_store, vault_repository=vault_repo)
    handler = create_enterprise_knowledge_read_handler(service)

    result = await handler(
        {"query": "salary"}, {"workspace_id": workspace_id, "principal": "member-1"}
    )
    assert len(result["citations"]) == 1
    citation = result["citations"][0]
    assert citation["vault_version_id"] is not None
    assert "salary" in citation["snippet"]


@pytest.mark.asyncio
async def test_handler_does_not_assume_operator_role_without_resolver():
    """Không có role_ids_resolver injected -> role_ids mặc định RỖNG, kể cả
    khi ctx.principal trùng tên hay giống founder — capability KHÔNG được tự
    suy diễn quyền operator từ bất kỳ tín hiệu nào ngoài role_ids tường minh."""
    vault_repo = InMemoryVaultRepository()
    knowledge_store = InMemoryKnowledgeStore()
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    await _seed_published_doc(
        vault_repo,
        knowledge_store,
        workspace_id,
        created_by="founder-owner",
        visibility=VaultVisibility.WORKSPACE,
        classification=VaultClassification.RESTRICTED,
    )
    service = KnowledgeIngestionService(store=knowledge_store, vault_repository=vault_repo)
    handler = create_enterprise_knowledge_read_handler(service)

    result = await handler(
        {"query": "salary"}, {"workspace_id": workspace_id, "principal": "some-other-member"}
    )
    assert result["citations"] == []


@pytest.mark.asyncio
async def test_handler_uses_injected_role_ids_resolver():
    vault_repo = InMemoryVaultRepository()
    knowledge_store = InMemoryKnowledgeStore()
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    await _seed_published_doc(
        vault_repo,
        knowledge_store,
        workspace_id,
        created_by="founder-owner",
        visibility=VaultVisibility.WORKSPACE,
        classification=VaultClassification.RESTRICTED,
    )
    service = KnowledgeIngestionService(store=knowledge_store, vault_repository=vault_repo)
    handler = create_enterprise_knowledge_read_handler(
        service, role_ids_resolver=lambda ctx: {"founder"}
    )

    result = await handler(
        {"query": "salary"}, {"workspace_id": workspace_id, "principal": "founder-owner"}
    )
    assert len(result["citations"]) == 1


@pytest.mark.asyncio
async def test_handler_requires_workspace_id_and_principal():
    service = KnowledgeIngestionService()
    handler = create_enterprise_knowledge_read_handler(service)

    with pytest.raises(ValueError, match="workspace_id"):
        await handler({"query": "salary"}, {"principal": "member-1"})

    with pytest.raises(ValueError, match="principal"):
        await handler({"query": "salary"}, {"workspace_id": "ws-1"})
