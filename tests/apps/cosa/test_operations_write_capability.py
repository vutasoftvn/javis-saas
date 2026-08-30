from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.operations_write import (
    OPERATIONS_TASK_CREATE_DRAFT_SPEC,
    create_operations_task_create_draft_handler,
)


@pytest.mark.asyncio
async def test_operations_task_create_draft_requires_project_and_evidence():
    client = AsyncMock(spec=CompanyServiceClient)
    client.post.return_value = {"id": "task-101", "status": "todo"}
    handler = create_operations_task_create_draft_handler(client)

    # 1. Valid request succeeds
    res = await handler(
        {
            "project_id": "proj-1",
            "title": "Setup analytics webhook",
            "priority": "high",
            "decision_reason": "Required for Tranche C PMF monitoring",
            "evidence_refs": ["ev-approved-1"],
        },
        context={"workspace_id": "ws-1"},
    )
    assert res["task"]["id"] == "task-101"
    assert res["advisory"]["label"] == "proposal"
    client.post.assert_called_once()
    assert client.post.call_args[1]["headers"]["X-Workspace-Id"] == "ws-1"

    # 2. Missing project_id fails
    with pytest.raises(ValueError, match="project_id is required"):
        await handler(
            {
                "project_id": "",
                "title": "Task without project",
                "decision_reason": "Some reason",
                "evidence_refs": ["ev-1"],
            },
            context={"workspace_id": "ws-1"},
        )

    # 3. Missing decision_reason fails
    with pytest.raises(ValueError, match="decision_reason is required"):
        await handler(
            {
                "project_id": "proj-1",
                "title": "Task without reason",
                "decision_reason": "",
                "evidence_refs": ["ev-1"],
            },
            context={"workspace_id": "ws-1"},
        )

    # 4. Cross-workspace evidence reference fails
    with pytest.raises(ValueError, match="Cross-workspace evidence reference rejected"):
        await handler(
            {
                "project_id": "proj-1",
                "title": "Task with stolen evidence",
                "decision_reason": "Some reason",
                "evidence_refs": ["artifact://ws-other/ev/1"],
            },
            context={"workspace_id": "ws-1"},
        )

    # 5. Omitted project_id (key entirely absent, not just empty) must fail closed,
    # not silently substitute a fake "proj-default" reference.
    with pytest.raises(ValueError, match="project_id is required"):
        await handler(
            {
                "title": "Task with no project key at all",
                "decision_reason": "Some reason",
                "evidence_refs": ["ev-1"],
            },
            context={"workspace_id": "ws-1"},
        )

    # 6. Omitted evidence_refs (key entirely absent) must fail closed,
    # not silently substitute a fake "ev-default" reference.
    with pytest.raises(ValueError, match="evidence_refs with at least 1 reference is required"):
        await handler(
            {
                "project_id": "proj-1",
                "title": "Task with no evidence_refs key at all",
                "decision_reason": "Some reason",
            },
            context={"workspace_id": "ws-1"},
        )
