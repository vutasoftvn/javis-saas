from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient

from agent_core.artifacts import InMemoryArtifactRepository, WorkspaceArtifact
from agent_core.conversations.models import ConversationRecord
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
def test_setup():
    conv_repo = InMemoryConversationRepository()
    run_repo = InMemoryRunRepository()
    stream_repo = InMemoryRunStreamEventRepository()
    art_repo = InMemoryArtifactRepository()

    mock_client = AsyncMock(spec=CompanyServiceClient)
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(),
        repository=run_repo,
        conversation_repository=conv_repo,
        spec_registry=InMemorySpecRegistryRepository(),
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

    return {
        "app": app,
        "client": client,
        "conv_repo": conv_repo,
        "art_repo": art_repo,
    }


@pytest.mark.asyncio
async def test_list_artifacts_scoped_and_lineage(test_setup):
    client = test_setup["client"]
    conv_repo = test_setup["conv_repo"]
    art_repo = test_setup["art_repo"]
    app = test_setup["app"]

    # 1. Create conversation for Company A, Workspace A
    conv = ConversationRecord(
        conversation_id="conv_art_1",
        company_id="company_A",
        workspace_id="ws_A",
        created_by_principal="user:alice",
        title="Artifact Test",
    )
    await conv_repo.create_conversation(conv)

    # 2. Add two artifacts to conv_art_1
    art1 = WorkspaceArtifact(
        company_id="company_A",
        workspace_id="ws_A",
        conversation_id="conv_art_1",
        run_id="run_101",
        source_message_id="msg_101",
        artifact_kind="assistant_output",
        display_name="Final Analysis",
        media_type="text/plain",
        object_ref="artifact://run/run_101/final",
    )
    art2 = WorkspaceArtifact(
        company_id="company_A",
        workspace_id="ws_A",
        conversation_id="conv_art_1",
        run_id="run_101",
        source_message_id="msg_101",
        artifact_kind="table",
        display_name="Quarterly Summary Table",
        media_type="application/json",
        object_ref="artifact://table/quarterly.json",
    )
    await art_repo.create(art1)
    await art_repo.create(art2)

    # 3. Query artifacts via API
    res = client.get("/agent/conversations/conv_art_1/artifacts")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    display_names = [i["display_name"] for i in items]
    assert "Final Analysis" in display_names
    assert "Quarterly Summary Table" in display_names
    assert items[0]["run_id"] == "run_101"
    assert items[0]["source_message_id"] == "msg_101"

    # 4. Check that SessionView also includes artifacts
    session_res = client.get("/agent/sessions/conv_art_1")
    assert session_res.status_code == 200
    session_data = session_res.json()
    assert len(session_data["artifacts"]) == 2

    # 5. Query from another tenant -> 404
    override_authenticated_identity(
        app,
        principal_id="user:bob",
        platform_user_id="bob",
        company_id="company_B",
        workspace_id="ws_B",
    )
    denied = client.get("/agent/conversations/conv_art_1/artifacts")
    assert denied.status_code == 404
