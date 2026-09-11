"""Test Project Activity Feed routes: list, detail, and SSE stream (Task 5).

Dùng verify_project_context trước mọi route; isolation theo workspace+project;
redaction ở detail; reconnect với Last-Event-ID (list_since là source of truth).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import httpx
import pytest
from agent.conversations.repository import InMemoryConversationRepository
from agent.coordination.scheduler import RunScheduler
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.project_activity.models import ProjectActivityEventRecord
from agent.project_activity.repository import InMemoryProjectActivityRepository
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.leases import RunLeaseManager
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel

from apps.cosa.api.app import create_cosa_app
from apps.cosa.api.project_context import (
    PROJECT_CONTEXT_REQUIRED,
    PROJECT_NOT_FOUND_OR_FORBIDDEN,
)
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.agent_plane import build_cosa_agent_plane
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity
from tests.apps.cosa.locale_test_helpers import FakeProfileLocaleClient
from tests.apps.cosa.policy_test_helpers import (
    configure_mock_client_allows_data_use,
    configure_mock_client_project_access,
    fake_active_tenant_policy_client,
)

WORKSPACE_A = "ws_a"
PROJECT_A = "proj_a"
PROJECT_B = "proj_b"


@pytest.fixture
def test_app():
    mock_client = AsyncMock(spec=CompanyServiceClient)
    configure_mock_client_allows_data_use(mock_client)
    configure_mock_client_project_access(mock_client, workspace_id=WORKSPACE_A)

    repo = InMemoryProjectActivityRepository()

    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(workspace_id=WORKSPACE_A),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        project_activity_repository=repo,
        model=FakeSDKModel(),
        profile_locale_client=FakeProfileLocaleClient(),
    )
    app = create_cosa_app(plane=plane)
    override_authenticated_identity(app, workspace_id=WORKSPACE_A)
    return app, plane, mock_client, repo


@pytest.mark.asyncio
async def test_list_activity_requires_project_context(test_app):
    """Yêu cầu project_id bắt buộc; không có project_id trong path -> 404/422."""
    app, _, _, _ = test_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/agent/projects//activity")
        assert response.status_code in (404, 422)


@pytest.mark.asyncio
async def test_list_activity_project_a_filters_project_b(test_app):
    """Project A có 2 event, Project B có 1. List proj_a trả chỉ proj_a events."""
    app, plane, mock_client, repo = test_app

    # Tạo events cho Project A
    event_a1 = ProjectActivityEventRecord(
        event_id="ev_a1",
        workspace_id=WORKSPACE_A,
        project_id=PROJECT_A,
        project_sequence=1,
        idempotency_key="run:run_1:run.queued:1",
        kind="run.queued",
        phase="runtime",
        status="accepted",
        actor_kind="human",
        actor_id="human_a",
        correlation_id="corr_1",
        source_type="run",
        source_id="run_1",
        source_version="1",
        summary={"status": "queued"},
        classification="internal",
        payload_hash="hash1",
        occurred_at=datetime.now(UTC),
        recorded_at=datetime.now(UTC),
    )

    event_a2 = ProjectActivityEventRecord(
        event_id="ev_a2",
        workspace_id=WORKSPACE_A,
        project_id=PROJECT_A,
        project_sequence=2,
        idempotency_key="run:run_2:run.completed:1",
        kind="run.completed",
        phase="runtime",
        status="accepted",
        actor_kind="human",
        actor_id="human_a",
        correlation_id="corr_2",
        source_type="run",
        source_id="run_2",
        source_version="1",
        summary={"status": "completed"},
        classification="internal",
        payload_hash="hash2",
        occurred_at=datetime.now(UTC),
        recorded_at=datetime.now(UTC),
    )

    # Tạo event cho Project B
    event_b1 = ProjectActivityEventRecord(
        event_id="ev_b1",
        workspace_id=WORKSPACE_A,
        project_id=PROJECT_B,
        project_sequence=1,
        idempotency_key="run:run_3:run.queued:1",
        kind="run.queued",
        phase="runtime",
        status="accepted",
        actor_kind="human",
        actor_id="human_a",
        correlation_id="corr_3",
        source_type="run",
        source_id="run_3",
        source_version="1",
        summary={"status": "queued"},
        classification="internal",
        payload_hash="hash3",
        occurred_at=datetime.now(UTC),
        recorded_at=datetime.now(UTC),
    )

    await repo.append_if_absent(event_a1)
    await repo.append_if_absent(event_a2)
    await repo.append_if_absent(event_b1)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/agent/projects/{PROJECT_A}/activity")

        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 2
        assert all(item["project_id"] == PROJECT_A for item in body["items"])
        assert [item["project_sequence"] for item in body["items"]] == [1, 2]


@pytest.mark.asyncio
async def test_list_activity_after_sequence_pagination(test_app):
    """after_project_sequence filter: tính từ sequence N+1 trở đi."""
    app, plane, mock_client, repo = test_app

    event1 = ProjectActivityEventRecord(
        event_id="ev1",
        workspace_id=WORKSPACE_A,
        project_id=PROJECT_A,
        project_sequence=1,
        idempotency_key="a",
        kind="run.queued",
        phase="runtime",
        status="accepted",
        actor_kind="human",
        actor_id="h1",
        correlation_id="c1",
        source_type="run",
        source_id="r1",
        source_version="1",
        summary={},
        classification="internal",
        payload_hash="h1",
        occurred_at=datetime.now(UTC),
        recorded_at=datetime.now(UTC),
    )

    event2 = ProjectActivityEventRecord(
        event_id="ev2",
        workspace_id=WORKSPACE_A,
        project_id=PROJECT_A,
        project_sequence=2,
        idempotency_key="b",
        kind="run.started",
        phase="runtime",
        status="accepted",
        actor_kind="human",
        actor_id="h1",
        correlation_id="c1",
        source_type="run",
        source_id="r1",
        source_version="1",
        summary={},
        classification="internal",
        payload_hash="h2",
        occurred_at=datetime.now(UTC),
        recorded_at=datetime.now(UTC),
    )

    await repo.append_if_absent(event1)
    await repo.append_if_absent(event2)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/agent/projects/{PROJECT_A}/activity?after_project_sequence=1"
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["project_sequence"] == 2


@pytest.mark.asyncio
async def test_detail_returns_404_when_project_not_found(test_app):
    """Detail endpoint trả 404 PROJECT_NOT_FOUND_OR_FORBIDDEN khi Project không xác nhận."""
    from apps.cosa.capabilities.client import CompanyServiceError
    app, plane, mock_client, repo = test_app

    event = ProjectActivityEventRecord(
        event_id="ev1",
        workspace_id=WORKSPACE_A,
        project_id=PROJECT_A,
        project_sequence=1,
        idempotency_key="a",
        kind="run.queued",
        phase="runtime",
        status="accepted",
        actor_kind="human",
        actor_id="h1",
        correlation_id="c1",
        source_type="run",
        source_id="r1",
        source_version="1",
        summary={},
        classification="internal",
        payload_hash="h1",
        occurred_at=datetime.now(UTC),
        recorded_at=datetime.now(UTC),
    )

    await repo.append_if_absent(event)

    # Mock company client reject access
    mock_client.get.side_effect = CompanyServiceError("Not found or not authorized")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/agent/projects/{PROJECT_A}/activity/ev1",
        )

        assert response.status_code == 404
        body = response.json()
        assert body["detail"]["code"] == PROJECT_NOT_FOUND_OR_FORBIDDEN


@pytest.mark.asyncio
async def test_stream_rejects_invalid_last_event_id(test_app):
    """Last-Event-ID phải là positive integer; reject non-numeric."""
    app, plane, mock_client, repo = test_app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/agent/projects/{PROJECT_A}/activity/stream",
            headers={"Last-Event-ID": "not_a_number"},
        )

        # Expects error response
        assert response.status_code in (400, 422)
