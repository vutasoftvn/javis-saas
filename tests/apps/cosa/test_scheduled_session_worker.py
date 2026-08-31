from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from agent.artifacts import InMemoryArtifactRepository
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response

from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.main import dispatch_one_task
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    fake_active_tenant_policy_client,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest_asyncio.fixture
async def worker_setup():
    conv_repo = InMemoryConversationRepository()
    run_repo = InMemoryRunRepository()
    spec_repo = InMemorySpecRegistryRepository()
    stream_repo = InMemoryRunStreamEventRepository()
    art_repo = InMemoryArtifactRepository()
    scheduler = RunScheduler()
    lease_mgr = RunLeaseManager()

    mock_client = AsyncMock(spec=CompanyServiceClient)

    configure_mock_client_allows_data_use(mock_client)
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
        model=FakeSDKModel(responses=[text_response("Scheduled report analysis complete.")]),
    )
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
        skillpacks_root=REPO_ROOT / "skillpacks",
    )


    return {
        "plane": plane,
        "conv_repo": conv_repo,
        "scheduler": scheduler,
        "art_repo": art_repo,
    }


@pytest.mark.asyncio
async def test_worker_dispatches_scheduled_session_task(worker_setup):
    plane = worker_setup["plane"]
    conv_repo = worker_setup["conv_repo"]
    scheduler = worker_setup["scheduler"]
    art_repo = worker_setup["art_repo"]

    # 1. Enqueue scheduled session task
    await scheduler.schedule(
        target_spec_id="cosa.schedule-execution",
        target_spec_kind="agent",
        input_payload={
            "task_type": "scheduled_session",
            "schedule_execution_id": "exec_test_101",
            "company_id": "company_sched",
            "workspace_id": "ws_sched",
            "prompt_template": "Run quarterly risk review",
            "agent_profile": "operations",
        },
    )

    # 2. Poll due tasks
    due = await scheduler.poll_due_tasks(worker_id="test-worker", limit=1)
    assert len(due) == 1
    task_to_run = due[0]

    # 3. Dispatch task via worker loop handler
    await dispatch_one_task(plane, task_to_run)

    # 4. Verify conversation was created
    conversations, total = await conv_repo.list_conversations(workspace_id="ws_sched",
    )
    assert total == 1
    assert len(conversations) == 1
    sched_conv = conversations[0]
    assert sched_conv.created_by_principal == "service:scheduler"
    assert "Scheduled execution:" in sched_conv.title


    # 5. Verify messages in conversation (user prompt + assistant output)
    messages = await conv_repo.list_messages(sched_conv.conversation_id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Run quarterly risk review"
    assert messages[1].role == "assistant"
    assert "Scheduled report analysis complete." in messages[1].content
    assert messages[1].status == "completed"

    # 6. Verify WorkspaceArtifact was created for this scheduled conversation
    artifacts = await art_repo.list_for_conversation(workspace_id="ws_sched",
        conversation_id=sched_conv.conversation_id,
    )
    assert len(artifacts) == 1
    assert artifacts[0].artifact_kind == "assistant_output"
