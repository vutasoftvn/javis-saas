"""Project Activity projection — Task 3 fix (review Finding 1).

Proves the durable Project Activity projection is actually reachable through
the REAL production call sites, not just through CosaEventStreamManager
directly:
- apps/cosa/worker/handlers.py::execute_run_task (run.started, run.completed,
  run.failed, approval.requested, run.waiting_approval)
- apps/cosa/api/workforce_routes.py::decide_approval (approval.resolved)

Every scenario asserts against the InMemoryProjectActivityRepository the
plane was built with — the durable source of truth, not the SSE queue.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from agent.contracts.run import RunResult, RunStatus
from agent.contracts.wait import WaitDescriptor, WaitKind
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.project_activity.repository import InMemoryProjectActivityRepository
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.models import RunRecord
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.api.app import create_cosa_app
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from apps.cosa.worker.handlers import execute_run_task
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    configure_mock_client_project_access,
    fake_active_tenant_policy_client,
)

WORKSPACE_ID = "ws_1"
PROJECT_ID = "proj_1"


def _worker_plane(activity_repo: InMemoryProjectActivityRepository):
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    return build_cosa_agent_plane(
        company_client=mock_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
        project_activity_repository=activity_repo,
    )


def _payload(**overrides) -> dict:
    base = {
        "run_id": "run_wiring_test_1",
        "conversation_id": "conv_1",
        "user_prompt": "hello",
        "agent_profile": "operations",
        "principal": "user_1",
        "workspace_id": WORKSPACE_ID,
        "project_id": PROJECT_ID,
        "delegation_token": "fake-token",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_execute_run_task_records_run_started_and_run_completed():
    activity_repo = InMemoryProjectActivityRepository()
    plane = _worker_plane(activity_repo)
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(plane, stream_mgr, _payload())

    events = await activity_repo.list_since(workspace_id=WORKSPACE_ID, project_id=PROJECT_ID)
    kinds = [e.kind for e in events]
    assert "run.started" in kinds
    assert "run.completed" in kinds
    # sanity: durable projection is sequenced (not just non-empty)
    assert events == sorted(events, key=lambda e: e.project_sequence)


@pytest.mark.asyncio
async def test_execute_run_task_records_run_failed_when_registry_not_seeded():
    """Registry NOT seeded -> spec resolution fails -> run.failed emitted by
    the real worker code path (no mocking of the projection itself)."""
    activity_repo = InMemoryProjectActivityRepository()
    plane = _worker_plane(activity_repo)
    stream_mgr = CosaEventStreamManager()

    await execute_run_task(plane, stream_mgr, _payload(run_id="run_wiring_test_fail"))

    events = await activity_repo.list_since(workspace_id=WORKSPACE_ID, project_id=PROJECT_ID)
    assert "run.failed" in [e.kind for e in events]


@pytest.mark.asyncio
async def test_execute_run_task_records_approval_requested_and_run_waiting_approval():
    """Forces the kernel to return WAITING_APPROVAL (mirrors how
    _execute_run_task_inner's WAITING_APPROVAL branch is exercised elsewhere
    in this suite) to prove BOTH new activity kinds this fix wires directly
    (approval.requested via the approval.required stream event, and
    run.waiting_approval via a direct ProjectActivityService call) actually
    reach the projection when the worker runs them."""
    activity_repo = InMemoryProjectActivityRepository()
    plane = _worker_plane(activity_repo)
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    stream_mgr = CosaEventStreamManager()

    fake_wait = WaitDescriptor(
        kind=WaitKind.APPROVAL,
        reason="high risk action needs approval",
        checkpoint_ref="ckpt_wiring_1",
        related_ref="appr_wiring_1",
    )
    fake_result = RunResult(
        run_id="run_wiring_test_wait",
        status=RunStatus.WAITING_APPROVAL,
        interruptions_waits=[fake_wait],
    )

    with patch(
        "apps.cosa.worker.handlers.run_kernel",
        AsyncMock(return_value=(fake_result, 0.01)),
    ):
        await execute_run_task(plane, stream_mgr, _payload(run_id="run_wiring_test_wait"))

    events = await activity_repo.list_since(workspace_id=WORKSPACE_ID, project_id=PROJECT_ID)
    kinds = [e.kind for e in events]
    assert "approval.requested" in kinds
    assert "run.waiting_approval" in kinds

    waiting_event = next(e for e in events if e.kind == "run.waiting_approval")
    # allowlisted summary keys only — no raw payload.
    assert waiting_event.summary.get("checkpoint_ref") == "ckpt_wiring_1"
    assert waiting_event.summary.get("approval_id") == "appr_wiring_1"


@pytest.fixture
def approval_test_app():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_project_access(mock_client)
    activity_repo = InMemoryProjectActivityRepository()
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
        model=FakeSDKModel(),
        project_activity_repository=activity_repo,
    )
    app = create_cosa_app(plane=plane)
    return app, activity_repo


@pytest.mark.asyncio
async def test_decide_approval_records_approval_resolved(approval_test_app):
    """apps/cosa/api/workforce_routes.py::decide_approval — the real HTTP
    endpoint founders hit to approve/reject — must also record the durable
    Project Activity row (this is the site Finding 1 named explicitly)."""
    app, activity_repo = approval_test_app
    override_authenticated_identity(app, workspace_id=WORKSPACE_ID)
    plane = app.state.plane

    run = RunRecord(
        workspace_id=WORKSPACE_ID,
        project_id=PROJECT_ID,
        principal="user:test_user",
        root_executable_id="test-spec",
    )
    await plane.repository.create_run(run)

    approval, _wait_desc = await plane.approval_service.create_approval_request(
        run_id=run.run_id,
        tool_call_id="tc_wiring_1",
        checkpoint_ref="ckpt_wiring_approval_1",
        requirement={"risk_level": "high"},
        requester="user:test_user",
        action="finance.payout.execute",
        subject="Acme Corp",
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post(
            f"/agent/workforce/approvals/{approval.approval_id}/decision",
            json={"approved": True},
        )
        assert res.status_code == 200

    events = await activity_repo.list_since(workspace_id=WORKSPACE_ID, project_id=PROJECT_ID)
    assert "approval.resolved" in [e.kind for e in events]
