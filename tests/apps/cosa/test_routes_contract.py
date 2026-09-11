from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    configure_mock_client_project_access,
    stub_active_tenant_policy_client,
)
from agent.runs.repository import InMemoryRunRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.coordination.scheduler import RunScheduler
from agent.runs.leases import RunLeaseManager
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent.artifacts import InMemoryArtifactRepository
from agent.workforce.repository import InMemoryWorkforceRepository
from agent.vault.repository import InMemoryVaultRepository
from agent_testkit.fake_sdk_model import FakeSDKModel


@pytest.fixture
def cosa_app():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    configure_mock_client_project_access(mock_client)
    plane = build_cosa_agent_plane(
        company_client=mock_client,
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
    return create_cosa_app(plane)


@pytest.mark.asyncio
async def test_conversations_routes_contract(cosa_app):
    override_authenticated_identity(cosa_app, workspace_id="ws_contract_1")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cosa_app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/agent/conversations?project_id=proj_contract_1")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["items"] == []


@pytest.mark.asyncio
async def test_workforce_runs_routes_contract(cosa_app):
    override_authenticated_identity(cosa_app, workspace_id="ws_contract_1")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cosa_app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/agent/workforce/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
