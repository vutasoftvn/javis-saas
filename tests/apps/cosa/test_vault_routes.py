from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from agent.artifacts import InMemoryArtifactRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
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
        vault_repository=InMemoryVaultRepository(),
        model=FakeSDKModel(),
    )
    asyncio.run(seed_cosa_agent_specs(plane.spec_registry))
    return create_cosa_app(plane)


@pytest.mark.asyncio
async def test_empty_documents_roster_is_honest(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        res = await client.get("/agent/vault/documents")
        assert res.status_code == 200
        data = res.json()
        assert data["meta"]["data_state"] == "empty"
        assert data["data"] == []


@pytest.mark.asyncio
async def test_upload_ticket_and_confirm_lifecycle(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        # 1. Create upload ticket
        ticket_res = await client.post(
            "/agent/vault/documents/upload-ticket",
            json={"file_name": "Product Spec.md", "media_type": "text/markdown", "size_bytes": 1024},
        )
        assert ticket_res.status_code == 200
        ticket = ticket_res.json()["data"]
        doc_id = ticket["document_id"]
        assert doc_id is not None

        # 2. Confirm upload
        confirm_res = await client.post(
            f"/agent/vault/documents/{doc_id}/confirm",
            json={"checksum_sha256": "sha256:fedcba", "size_bytes": 1024},
        )
        assert confirm_res.status_code == 200
        doc = confirm_res.json()["data"]
        assert doc["state"] == "INDEXED"
        assert doc["current_version_id"] is not None

        # 3. Get document detail
        detail_res = await client.get(f"/agent/vault/documents/{doc_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()["data"]
        assert detail["title"] == "Product Spec.md"
        assert len(detail["versions"]) == 1

        # 4. Search and retrieval query
        query_res = await client.post(
            "/agent/vault/retrieval/query",
            json={"query": "Product", "limit": 5},
        )
        assert query_res.status_code == 200
        hits = query_res.json()["data"]
        assert len(hits) == 1
        assert hits[0]["title"] == "Product Spec.md"


@pytest.mark.asyncio
async def test_tenant_isolation_cannot_see_or_delete_other_workspace_document(test_app) -> None:
    # 1. Workspace A creates and confirms document
    override_authenticated_identity(test_app, workspace_id="ws_A", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client_a:
        ticket_res = await client_a.post(
            "/agent/vault/documents/upload-ticket",
            json={"file_name": "Secret WS A.pdf", "media_type": "application/pdf", "size_bytes": 2048},
        )
        doc_id_a = ticket_res.json()["data"]["document_id"]

    # 2. Workspace B lists documents (must be empty)
    override_authenticated_identity(test_app, workspace_id="ws_B", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client_b:
        list_res = await client_b.get("/agent/vault/documents")
        assert list_res.status_code == 200
        assert list_res.json()["data"] == []

        # 3. Workspace B attempts to get Workspace A's document (must be 404)
        get_res = await client_b.get(f"/agent/vault/documents/{doc_id_a}")
        assert get_res.status_code == 404

        # 4. Workspace B attempts to delete Workspace A's document (must be 404)
        del_res = await client_b.delete(f"/agent/vault/documents/{doc_id_a}")
        assert del_res.status_code == 404
