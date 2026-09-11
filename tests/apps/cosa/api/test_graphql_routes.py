"""Task 9 (plan local-first-enterprise-knowledge) — `POST /agent/graphql`
persisted-operations BFF: reject raw query documents, member không enumerate
được source bị deny, chỉ đọc (không có mutation nào đăng ký)."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock

import httpx
import pytest
from agent.artifacts import InMemoryArtifactRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.knowledge.models import KnowledgeChunk, KnowledgeDocument
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.vault.models import VaultClassification, VaultVisibility
from agent.vault.repository import InMemoryVaultRepository
from agent.workforce.repository import InMemoryWorkforceRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)


@pytest.fixture
def test_app():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    vault_repository = InMemoryVaultRepository()
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        workforce_repository=InMemoryWorkforceRepository(),
        vault_repository=vault_repository,
        model=FakeSDKModel(),
    )
    asyncio.run(seed_cosa_agent_specs(plane.spec_registry))
    app = create_cosa_app(plane)
    return app, plane


async def _seed_published_doc(
    plane, workspace_id: str, *, created_by: str, visibility, classification, content: str
):
    vault_doc = await plane.vault_repository.create_draft(
        workspace_id,
        "handbook",
        created_by=created_by,
        classification=classification,
        visibility=visibility,
    )
    version = await plane.vault_repository.append_version(
        workspace_id,
        vault_doc.document_id,
        object_ref={"path": "handbook.md"},
        checksum_sha256="0" * 64,
        size_bytes=len(content),
        source_uri=f"vault://{vault_doc.document_id}",
        created_by=created_by,
    )
    await plane.vault_repository.update_document_state(
        workspace_id, vault_doc.document_id, "PUBLISHED"
    )

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
    await plane.knowledge_ingestion_service.ingest_normalized_document(doc)


@pytest.mark.asyncio
async def test_raw_query_document_is_rejected(test_app):
    app, _plane = test_app
    override_authenticated_identity(app, role_id="member")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/agent/graphql", json={"query": "{ secrets }"})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_unknown_operation_id_is_rejected(test_app):
    """`operation_id` là pydantic Literal — 1 id lạ bị reject ở validation
    (422) TRƯỚC KHI tới `execute_persisted_operation()` (404 branch ở đó chỉ
    còn reachable cho caller gọi trực tiếp ngoài HTTP, xem
    tests/apps/cosa/graphql/test_workspace_context.py)."""
    app, _plane = test_app
    override_authenticated_identity(app, role_id="member")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/agent/graphql", json={"operationId": "deleteEverything", "variables": {}}
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_unknown_variable_is_rejected(test_app):
    app, _plane = test_app
    override_authenticated_identity(app, role_id="member")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/agent/graphql",
            json={
                "operationId": "enterpriseKnowledgeSearch",
                "variables": {"query": "salary", "raw_sql": "1=1"},
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_oversized_string_variable_is_rejected(test_app):
    app, _plane = test_app
    override_authenticated_identity(app, role_id="member")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/agent/graphql",
            json={"operationId": "enterpriseKnowledgeSearch", "variables": {"query": "x" * 5000}},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_member_cannot_see_denied_source_via_persisted_operation(test_app):
    app, plane = test_app
    workspace_id = "ws-graphql-1"
    await _seed_published_doc(
        plane,
        workspace_id,
        created_by="founder",
        visibility=VaultVisibility.PRIVATE,
        classification=VaultClassification.INTERNAL,
        content="quarterly salary table",
    )
    override_authenticated_identity(
        app, workspace_id=workspace_id, role_id="member", principal_id="member-1"
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/agent/graphql",
            json={"operationId": "enterpriseKnowledgeSearch", "variables": {"query": "lương"}},
        )
        assert response.status_code == 200
        assert response.json()["data"]["enterpriseKnowledgeSearch"]["citations"] == []


@pytest.mark.asyncio
async def test_founder_workspace_context_includes_permitted_knowledge(test_app):
    app, plane = test_app
    workspace_id = "ws-graphql-2"
    await _seed_published_doc(
        plane,
        workspace_id,
        created_by="user:test_user",
        visibility=VaultVisibility.WORKSPACE,
        classification=VaultClassification.INTERNAL,
        content="rủi ro quý này tập trung ở dòng tiền",
    )
    override_authenticated_identity(app, workspace_id=workspace_id, role_id="founder")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/agent/graphql",
            json={"operationId": "workspaceContext", "variables": {"question": "rủi ro quý này"}},
        )
        assert response.status_code == 200
        assert response.json()["data"]["workspaceContext"]["citations"]


@pytest.mark.asyncio
async def test_only_read_operations_are_registered(test_app):
    """Không có mutation resolver nào — persisted operations chỉ 2 cái, cả 2
    đều là read."""
    from apps.cosa.graphql.resolvers import PERSISTED_OPERATIONS

    assert set(PERSISTED_OPERATIONS.keys()) == {
        "workspaceContext",
        "enterpriseKnowledgeSearch",
        "workspaceAuthorityOverview",
    }
