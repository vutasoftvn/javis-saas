"""Test Company→Agent Project Activity event projection.

Verifies that signed Company business events carrying projectId are projected
into the durable Agent Activity Feed with idempotency (same event_id returns
same record without incrementing sequence) and project isolation (foreign
Project data remains isolated).
"""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from agent.project_activity.models import ProjectActivityEventRecord
from agent.project_activity.repository import InMemoryProjectActivityRepository


@pytest.fixture
def project_activity_repo():
    """In-memory repository fixture for Company event projection tests."""
    return InMemoryProjectActivityRepository()


@pytest.mark.asyncio
async def test_company_event_projector_accepts_project_scoped_task_event(
    project_activity_repo,
):
    """Verify a signed Company task event projects correctly into Activity Feed."""
    # Company would send this via /agent/internal/events with HMAC signature
    company_event_id = "evt_001"

    event = ProjectActivityEventRecord(
        event_id=company_event_id,
        workspace_id="ws_a",
        project_id="proj_a",
        idempotency_key=f"company:task_a:task.completed:1",
        kind="task.completed",
        phase="execution",
        status="completed",
        actor_kind="user",
        actor_id="human_a",
        correlation_id="corr_a",
        source_type="task",
        source_id="task_a",
        source_version="1",
        classification="internal",
        summary={"task_id": "task_a", "title": "Complete work"},
        payload_hash="abc123",
        occurred_at=datetime.now(UTC),
    )

    recorded = await project_activity_repo.append_if_absent(event)

    assert recorded.event_id == company_event_id
    assert recorded.workspace_id == "ws_a"
    assert recorded.project_id == "proj_a"
    assert recorded.project_sequence == 1
    assert recorded.kind == "task.completed"


@pytest.mark.asyncio
async def test_company_event_projector_idempotent_delivery(project_activity_repo):
    """Verify duplicate event delivery returns original row without new sequence."""
    company_event_id = "evt_002"

    first_event = ProjectActivityEventRecord(
        event_id=company_event_id,
        workspace_id="ws_a",
        project_id="proj_a",
        idempotency_key=f"company:task_a:task.completed:1",
        kind="task.completed",
        phase="execution",
        status="completed",
        actor_kind="user",
        actor_id="human_a",
        correlation_id="corr_a",
        source_type="task",
        source_id="task_a",
        source_version="1",
        classification="internal",
        summary={"task_id": "task_a"},
    )

    recorded_first = await project_activity_repo.append_if_absent(first_event)
    recorded_dup = await project_activity_repo.append_if_absent(first_event)

    assert recorded_first.project_sequence == recorded_dup.project_sequence == 1
    assert recorded_dup.event_id == company_event_id


@pytest.mark.asyncio
async def test_company_event_projector_isolates_projects(project_activity_repo):
    """Verify Project A events cannot appear in Project B feed."""
    # Event for Project A
    event_proj_a = ProjectActivityEventRecord(
        event_id="evt_a",
        workspace_id="ws_a",
        project_id="proj_a",
        idempotency_key="company:task_a:task.created:1",
        kind="task.created",
        source_type="task",
        source_id="task_a",
        source_version="1",
        summary={"task_id": "task_a"},
    )

    # Event for Project B
    event_proj_b = ProjectActivityEventRecord(
        event_id="evt_b",
        workspace_id="ws_a",
        project_id="proj_b",
        idempotency_key="company:task_b:task.created:1",
        kind="task.created",
        source_type="task",
        source_id="task_b",
        source_version="1",
        summary={"task_id": "task_b"},
    )

    await project_activity_repo.append_if_absent(event_proj_a)
    await project_activity_repo.append_if_absent(event_proj_b)

    # Query Project A feed — should not see Project B events
    proj_a_events = await project_activity_repo.list_since(
        workspace_id="ws_a", project_id="proj_a"
    )

    assert len(proj_a_events) == 1
    assert proj_a_events[0].project_id == "proj_a"
    assert proj_a_events[0].event_id == "evt_a"

    # Query Project B feed
    proj_b_events = await project_activity_repo.list_since(
        workspace_id="ws_a", project_id="proj_b"
    )

    assert len(proj_b_events) == 1
    assert proj_b_events[0].project_id == "proj_b"
    assert proj_b_events[0].event_id == "evt_b"
