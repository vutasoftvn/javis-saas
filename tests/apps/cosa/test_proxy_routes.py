from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
import httpx

from agent_core.artifacts import InMemoryArtifactRepository
from agent_core.conversations.repository import InMemoryConversationRepository
from agent_core.coordination.scheduler import RunScheduler
from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent_core.registry.repository import InMemorySpecRegistryRepository
from agent_core.runs.leases import RunLeaseManager
from agent_core.runs.repository import InMemoryRunRepository
from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client


@pytest.fixture
def proxy_setup():
    conv_repo = InMemoryConversationRepository()
    run_repo = InMemoryRunRepository()
    spec_repo = InMemorySpecRegistryRepository()
    stream_repo = InMemoryRunStreamEventRepository()
    art_repo = InMemoryArtifactRepository()

    mock_client = AsyncMock(spec=CompanyServiceClient)
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(),
        repository=run_repo,
        conversation_repository=conv_repo,
        spec_registry=spec_repo,
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=stream_repo,
        artifact_repository=art_repo,
        model=FakeSDKModel(),
    )

    app = create_cosa_app(plane=plane)
    override_authenticated_identity(
        app,
        principal_id="user:alice",
        platform_user_id="alice",
        company_id="company_A",
        workspace_id="ws_A",
    )
    client = TestClient(app)

    return {"app": app, "client": client}


@pytest.mark.asyncio
async def test_connector_and_schedule_proxy_routes(proxy_setup):
    client = proxy_setup["client"]

    # Mock httpx.AsyncClient.post for connector install
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            json={
                "id": "conn_inst_1",
                "companyId": "company_A",
                "workspaceId": "ws_A",
                "connectorKey": "sandbox-read",
                "status": "enabled",
            },
            request=httpx.Request("POST", "http://127.0.0.1:4001/cosa/connectors/install"),
        )

        res = client.post("/agent/connectors/install", json={"connector_key": "sandbox-read"})
        assert res.status_code == 200
        assert res.json()["connectorKey"] == "sandbox-read"
        assert mock_post.called

    # Mock httpx.AsyncClient.post for create schedule
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            json={
                "id": "sched_1",
                "companyId": "company_A",
                "workspaceId": "ws_A",
                "createdBy": "user:alice",
                "scheduleKind": "daily",
                "timezone": "Asia/Ho_Chi_Minh",
                "promptTemplate": "Daily summary",
                "agentProfile": "operations",
                "state": "enabled",
                "createdAt": "2026-08-26T15:00:00Z",
            },
            request=httpx.Request("POST", "http://127.0.0.1:4001/cosa/schedules"),
        )

        res = client.post(
            "/agent/schedules",
            json={
                "schedule_kind": "daily",
                "timezone": "Asia/Ho_Chi_Minh",
                "hour": 9,
                "minute": 0,
                "prompt_template": "Daily summary",
            },
        )
        assert res.status_code == 200
        assert res.json()["id"] == "sched_1"
        assert res.json()["company_id"] == "company_A"
