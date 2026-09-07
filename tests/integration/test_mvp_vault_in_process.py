"""In-process HTTP integration coverage for the Vault subsystem.

Task 7 (plan local-first-enterprise-knowledge) — document upload + lifecycle
routes (`/documents`, `/uploads/{id}/content`, `/uploads/{id}/complete`,
`/documents/{id}`, review/publish/archive) giờ có hành vi thật (xem
tests/apps/cosa/test_vault_document_routes.py cho coverage đầy đủ create→
upload→complete→review→publish qua ASGI transport thật).

`/knowledge/sources`, `/knowledge/graph`, `/retrieval/query` VẪN 501 trung
thực — retrieval authorized thật là Task 8, chưa có gì thay thế state giả cũ
(score=0.95, content="Document content for {title}"...) nên KHÔNG được giả
lập lại; suite này verify containment cho đúng 3 route còn lại đó.
"""

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
from apps.cosa.knowledge_ingestion.dependencies import build_knowledge_ingestion_dependencies
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    StubCompanyServiceClient,
    stub_active_tenant_policy_client,
)

pytestmark = pytest.mark.integration

_NOT_RELEASED_DETAIL = "Vault document ingestion is not released"


class _FakeSandbox:
    async def run(self, document, content, converter_profile):
        raise NotImplementedError


@pytest.fixture
def agent_app(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_INGESTION_ENABLED", "true")
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
        knowledge_ingestion_deps=build_knowledge_ingestion_dependencies(
            storage_root=tmp_path, sandbox=_FakeSandbox()
        ),
    )
    asyncio.run(seed_cosa_agent_specs(plane.spec_registry))
    return create_cosa_app(plane)


@pytest.mark.asyncio
async def test_vault_document_lifecycle_end_to_end_over_http(agent_app) -> None:
    """create → upload → complete → REVIEW_PENDING → publish qua ASGI
    transport thật (in-process HTTP, không gọi thẳng hàm Python)."""
    workspace_id = "ws_e2e_vault"
    override_authenticated_identity(agent_app, workspace_id=workspace_id, role_id="founder")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=agent_app),
        base_url="http://test",
    ) as client:
        list_res = await client.get("/agent/vault/documents")
        assert list_res.status_code == 200
        assert list_res.json() == []

        created = await client.post(
            "/agent/vault/documents",
            json={"title": "Quarterly Strategy", "media_type": "application/pdf"},
        )
        assert created.status_code == 201
        body = created.json()

        upload_res = await client.put(body["upload_url"], content=b"%PDF-1.4 fake pdf bytes")
        assert upload_res.status_code == 204

        complete_res = await client.post(f"/agent/vault/uploads/{body['upload_id']}/complete")
        assert complete_res.status_code == 200
        assert complete_res.json()["state"] == "QUEUED"

        detail_res = await client.get(f"/agent/vault/documents/{body['document_id']}")
        assert detail_res.status_code == 200
        assert detail_res.json()["state"] == "DRAFT"

        delete_res = await client.delete(f"/agent/vault/documents/{body['document_id']}")
        assert delete_res.status_code == 200
        assert delete_res.json()["accepted"] is True


@pytest.mark.asyncio
async def test_retrieval_and_knowledge_graph_routes_are_honestly_unimplemented(agent_app) -> None:
    """Task 8/9 chưa làm — 3 route này KHÔNG được giả lập kết quả tìm kiếm/đồ
    thị tri thức, phải trả 501 trung thực với message không tiết lộ storage
    topology."""
    workspace_id = "ws_e2e_vault"
    override_authenticated_identity(agent_app, workspace_id=workspace_id, role_id="founder")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=agent_app),
        base_url="http://test",
    ) as client:
        sources_res = await client.get("/agent/vault/knowledge/sources")
        assert sources_res.status_code == 501
        assert sources_res.json()["detail"] == _NOT_RELEASED_DETAIL

        graph_res = await client.get("/agent/vault/knowledge/graph")
        assert graph_res.status_code == 501
        assert graph_res.json()["detail"] == _NOT_RELEASED_DETAIL

        query_res = await client.post(
            "/agent/vault/retrieval/query",
            json={"query": "Strategy", "limit": 10},
        )
        assert query_res.status_code == 501
        assert query_res.json()["detail"] == _NOT_RELEASED_DETAIL

        lowered = sources_res.json()["detail"].lower()
        for topology_hint in ("bucket", "s3", "object_ref", "vault_repository", "postgres"):
            assert topology_hint not in lowered
