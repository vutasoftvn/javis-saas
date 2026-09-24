from pathlib import Path
from unittest.mock import AsyncMock, patch

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
from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.company.project_team_client import ProjectAgentRunAuthority, SpecRef
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.handlers import execute_scheduled_session_task
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
    # Giữ response mock chung cho các endpoint Company khác mà plane có thể
    # gọi trong lúc run (không còn dùng để "đoán" project — Task 5 đã xoá
    # fallback `_resolve_workspace_project_id`; project_id giờ luôn đến từ
    # payload/snapshot của chính schedule execution).
    mock_client.get.return_value = {
        "projects": [{"id": "proj_test_1"}],
        "tasks": [],
        "total": 0,
        "items": [],
    }
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
    mock_team_client = AsyncMock()
    mock_team_client.get_run_authority.return_value = ProjectAgentRunAuthority(
        projectId="proj_test_1",
        workspaceId="ws_sched",
        profileKey="operations",
        assignmentVersion=1,
        agentWorkforceMemberId="mem_test_agent",
        spec=SpecRef(
            id=COSA_OPERATIONS_AGENT_SPEC.id,
            version=COSA_OPERATIONS_AGENT_SPEC.version,
            hash=COSA_OPERATIONS_AGENT_SPEC.compute_hash(),
        ),
    )
    plane.project_team_client = mock_team_client

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
            "project_id": "proj_test_1",
        },
    )

    # 2. Poll due tasks
    due = await scheduler.poll_due_tasks(worker_id="test-worker", limit=1)
    assert len(due) == 1
    task_to_run = due[0]

    # 3. Dispatch task via worker loop handler
    await dispatch_one_task(plane, task_to_run)

    # 4. Verify conversation was created
    conversations, total = await conv_repo.list_conversations(
        workspace_id="ws_sched", project_id="proj_test_1"
    )
    assert total == 1
    assert len(conversations) == 1
    sched_conv = conversations[0]
    assert sched_conv.project_id == "proj_test_1"
    assert sched_conv.scope_state == "PROJECT_SCOPED"
    assert sched_conv.active_agent_profile == "operations"
    assert sched_conv.created_by_principal == "service:scheduler"
    assert "Scheduled execution:" in sched_conv.title

    # 5. Verify messages in conversation (user prompt + assistant output)
    messages = await conv_repo.list_messages(sched_conv.conversation_id)
    assert len(messages) == 2
    assert {message.project_id for message in messages} == {"proj_test_1"}
    assert messages[0].role == "user"
    assert messages[0].content == "Run quarterly risk review"
    assert messages[1].role == "assistant"
    assert "Scheduled report analysis complete." in messages[1].content
    assert messages[1].status == "completed"

    # 6. Verify WorkspaceArtifact was created for this scheduled conversation
    artifacts = await art_repo.list_for_conversation(
        workspace_id="ws_sched",
        conversation_id=sched_conv.conversation_id,
    )
    assert len(artifacts) == 1
    assert artifacts[0].artifact_kind == "assistant_output"



@pytest.mark.asyncio
async def test_scheduled_session_fails_closed_when_payload_missing_project_id(worker_setup):
    """Task 5 (spec #1 schedule-project-scope): worker không còn tự "đoán"
    project đầu tiên của workspace (`_resolve_workspace_project_id` đã bị
    xoá) — thiếu project_id phải fail-closed, không được lặng lẽ chạy nhầm
    project.
    """
    plane = worker_setup["plane"]
    conv_repo = worker_setup["conv_repo"]
    stream_mgr = CosaEventStreamManager()

    with pytest.raises(ValueError, match="schedule_project_context_missing"):
        await execute_scheduled_session_task(
            plane,
            stream_mgr,
            {
                "task_type": "scheduled_session",
                "schedule_execution_id": "exec_missing_project",
                "workspace_id": "ws_sched",
                "prompt_template": "Run quarterly risk review",
                "agent_profile": "operations",
                # project_id intentionally omitted.
            },
            run_id="run_missing_project",
        )

    # Fail-closed phải xảy ra TRƯỚC khi tạo conversation — không để lại
    # conversation mồ côi cho 1 run chưa từng có project context hợp lệ.
    _, total = await conv_repo.list_conversations(
        workspace_id="ws_sched", project_id=None
    )
    assert total == 0


@pytest.mark.asyncio
async def test_scheduled_session_fails_closed_when_payload_project_mismatches_snapshot(worker_setup):
    plane = worker_setup["plane"]
    conv_repo = worker_setup["conv_repo"]
    stream_mgr = CosaEventStreamManager()

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: {
        "organizationId": "ws_sched",
        "promptTemplateSnapshot": "Run quarterly risk review",
        "agentProfileSnapshot": "operations",
        "projectIdSnapshot": "proj_snapshot_a",
    }

    mock_post = AsyncMock()

    with (
        patch("apps.cosa.worker.handlers.resolve_platform_control_plane_url", return_value="http://control-plane"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("httpx.AsyncClient.post", new=mock_post),
    ):
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="PROJECT_CONTEXT_MISMATCH"):
            await execute_scheduled_session_task(
                plane,
                stream_mgr,
                {
                    "task_type": "scheduled_session",
                    "schedule_execution_id": "exec_mismatch",
                    "workspace_id": "ws_sched",
                    "prompt_template": "Run quarterly risk review",
                    "agent_profile": "operations",
                    "project_id": "proj_payload_b",
                },
                run_id="run_mismatch",
            )

    _, total = await conv_repo.list_conversations(
        workspace_id="ws_sched", project_id="proj_payload_b"
    )
    assert total == 0



