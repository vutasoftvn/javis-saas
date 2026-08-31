"""End-to-End HTTP Integration Test for Vault Subsystem."""

from __future__ import annotations

import asyncio

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
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    StubCompanyServiceClient,
    stub_active_tenant_policy_client,
)


@pytest.fixture
def e2e_app():
    plane = build_cosa_agent_plane(
        company_client=StubCompanyServiceClient(),
        tenant_policy_client=stub_active_tenant_policy_client(),
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
async def test_full_vault_lifecycle_e2e(e2e_app) -> None:
    workspace_id = "ws_e2e_vault"
    override_authenticated_identity(e2e_app, workspace_id=workspace_id, role_id="founder")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=e2e_app),
        base_url="http://test",
    ) as client:
        # 1. Initially empty documents list
        list_res = await client.get("/agent/vault/documents")
        assert list_res.status_code == 200
        assert list_res.json()["meta"]["data_state"] == "empty"
        assert list_res.json()["data"] == []

        # 2. Create upload ticket
        ticket_res = await client.post(
            "/agent/vault/documents/upload-ticket",
            json={
                "file_name": "Quarterly Strategy.pdf",
                "media_type": "application/pdf",
                "size_bytes": 4096,
            },
        )
        assert ticket_res.status_code == 200
        ticket = ticket_res.json()["data"]
        doc_id = ticket["document_id"]
        assert doc_id is not None

        # 3. Confirm upload
        confirm_res = await client.post(
            f"/agent/vault/documents/{doc_id}/confirm",
            json={
                "checksum_sha256": "sha256:1122334455",
                "size_bytes": 4096,
            },
        )
        assert confirm_res.status_code == 200
        confirmed = confirm_res.json()["data"]
        assert confirmed["state"] == "INDEXED"
        assert confirmed["current_version_id"] is not None

        # 4. Get document detail
        detail_res = await client.get(f"/agent/vault/documents/{doc_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()["data"]
        assert detail["title"] == "Quarterly Strategy.pdf"
        assert len(detail["versions"]) == 1

        # 5. List indexed sources
        sources_res = await client.get("/agent/vault/knowledge/sources")
        assert sources_res.status_code == 200
        sources = sources_res.json()["data"]
        assert len(sources) == 1
        assert sources[0]["source_id"] == doc_id

        # 6. Knowledge graph
        graph_res = await client.get("/agent/vault/knowledge/graph")
        assert graph_res.status_code == 200
        graph = graph_res.json()["data"]
        assert len(graph["nodes"]) == 1
        assert graph["nodes"][0]["id"] == doc_id

        # 7. Retrieval query
        query_res = await client.post(
            "/agent/vault/retrieval/query",
            json={"query": "Strategy", "limit": 10},
        )
        assert query_res.status_code == 200
        hits = query_res.json()["data"]
        assert len(hits) == 1
        assert hits[0]["title"] == "Quarterly Strategy.pdf"

        # 8. Delete document
        delete_res = await client.delete(f"/agent/vault/documents/{doc_id}")
        assert delete_res.status_code == 200
        assert delete_res.json()["data"]["deleted"] is True

        # 9. Verify document is gone
        list_empty = await client.get("/agent/vault/documents")
        assert list_empty.status_code == 200
        assert list_empty.json()["meta"]["data_state"] == "empty"
        assert list_empty.json()["data"] == []
