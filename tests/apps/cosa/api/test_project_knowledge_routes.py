"""Tests for Project-scoped Knowledge Search API Routes."""

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
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(client)

    # Mock project lookup
    async def _mock_get(path, headers=None):
        if path == "/operations/projects/proj-valid-1":
            return {"data": {"id": "proj-valid-1", "workspaceId": "ws-1", "title": "Project One"}}
        if path == "/operations/projects/proj-foreign-2":
            return {"data": {"id": "proj-foreign-2", "workspaceId": "ws-other", "title": "Foreign Project"}}
        return None

    client.get.side_effect = _mock_get
    return client


@pytest.fixture
def test_app(mock_company_client):
    vault_repository = InMemoryVaultRepository()
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
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


async def _seed_doc(
    plane,
    workspace_id: str,
    *,
    title: str,
    content: str,
    created_by: str = "founder",
    visibility=VaultVisibility.WORKSPACE,
    project_id: str | None = None,
):
    vault_doc = await plane.vault_repository.create_draft(
        workspace_id,
        title,
        created_by=created_by,
        classification=VaultClassification.INTERNAL,
        visibility=visibility,
    )
    version = await plane.vault_repository.append_version(
        workspace_id,
        vault_doc.document_id,
        object_ref={"path": f"{title}.md"},
        checksum_sha256="0" * 64,
        size_bytes=len(content),
        source_uri=f"vault://{vault_doc.document_id}",
        created_by=created_by,
    )
    await plane.vault_repository.update_document_state(
        workspace_id, vault_doc.document_id, "PUBLISHED"
    )

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    metadata = {}
    if project_id:
        metadata["projectId"] = project_id

    doc = KnowledgeDocument(
        id=doc_id,
        workspace_id=workspace_id,
        title=title,
        ingest_status="published",
        vault_document_id=str(vault_doc.document_id),
        vault_version_id=str(version.version_id),
        access_policy_version=1,
        metadata=metadata,
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
    return doc


@pytest.mark.asyncio
async def test_search_foreign_project_returns_404(test_app):
    app, _plane = test_app
    override_authenticated_identity(app, workspace_id="ws-1", role_id="founder")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # foreign project belongs to ws-other, not ws-1
        response = client.post(
            "/agent/knowledge/projects/proj-foreign-2/search",
            headers={"X-Workspace-Id": "ws-1"},
            json={"query": "pricing", "limit": 5},
        )
        assert (await response).status_code == 404

        # non-existent project also returns 404
        response_missing = await client.post(
            "/agent/knowledge/projects/proj-does-not-exist/search",
            headers={"X-Workspace-Id": "ws-1"},
            json={"query": "pricing", "limit": 5},
        )
        assert response_missing.status_code == 404


@pytest.mark.asyncio
async def test_search_project_knowledge_success_with_citations_and_provenance(test_app):
    app, plane = test_app
    workspace_id = "ws-1"
    await _seed_doc(
        plane,
        workspace_id,
        title="Pricing Strategy",
        content="Our pricing model is SaaS tiered pricing at $49/mo and $99/mo.",
        project_id="proj-valid-1",
    )
    override_authenticated_identity(app, workspace_id=workspace_id, role_id="founder")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/agent/knowledge/projects/proj-valid-1/search",
            headers={"X-Workspace-Id": workspace_id},
            json={"query": "pricing", "limit": 5},
        )
        assert response.status_code == 200
        result = response.json()

        # Check citations format
        assert "citations" in result
        assert len(result["citations"]) > 0
        citation = result["citations"][0]
        assert citation.keys() >= {"documentId", "versionId", "chunkId", "title", "excerpt"}
        assert citation["title"] == "Pricing Strategy"
        assert "pricing" in citation["excerpt"].lower()

        # Check items format
        assert "items" in result
        assert len(result["items"]) > 0
        item = result["items"][0]
        assert "text" in item
        assert "citations" in item
        assert item["citations"][0]["title"] == "Pricing Strategy"


@pytest.mark.asyncio
async def test_search_does_not_leak_other_project_docs(test_app):
    app, plane = test_app
    workspace_id = "ws-1"
    # Seed doc for a different project
    await _seed_doc(
        plane,
        workspace_id,
        title="Other Project Secret",
        content="This is pricing for another project only.",
        project_id="proj-other-secret",
    )
    override_authenticated_identity(app, workspace_id=workspace_id, role_id="founder")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/agent/knowledge/projects/proj-valid-1/search",
            headers={"X-Workspace-Id": workspace_id},
            json={"query": "pricing", "limit": 5},
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["citations"]) == 0
