"""In-process HTTP integration coverage for the Vault subsystem.

Task 5 (Truthful MVP Hardening, 2026-09-01) — trước đây file này chứng minh
một "full lifecycle" (ticket → confirm → INDEXED → sources → graph →
retrieval hit → delete) nhưng đó chỉ là DB tạm + state giả, không có
storage/indexing/retrieval thật phía sau — không chứng minh được gì về một
upload thật. Suite giờ xác nhận containment: mọi route `/agent/vault/*` trả
501 trung thực, không route nào còn giả lập một vòng đời tài liệu không tồn
tại.
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
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    StubCompanyServiceClient,
    stub_active_tenant_policy_client,
)

pytestmark = pytest.mark.integration

_NOT_RELEASED_DETAIL = "Vault document ingestion is not released"


@pytest.fixture
def agent_app():
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
async def test_vault_routes_are_honestly_unimplemented_end_to_end(agent_app) -> None:
    """Không còn upload/index/retrieval giả — mọi entrypoint public của Vault
    phải trả 501 với message không tiết lộ storage topology, kể cả khi gọi
    qua ASGI transport thật (in-process HTTP) thay vì gọi thẳng hàm Python."""
    workspace_id = "ws_e2e_vault"
    override_authenticated_identity(agent_app, workspace_id=workspace_id, role_id="founder")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=agent_app),
        base_url="http://test",
    ) as client:
        list_res = await client.get("/agent/vault/documents")
        assert list_res.status_code == 501
        assert list_res.json()["detail"] == _NOT_RELEASED_DETAIL

        ticket_res = await client.post(
            "/agent/vault/documents/upload-ticket",
            json={
                "file_name": "Quarterly Strategy.pdf",
                "media_type": "application/pdf",
                "size_bytes": 4096,
            },
        )
        assert ticket_res.status_code == 501
        assert ticket_res.json()["detail"] == _NOT_RELEASED_DETAIL

        confirm_res = await client.post(
            "/agent/vault/documents/doc_anything/confirm",
            json={"checksum_sha256": "sha256:1122334455", "size_bytes": 4096},
        )
        assert confirm_res.status_code == 501
        assert confirm_res.json()["detail"] == _NOT_RELEASED_DETAIL

        detail_res = await client.get("/agent/vault/documents/doc_anything")
        assert detail_res.status_code == 501

        sources_res = await client.get("/agent/vault/knowledge/sources")
        assert sources_res.status_code == 501

        graph_res = await client.get("/agent/vault/knowledge/graph")
        assert graph_res.status_code == 501

        query_res = await client.post(
            "/agent/vault/retrieval/query",
            json={"query": "Strategy", "limit": 10},
        )
        assert query_res.status_code == 501
        assert query_res.json()["detail"] == _NOT_RELEASED_DETAIL

        delete_res = await client.delete("/agent/vault/documents/doc_anything")
        assert delete_res.status_code == 501
