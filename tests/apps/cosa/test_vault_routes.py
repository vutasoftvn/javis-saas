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

_NOT_RELEASED_DETAIL = "Vault document ingestion is not released"


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


def _assert_honest_501(response: httpx.Response) -> None:
    assert response.status_code == 501
    detail = response.json()["detail"]
    assert detail == _NOT_RELEASED_DETAIL
    # Message không được tiết lộ storage topology (bucket, provider, tên bảng DB...).
    lowered = detail.lower()
    for topology_hint in ("bucket", "s3", "object_ref", "vault_repository", "postgres"):
        assert topology_hint not in lowered


@pytest.mark.asyncio
async def test_legacy_upload_ticket_endpoint_returns_not_implemented(test_app) -> None:
    """Task 5 (Truthful MVP Hardening) — Vault chưa có storage/ingestion thật ở
    backend nên route legacy phải trả 501 trung thực, không giả lập ticket."""
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/agent/vault/documents/upload-ticket",
            json={"file_name": "Product Spec.md", "media_type": "text/markdown", "size_bytes": 1024},
        )
        _assert_honest_501(response)


@pytest.mark.asyncio
async def test_list_documents_returns_not_implemented(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/agent/vault/documents")
        _assert_honest_501(response)


@pytest.mark.asyncio
async def test_get_document_returns_not_implemented(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        # Không còn tài liệu thật nào tồn tại — dùng id bất kỳ, phải trả 501
        # (không phải 404, vì 404 sẽ ngụ ý "route hoạt động nhưng không tìm
        # thấy", trong khi sự thật là toàn bộ tính năng chưa được triển khai).
        response = await client.get("/agent/vault/documents/doc_anything")
        _assert_honest_501(response)


@pytest.mark.asyncio
async def test_confirm_upload_does_not_trust_client_declared_checksum(test_app) -> None:
    """Không còn storage thật để đối chiếu checksum/size do client khai báo —
    route phải trả 501 bất kể payload trông hợp lệ thế nào."""
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/agent/vault/documents/doc_anything/confirm",
            json={"checksum_sha256": "sha256:deadbeef", "size_bytes": 1024},
        )
        _assert_honest_501(response)


@pytest.mark.asyncio
async def test_delete_document_returns_not_implemented(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.delete("/agent/vault/documents/doc_anything")
        _assert_honest_501(response)


@pytest.mark.asyncio
async def test_knowledge_graph_returns_not_implemented(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/agent/vault/knowledge/graph")
        _assert_honest_501(response)


@pytest.mark.asyncio
async def test_indexed_sources_returns_not_implemented(test_app) -> None:
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/agent/vault/knowledge/sources")
        _assert_honest_501(response)


@pytest.mark.asyncio
async def test_retrieval_query_returns_not_implemented(test_app) -> None:
    """Không còn giả lập retrieval hit (score=0.95, content="Document content
    for {title}") — route phải trả 501 thay vì kết quả tìm kiếm giả."""
    override_authenticated_identity(test_app, workspace_id="ws_1001", role_id="founder")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/agent/vault/retrieval/query",
            json={"query": "Product", "limit": 5},
        )
        _assert_honest_501(response)
