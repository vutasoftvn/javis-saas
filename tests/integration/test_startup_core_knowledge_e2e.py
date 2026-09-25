"""End-to-end integration test for startup core project-scoped knowledge retrieval."""

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
from agent.knowledge.service import KnowledgeIngestionService
from agent.knowledge.store import InMemoryKnowledgeStore
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

pytestmark = pytest.mark.integration


@pytest.fixture
def e2e_setup():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)

    # Mock projects
    async def _mock_get(path, headers=None):
        if path == "/operations/projects/proj-alpha":
            return {"data": {"id": "proj-alpha", "workspaceId": "ws-alpha", "title": "Project Alpha"}}
        if path == "/operations/projects/proj-beta":
            return {"data": {"id": "proj-beta", "workspaceId": "ws-beta", "title": "Project Beta"}}
        return None

    mock_client.get.side_effect = _mock_get

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
        # Vault chạy in-memory nên knowledge store cũng phải in-memory: nếu để
        # storage_factory tự chọn theo AGENT_DATABASE_URL, PostgresKnowledgeStore
        # sẽ JOIN sang bảng vault.* không tồn tại trong DB test.
        knowledge_ingestion_service=KnowledgeIngestionService(
            InMemoryKnowledgeStore(), vault_repository=vault_repository
        ),
        model=FakeSDKModel(),
    )
    asyncio.run(seed_cosa_agent_specs(plane.spec_registry))
    app = create_cosa_app(plane)
    return {"app": app, "plane": plane}


@pytest.mark.asyncio
async def test_startup_core_knowledge_e2e(e2e_setup):
    app = e2e_setup["app"]
    plane = e2e_setup["plane"]

    # 1. Seed document in workspace Alpha
    vault_doc = await plane.vault_repository.create_draft(
        "ws-alpha",
        "Architecture Clean Slate",
        created_by="founder",
        classification=VaultClassification.INTERNAL,
        visibility=VaultVisibility.WORKSPACE,
    )
    version = await plane.vault_repository.append_version(
        "ws-alpha",
        vault_doc.document_id,
        object_ref={"path": "architecture.md"},
        checksum_sha256="0" * 64,
        size_bytes=120,
        source_uri=f"vault://{vault_doc.document_id}",
        created_by="founder",
    )
    await plane.vault_repository.update_document_state(
        "ws-alpha", vault_doc.document_id, "PUBLISHED"
    )

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    content = "The clean-slate architecture replaces all legacy frameworks with Project Operating Loop."
    doc = KnowledgeDocument(
        id=doc_id,
        workspace_id="ws-alpha",
        title="Architecture Clean Slate",
        ingest_status="published",
        vault_document_id=str(vault_doc.document_id),
        vault_version_id=str(version.version_id),
        access_policy_version=1,
        metadata={"projectId": "proj-alpha"},
        chunks=[
            KnowledgeChunk(
                id=f"chk_{doc_id}_0",
                document_id=doc_id,
                workspace_id="ws-alpha",
                chunk_index=0,
                content=content,
            )
        ],
    )
    await plane.knowledge_ingestion_service.ingest_normalized_document(doc)

    # 2. Query knowledge as ws-alpha member
    override_authenticated_identity(app, workspace_id="ws-alpha", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/agent/knowledge/projects/proj-alpha/search",
            headers={"X-Workspace-Id": "ws-alpha"},
            json={"query": "clean-slate architecture", "limit": 5},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["citations"]) == 1
        cit = data["citations"][0]
        assert cit["documentId"] == str(vault_doc.document_id)
        assert cit["versionId"] == str(version.version_id)
        assert cit["title"] == "Architecture Clean Slate"
        assert "clean-slate" in cit["excerpt"]

        # 3. Cross-workspace isolation: ws-beta cannot search proj-alpha (returns 404)
        override_authenticated_identity(app, workspace_id="ws-beta", role_id="founder")
        res_cross = await client.post(
            "/agent/knowledge/projects/proj-alpha/search",
            headers={"X-Workspace-Id": "ws-beta"},
            json={"query": "clean-slate", "limit": 5},
        )
        assert res_cross.status_code == 404

        # 4. Searching proj-beta in ws-beta yields 0 citations for ws-alpha doc
        res_beta = await client.post(
            "/agent/knowledge/projects/proj-beta/search",
            headers={"X-Workspace-Id": "ws-beta"},
            json={"query": "clean-slate", "limit": 5},
        )
        assert res_beta.status_code == 200
        assert len(res_beta.json()["citations"]) == 0
