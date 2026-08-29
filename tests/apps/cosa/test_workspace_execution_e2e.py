from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient

from agent.artifacts import InMemoryArtifactRepository, WorkspaceArtifact
from agent.conversations.models import ConversationRecord, MessageRecord
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository, RunStreamEventRecord
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response
from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.app import create_cosa_app
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.main import dispatch_one_task
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import fake_active_tenant_policy_client


import pytest_asyncio

@pytest_asyncio.fixture
async def e2e_setup():

    conv_repo = InMemoryConversationRepository()
    run_repo = InMemoryRunRepository()
    spec_repo = InMemorySpecRegistryRepository()
    await seed_cosa_agent_specs(spec_repo)
    stream_repo = InMemoryRunStreamEventRepository()
    art_repo = InMemoryArtifactRepository()
    scheduler = RunScheduler()
    lease_mgr = RunLeaseManager()

    mock_client = AsyncMock(spec=CompanyServiceClient)
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(),
        repository=run_repo,
        conversation_repository=conv_repo,
        spec_registry=spec_repo,
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=scheduler,
        lease_client=lease_mgr,
        stream_event_repository=stream_repo,
        artifact_repository=art_repo,
        model=FakeSDKModel(responses=[text_response("E2E analysis verified.")]),
    )

    app = create_cosa_app(plane=plane)
    override_authenticated_identity(
        app,
        principal_id="user:alice",
        platform_user_id="alice",
        
        workspace_id="ws_E2E",
    )
    client = TestClient(app)

    return {
        "plane": plane,
        "app": app,
        "client": client,
        "conv_repo": conv_repo,
        "run_repo": run_repo,
        "stream_repo": stream_repo,
        "art_repo": art_repo,
        "scheduler": scheduler,
    }


@pytest.mark.asyncio
async def test_end_to_end_workspace_execution_flow(e2e_setup):
    client = e2e_setup["client"]
    plane = e2e_setup["plane"]
    conv_repo = e2e_setup["conv_repo"]
    stream_repo = e2e_setup["stream_repo"]
    art_repo = e2e_setup["art_repo"]
    scheduler = e2e_setup["scheduler"]
    app = e2e_setup["app"]

    # 1. Dispatch scheduled session task via worker
    task = await scheduler.schedule(
        target_spec_id="cosa.schedule-execution",
        target_spec_kind="agent",
        input_payload={
            "task_type": "scheduled_session",
            "schedule_execution_id": "exec_e2e_1",
            "company_id": "company_E2E",
            "workspace_id": "ws_E2E",
            "prompt_template": "Weekly operational health check",
            "agent_profile": "operations",
        },
    )

    due = await scheduler.poll_due_tasks(worker_id="e2e-worker", limit=1)
    assert len(due) == 1
    await dispatch_one_task(plane, due[0])

    # 2. Get created conversation
    convs, total = await conv_repo.list_conversations(
        workspace_id="ws_E2E",
    )
    assert total == 1
    conversation = convs[0]
    conv_id = conversation.conversation_id

    # 3. Add stream event with sensitive data to test event redaction
    await stream_repo.append(
        RunStreamEventRecord(
            run_id="run_e2e",
            conversation_id=conv_id,
            event_type="approval.required",
            payload={
                "approval_id": "app_999",
                "secret_ref": "secret://sensitive-vault-path",
                "delegation_token": "raw-jwt-secret-payload",
                "summary": "Approval for financial transaction",
            },
        )
    )

    # 4. Fetch SessionView via canonical endpoint
    session_res = client.get(f"/agent/sessions/{conv_id}")
    assert session_res.status_code == 200
    session_view = session_res.json()

    assert session_view["id"] == conv_id
    assert session_view["workspace_id"] == "ws_E2E"
    assert session_view["status"] == "waiting_approval"

    # Verify artifacts included
    assert len(session_view["artifacts"]) == 1
    artifact = session_view["artifacts"][0]
    assert artifact["artifact_kind"] == "assistant_output"
    assert artifact["object_ref"].startswith("artifact://run/")

    # 5. Fetch Session timeline and verify security redaction
    timeline_res = client.get(f"/agent/sessions/{conv_id}/timeline")
    assert timeline_res.status_code == 200
    events = timeline_res.json()
    assert len(events) >= 1

    for ev in events:
        payload = ev["payload"]
        assert "secret_ref" not in payload
        assert "delegation_token" not in payload
        assert "access_token" not in payload

    # 6. Verify Tenant B is denied access
    override_authenticated_identity(
        app,
        principal_id="user:bob",
        platform_user_id="bob",
        
        workspace_id="ws_Other",
    )
    denied = client.get(f"/agent/sessions/{conv_id}")
    assert denied.status_code == 404
