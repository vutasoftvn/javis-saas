"""Task 9 (plan local-first-enterprise-knowledge) — unit-level test cho
resolver/dispatch (`execute_persisted_operation`), tách khỏi HTTP transport
(xem tests/apps/cosa/api/test_graphql_routes.py cho coverage qua ASGI thật)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from agent.knowledge.models import KnowledgeChunk, KnowledgeDocument
from agent.knowledge.service import KnowledgeIngestionService
from agent.knowledge.store import InMemoryKnowledgeStore
from agent.vault.models import VaultClassification, VaultVisibility
from agent.vault.repository import InMemoryVaultRepository
from fastapi import HTTPException

from apps.cosa.auth.dependency import AuthenticatedIdentity
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.graphql.persisted_operations import execute_persisted_operation


class _FakePlane:
    def __init__(self, knowledge_ingestion_service, company_client=None) -> None:
        self.knowledge_ingestion_service = knowledge_ingestion_service
        self.company_client = company_client


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
    mock_client = AsyncMock(spec=CompanyServiceClient)
    mock_client.get.return_value = {
        "tasks": [{"id": 1, "title": "Q3 review"}],
        "total": 1,
    }
    plane = _FakePlane(
        KnowledgeIngestionService(store=store, vault_repository=vault_repo),
        company_client=mock_client,
    )
    identity = _identity(workspace_id=workspace_id, principal_id="founder-1", role_id="founder")

    result = await execute_persisted_operation(
        "workspaceContext", {"question": "rủi ro quý này"}, identity, plane
    )
    assert result["citations"]
    assert result["business"]["tasks"] == [{"id": 1, "title": "Q3 review"}]
    mock_client.get.assert_awaited_once()
    called_params = mock_client.get.await_args.kwargs.get("params", {})
    assert called_params.get("workspaceId") == workspace_id


@pytest.mark.asyncio
async def test_workspace_context_business_is_empty_without_company_client():
    """Không có `company_client` (vd. test cũ/dev fixture nhẹ) -> business
    field fail-closed rỗng, KHÔNG raise — citations vẫn hoạt động bình thường."""
    vault_repo = InMemoryVaultRepository()
    store = InMemoryKnowledgeStore()
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    plane = _FakePlane(KnowledgeIngestionService(store=store, vault_repository=vault_repo))
    identity = _identity(workspace_id=workspace_id, principal_id="founder-1", role_id="founder")

    result = await execute_persisted_operation(
        "workspaceContext", {"question": "gì đó"}, identity, plane
    )
    assert result["business"]["tasks"] == []


@pytest.mark.asyncio
async def test_workspace_context_business_fails_closed_when_company_service_errors():
    """Company service lỗi (down, timeout...) không được làm hỏng toàn bộ
    workspaceContext — citations vẫn trả về bình thường, business rỗng."""
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
    mock_client = AsyncMock(spec=CompanyServiceClient)
    mock_client.get.side_effect = RuntimeError("company service unavailable")
    plane = _FakePlane(
        KnowledgeIngestionService(store=store, vault_repository=vault_repo),
        company_client=mock_client,
    )
    identity = _identity(workspace_id=workspace_id, principal_id="founder-1", role_id="founder")

    result = await execute_persisted_operation(
        "workspaceContext", {"question": "rủi ro quý này"}, identity, plane
    )
    assert result["citations"]
    assert result["business"]["tasks"] == []


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
