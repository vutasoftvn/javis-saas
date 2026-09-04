from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.operations_write import (
    OPERATIONS_TASK_ADVANCE_SPEC,
    create_operations_task_advance_handler,
)


def test_spec_shape():
    assert OPERATIONS_TASK_ADVANCE_SPEC.id == "operations.task.advance"
    props = OPERATIONS_TASK_ADVANCE_SPEC.input_schema["properties"]
    assert set(props["to_status"]["enum"]) == {"in_progress", "done", "blocked"}
    assert set(OPERATIONS_TASK_ADVANCE_SPEC.input_schema["required"]) == {
        "task_id",
        "to_status",
        "run_id",
    }


@pytest.mark.asyncio
async def test_advance_posts_to_company_endpoint():
    client = AsyncMock(spec=CompanyServiceClient)
    client.post.return_value = {"id": "task-1", "status": "done"}
    handler = create_operations_task_advance_handler(client)

    res = await handler(
        {"task_id": "task-1", "to_status": "done", "run_id": "run_abc", "note": "shipped"},
        context={"workspace_id": "ws-9"},
    )
    assert res["task"]["status"] == "done"
    client.post.assert_called_once()
    call = client.post.call_args
    assert call[0][0] == "/operations/tasks/task-1/advance"
    assert call[1]["json"] == {"toStatus": "done", "runId": "run_abc", "note": "shipped"}
    assert call[1]["headers"]["X-Workspace-Id"] == "ws-9"


@pytest.mark.asyncio
async def test_advance_validation_failures():
    client = AsyncMock(spec=CompanyServiceClient)
    handler = create_operations_task_advance_handler(client)

    with pytest.raises(ValueError, match="workspace_id is required"):
        await handler({"task_id": "t", "to_status": "done", "run_id": "r"}, context={})

    with pytest.raises(ValueError, match="task_id is required"):
        await handler(
            {"task_id": "", "to_status": "done", "run_id": "r"},
            context={"workspace_id": "ws-1"},
        )

    with pytest.raises(ValueError, match="to_status must be"):
        await handler(
            {"task_id": "t", "to_status": "cancelled", "run_id": "r"},
            context={"workspace_id": "ws-1"},
        )

    with pytest.raises(ValueError, match="run_id is required"):
        await handler(
            {"task_id": "t", "to_status": "done", "run_id": ""},
            context={"workspace_id": "ws-1"},
        )
    client.post.assert_not_called()
