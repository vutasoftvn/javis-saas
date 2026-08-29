import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from unittest.mock import AsyncMock

from agent.artifacts import InMemoryArtifactRepository
from agent.conversations.models import ConversationRecord, MessageRecord

from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.models import RunRecord, RunStatus
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository, RunStreamEventRecord
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.api.app import create_cosa_app
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
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
        
        workspace_id="ws_A",
    )
    client = TestClient(app)

    return {
        "app": app,
        "client": client,
        "conv_repo": conv_repo,
        "run_repo": run_repo,
        "stream_repo": stream_repo,
    }



@pytest.mark.asyncio
async def test_session_view_owner_and_tenancy(test_setup):
    client = test_setup["client"]
    conv_repo = test_setup["conv_repo"]
    run_repo = test_setup["run_repo"]
    stream_repo = test_setup["stream_repo"]

    # 1. Create conversation for Company A, Workspace A

    conv_a = ConversationRecord(
        conversation_id="conv_a_123",
        
        workspace_id="ws_A",
        created_by_principal="user:alice",
        title="Đối chiếu giao dịch",
        active_agent_profile="operations",
    )
    await conv_repo.create_conversation(conv_a)

    # Add message
    msg = MessageRecord(
        message_id="msg_1",
        conversation_id="conv_a_123",
        role="user",
        content="Hãy đối chiếu báo cáo",
    )
    await conv_repo.add_message(msg)

    # Add run and stream events
    run = RunRecord(
        run_id="run_a_1",
        
        workspace_id="ws_A",
        conversation_id="conv_a_123",
        principal="user:alice",
        root_executable_id="cosa.operations",
        root_executable_kind="agent",
        status=RunStatus.RUNNING,
    )
    await run_repo.create_run(run)

    await stream_repo.append(
        RunStreamEventRecord(
            run_id="run_a_1",
            conversation_id="conv_a_123",
            event_type="run.started",
            payload={"run_id": "run_a_1", "secret_ref": "secret://hide-me"},
        )
    )
    await stream_repo.append(
        RunStreamEventRecord(
            run_id="run_a_1",
            conversation_id="conv_a_123",
            event_type="reasoning.status",
            payload={"status": "thinking", "access_token": "token123"},
        )
    )

    # 2. Query Session View as Company A
    res = client.get("/agent/sessions/conv_a_123")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "conv_a_123"
    assert data["workspace_id"] == "ws_A"
    assert data["title"] == "Đối chiếu giao dịch"
    assert data["status"] == "running"
    assert data["latest_run"]["run_id"] == "run_a_1"
    assert len(data["messages"]) == 1
    assert len(data["timeline"]) == 2
    # Verify redaction: secret_ref and access_token must NOT be present
    assert "secret_ref" not in data["timeline"][0]["payload"]
    assert "access_token" not in data["timeline"][1]["payload"]

    # 3. Query as Company B / Workspace B -> Expect 404
    override_authenticated_identity(
        test_setup["app"],
        principal_id="user:bob",
        platform_user_id="bob",
        
        workspace_id="ws_B",
    )
    res_b = client.get("/agent/sessions/conv_a_123")
    assert res_b.status_code == 404



@pytest.mark.asyncio
async def test_session_timeline_pagination_and_redaction(test_setup):
    client = test_setup["client"]
    conv_repo = test_setup["conv_repo"]
    stream_repo = test_setup["stream_repo"]

    conv = ConversationRecord(
        conversation_id="conv_time_1",
        
        workspace_id="ws_A",
        created_by_principal="user:alice",
        title="Timeline Test",
    )
    await conv_repo.create_conversation(conv)

    ev1 = await stream_repo.append(
        RunStreamEventRecord(
            run_id="run_1",
            conversation_id="conv_time_1",
            event_type="run.started",
            payload={"step": 1},
        )
    )
    ev2 = await stream_repo.append(
        RunStreamEventRecord(
            run_id="run_1",
            conversation_id="conv_time_1",
            event_type="reasoning.status",
            payload={"step": 2, "authorization_id": "auth_999"},
        )
    )
    ev3 = await stream_repo.append(
        RunStreamEventRecord(
            run_id="run_1",
            conversation_id="conv_time_1",
            event_type="run.completed",
            payload={"step": 3, "result": "done"},
        )
    )

    # Query all
    res = client.get("/agent/sessions/conv_time_1/timeline")
    assert res.status_code == 200
    events = res.json()
    assert len(events) == 3
    assert "authorization_id" not in events[1]["payload"]

    # Query after_sequence
    res_after = client.get(f"/agent/sessions/conv_time_1/timeline?after_sequence={ev1.sequence}")
    assert res_after.status_code == 200
    events_after = res_after.json()
    assert len(events_after) == 2
    assert events_after[0]["sequence"] == ev2.sequence

    # Query with limit > 100 -> 422
    res_limit = client.get("/agent/sessions/conv_time_1/timeline?limit=101")
    assert res_limit.status_code == 422


@pytest.mark.asyncio
async def test_session_status_derivation(test_setup):
    client = test_setup["client"]
    conv_repo = test_setup["conv_repo"]
    stream_repo = test_setup["stream_repo"]

    # Case A: approval required -> waiting_approval
    conv_a = ConversationRecord(
        conversation_id="conv_approval",
        
        workspace_id="ws_A",
        created_by_principal="user:alice",
        title="Approval Test",
    )
    await conv_repo.create_conversation(conv_a)
    await stream_repo.append(
        RunStreamEventRecord(
            run_id="run_app",
            conversation_id="conv_approval",
            event_type="approval.required",
            payload={"approval_id": "app_1"},
        )
    )
    res_a = client.get("/agent/sessions/conv_approval")
    assert res_a.json()["status"] == "waiting_approval"

    # Case B: run.failed -> failed
    conv_f = ConversationRecord(
        conversation_id="conv_failed",
        
        workspace_id="ws_A",
        created_by_principal="user:alice",
        title="Fail Test",
    )
    await conv_repo.create_conversation(conv_f)
    await stream_repo.append(
        RunStreamEventRecord(
            run_id="run_f",
            conversation_id="conv_failed",
            event_type="run.failed",
            payload={"error": "failed"},
        )
    )
    res_f = client.get("/agent/sessions/conv_failed")
    assert res_f.json()["status"] == "failed"

    # Case C: run.completed -> completed
    conv_c = ConversationRecord(
        conversation_id="conv_completed",
        
        workspace_id="ws_A",
        created_by_principal="user:alice",
        title="Complete Test",
    )
    await conv_repo.create_conversation(conv_c)
    await stream_repo.append(
        RunStreamEventRecord(
            run_id="run_c",
            conversation_id="conv_completed",
            event_type="run.completed",
            payload={"status": "success"},
        )
    )
    res_c = client.get("/agent/sessions/conv_completed")
    assert res_c.json()["status"] == "completed"