@pytest.mark.asyncio
async def test_fail_closed_reports_execution_failed_to_control_plane(worker_setup):
    """Finding 1 (2026-09-14 whole-branch review): trước đây nhánh fail-closed
    raise `ValueError` ngay mà KHÔNG báo control plane, khiến
    `workspace_schedule_executions.state` kẹt 'queued' vĩnh viễn dù worker
    task-tracking đã coi là failed. Giờ phải POST
    `/cosa/schedules/executions/complete` với `state=failed` TRƯỚC khi raise,
    dùng đúng cơ chế completion-report chung với đường thành công/thất bại
    bình thường."""
    plane = worker_setup["plane"]
    stream_mgr = CosaEventStreamManager()

    mock_post = AsyncMock()
    with (
        patch("httpx.AsyncClient.post", new=mock_post),
        pytest.raises(ValueError, match="schedule_project_context_missing"),
    ):
        await execute_scheduled_session_task(
            plane,
            stream_mgr,
            {
                "task_type": "scheduled_session",
                "schedule_execution_id": "exec_missing_project_report",
                "workspace_id": "ws_sched",
                "prompt_template": "Run quarterly risk review",
                "agent_profile": "operations",
                # project_id intentionally omitted.
            },
            run_id="run_missing_project_report",
        )

    assert mock_post.await_count == 1
    _, kwargs = mock_post.call_args
    sent = kwargs["json"]
    assert sent["executionId"] == "exec_missing_project_report"
    assert sent["state"] == "failed"
    assert "schedule_project_context_missing" in sent["error"]
    # Chưa từng tạo conversation (fail trước bước đó) -> không gửi conversationId.
    assert "conversationId" not in sent


@pytest.mark.asyncio
async def test_success_completion_report_omits_null_error_key(worker_setup):
    """Finding 3.2 (2026-09-14 whole-branch review): 1 trong 4 bug thật phát
    hiện lúc viết E2E Task 8 — completion report cho lần chạy thành công gửi
    `error: null` thay vì bỏ hẳn key `error`. Test này khoá lại hành vi đúng
    bằng cách mock outbound `httpx.AsyncClient.post` và kiểm tra `json=`
    kwarg gửi tới `/cosa/schedules/executions/complete`."""
    plane = worker_setup["plane"]
    stream_mgr = CosaEventStreamManager()

    mock_post = AsyncMock()
    with patch("httpx.AsyncClient.post", new=mock_post):
        await execute_scheduled_session_task(
            plane,
            stream_mgr,
            {
                "task_type": "scheduled_session",
                "schedule_execution_id": "exec_success_report",
                "workspace_id": "ws_sched",
                "prompt_template": "Run quarterly risk review",
                "agent_profile": "operations",
                "project_id": "proj_test_1",
            },
            run_id="run_success_report",
        )

    assert mock_post.await_count == 1
    _, kwargs = mock_post.call_args
    sent = kwargs["json"]
    assert sent["state"] == "succeeded"
    assert "error" not in sent


@pytest.mark.asyncio
async def test_scheduled_session_fails_closed_when_snapshot_lacks_project_id(
    worker_setup, monkeypatch
):
    """Cùng guard fail-closed nhưng qua nhánh fetch snapshot thật từ control
    plane (`GET /cosa/schedules/executions/:id`) — đường đi thật trong
    production, nơi payload dispatch chỉ có `schedule_execution_id` (xem
    `services/cosa/services/workspace-schedule.service.ts`).
    """
    plane = worker_setup["plane"]
    conv_repo = worker_setup["conv_repo"]
    stream_mgr = CosaEventStreamManager()

    class _Resp:
        status_code = 200

        def json(self):
            return {
                "organizationId": "ws_sched",
                "promptTemplateSnapshot": "Run quarterly risk review",
                "agentProfileSnapshot": "operations",
                # projectIdSnapshot intentionally omitted.
            }

    async def _fake_get(self, url, **kwargs):
        return _Resp()

    monkeypatch.setattr("httpx.AsyncClient.get", _fake_get)

    with pytest.raises(ValueError, match="schedule_project_context_missing"):
        await execute_scheduled_session_task(
            plane,
            stream_mgr,
            {"schedule_execution_id": "exec_snapshot_missing_project"},
            run_id="run_snapshot_missing_project",
        )

    _, total = await conv_repo.list_conversations(
        workspace_id="ws_sched", project_id=None
    )
    assert total == 0
