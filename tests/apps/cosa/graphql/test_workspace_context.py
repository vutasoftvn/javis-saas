"""Task 9 (plan local-first-enterprise-knowledge) — unit-level test cho
resolver/dispatch (`execute_persisted_operation`), tách khỏi HTTP transport
(xem tests/apps/cosa/api/test_graphql_routes.py cho coverage qua ASGI thật)."""

from __future__ import annotations

import uuid

import pytest
from agent.knowledge.models import KnowledgeChunk, KnowledgeDocument
from agent.knowledge.service import KnowledgeIngestionService
from agent.knowledge.store import InMemoryKnowledgeStore
from agent.vault.models import VaultClassification, VaultVisibility
from agent.vault.repository import InMemoryVaultRepository
from fastapi import HTTPException

from apps.cosa.auth.dependency import AuthenticatedIdentity
from apps.cosa.graphql.persisted_operations import execute_persisted_operation


class _FakePlane:
    def __init__(self, knowledge_ingestion_service) -> None:
        self.knowledge_ingestion_service = knowledge_ingestion_service


def _identity(*, workspace_id: str, principal_id: str, role_id: str) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        principal_id=principal_id,
        platform_user_id=principal_id,
        workspace_id=workspace_id,
        role_id=role_id,
        bearer_token="test-bearer-token",
        resolved_platform_user_id=principal_id,
    )


async def _seed(
    vault_repo, store, workspace_id, *, created_by, visibility, classification, content
):
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
async def test_founder_workspace_context_includes_permitted_business_and_knowledge():
    vault_repo = InMemoryVaultRepository()
    store = InMemoryKnowledgeStore()
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    await _seed(
        vault_repo,
        store,
        workspace_id,
        created_by="founder-1",
        visibility=VaultVisibility.WORKSPACE,
        classification=VaultClassification.INTERNAL,
        content="rủi ro quý này tập trung ở dòng tiền",
    )
    plane = _FakePlane(KnowledgeIngestionService(store=store, vault_repository=vault_repo))
    identity = _identity(workspace_id=workspace_id, principal_id="founder-1", role_id="founder")

    result = await execute_persisted_operation(
        "workspaceContext", {"question": "rủi ro quý này"}, identity, plane
    )
    assert result["citations"]


@pytest.mark.asyncio
async def test_member_cannot_submit_raw_query_or_see_denied_source():
    vault_repo = InMemoryVaultRepository()
    store = InMemoryKnowledgeStore()
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    await _seed(
        vault_repo,
        store,
        workspace_id,
        created_by="founder-1",
        visibility=VaultVisibility.PRIVATE,
        classification=VaultClassification.INTERNAL,
        content="quarterly salary table",
    )
    plane = _FakePlane(KnowledgeIngestionService(store=store, vault_repository=vault_repo))
    member_identity = _identity(
        workspace_id=workspace_id, principal_id="member-1", role_id="member"
    )

    with pytest.raises(HTTPException) as exc_info:
        await execute_persisted_operation("secretsQuery", {}, member_identity, plane)
    assert exc_info.value.status_code == 404

    result = await execute_persisted_operation(
        "enterpriseKnowledgeSearch", {"query": "lương"}, member_identity, plane
    )
    assert result["citations"] == []


@pytest.mark.asyncio
async def test_unknown_variable_rejected_before_resolver_runs():
    plane = _FakePlane(KnowledgeIngestionService())
    identity = _identity(workspace_id="ws-1", principal_id="member-1", role_id="member")

    with pytest.raises(HTTPException) as exc_info:
        await execute_persisted_operation(
            "enterpriseKnowledgeSearch", {"query": "x", "unexpected": "y"}, identity, plane
        )
    assert exc_info.value.status_code == 422
