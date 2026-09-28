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
async def test_handler_default_resolver_reads_real_role_id_from_ctx():
    """Task 10 wired `role_id` thật vào ctx (conversation_routes.py ->
    worker/handlers.py -> InvocationContext.metadata) — resolver mặc định
    (không inject gì) giờ phải ĐỌC ĐƯỢC field đó, không còn luôn rỗng như
    trước khi đóng gap này."""
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
        {"query": "salary"},
        {"workspace_id": workspace_id, "principal": "some-other-member", "role_id": "founder"},
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


@pytest.mark.asyncio
async def test_handler_without_snapshot_store_ignores_initiative_id():
    """No `ai_initiative_snapshot_store` injected (plane built without DB, or
    older callers) — Task 11 gate must be a no-op, not a new denial, so a run
    carrying `metadata.initiative_id` behaves exactly as before Task 11."""
    vault_repo = InMemoryVaultRepository()
    knowledge_store = InMemoryKnowledgeStore()
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    await _seed_published_doc(
        vault_repo,
        knowledge_store,
        workspace_id,
        created_by="founder",
        visibility=VaultVisibility.WORKSPACE,
    )
    service = KnowledgeIngestionService(store=knowledge_store, vault_repository=vault_repo)
    handler = create_enterprise_knowledge_read_handler(service)

    result = await handler(
        {"query": "salary"},
        {"workspace_id": workspace_id, "principal": "member-1", "metadata": {"initiative_id": "init_1"}},
    )
    assert len(result["citations"]) == 1


@pytest.mark.asyncio
async def test_handler_denies_when_initiative_has_no_snapshot():
    from apps.cosa.models.ai_initiative_snapshot import InMemoryAiInitiativePromotionSnapshotStore

    vault_repo = InMemoryVaultRepository()
    knowledge_store = InMemoryKnowledgeStore()
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    await _seed_published_doc(
        vault_repo,
        knowledge_store,
        workspace_id,
        created_by="founder",
        visibility=VaultVisibility.WORKSPACE,
    )
    service = KnowledgeIngestionService(store=knowledge_store, vault_repository=vault_repo)
    store = InMemoryAiInitiativePromotionSnapshotStore()
    handler = create_enterprise_knowledge_read_handler(service, ai_initiative_snapshot_store=store)

    with pytest.raises(ValueError, match="initiative_snapshot_not_found"):
        await handler(
            {"query": "salary"},
            {
                "workspace_id": workspace_id,
                "principal": "member-1",
                "metadata": {"initiative_id": "init_unknown"},
            },
        )


@pytest.mark.asyncio
async def test_handler_denies_when_initiative_data_readiness_not_ready():
    from apps.cosa.models.ai_initiative_snapshot import (
        AiInitiativePromotionSnapshot,
        InMemoryAiInitiativePromotionSnapshotStore,
    )

    vault_repo = InMemoryVaultRepository()
    knowledge_store = InMemoryKnowledgeStore()
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    await _seed_published_doc(
        vault_repo,
        knowledge_store,
        workspace_id,
        created_by="founder",
        visibility=VaultVisibility.WORKSPACE,
    )
    service = KnowledgeIngestionService(store=knowledge_store, vault_repository=vault_repo)
    store = InMemoryAiInitiativePromotionSnapshotStore()
    await store.consume(
        f"{workspace_id}:init_1:dec_1",
        AiInitiativePromotionSnapshot(
            workspace_id=workspace_id,
            project_id="proj_1",
            initiative_id="init_1",
            initiative_revision=1,
            decision_id="dec_1",
            decision_hash="hash_1",
            lifecycle_state="PILOT",
            risk_tier="LOW",
            autonomy_tier="A0",
            data_readiness_status="NOT_READY",
            retrieval_mode="none",
        ),
    )
    handler = create_enterprise_knowledge_read_handler(service, ai_initiative_snapshot_store=store)

    with pytest.raises(ValueError, match="data_readiness_not_ready"):
        await handler(
            {"query": "salary"},
            {"workspace_id": workspace_id, "principal": "member-1", "metadata": {"initiative_id": "init_1"}},
        )
