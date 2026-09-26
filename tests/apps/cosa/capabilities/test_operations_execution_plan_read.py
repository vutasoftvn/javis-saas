"""WGA G8 — agent chat đọc kế hoạch triển khai + tiến độ task."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from agent.governance.contracts import CapabilityRisk

from apps.cosa.agents.specs import (
    COSA_COFOUNDER_ASSISTANT_AGENT_SPEC,
    COSA_OPERATIONS_AGENT_SPEC,
)
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.operations_read import (
    OPERATIONS_EXECUTION_PLAN_READ_SPEC,
    create_operations_execution_plan_read_handler,
)

_PLAN = {
    "id": "pl1",
    "goalText": "Chốt 3 phỏng vấn",
    "status": "accepted",
    "origin": "chat",
    "items": [
        {
            "title": "Liệt kê task",
            "decisionReason": "rất dài " * 50,
            "evidenceRefs": ["e1"],
            "ownerAgentProfile": "operations",
            "autonomyClass": "AUTO",
            "expectedCapability": "operations.task.list",
            "status": "accepted",
            "taskStatus": "done",
            "priority": "high",
        },
        {
            "title": "Phỏng vấn KH",
            "ownerAgentProfile": None,
            "autonomyClass": "FOUNDER_ONLY",
            "status": "accepted",
            "taskStatus": "todo",
        },
        {"title": "Bỏ", "status": "dropped", "taskStatus": None},
    ],
}


def test_spec_is_read_only_and_requires_project_scope():
    assert OPERATIONS_EXECUTION_PLAN_READ_SPEC.risk == CapabilityRisk.LOW
    schema = OPERATIONS_EXECUTION_PLAN_READ_SPEC.input_schema
    assert schema["required"] == ["project_id"]
    # project_id trong schema -> apply_run_scope tự điền/chặn lệch project.
    assert "project_id" in schema["properties"]


def test_chat_agents_carry_the_capability():
    for spec in (COSA_OPERATIONS_AGENT_SPEC, COSA_COFOUNDER_ASSISTANT_AGENT_SPEC):
        assert "operations.execution_plan.read" in spec.capability_refs


@pytest.mark.asyncio
async def test_handler_summarizes_progress_and_scopes_by_context():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {
        "plans": [_PLAN],
        "latestDecomposition": {"weeklyPlanId": "77", "status": "done", "errorCode": None},
    }
    handler = create_operations_execution_plan_read_handler(client)

    res = await handler({"project_id": "proj1"}, {"workspace_id": "ws1"})

    call = client.get.await_args
    assert call.args[0] == "/operations/execution-plans"
    assert call.kwargs["params"] == {"projectId": "proj1"}
    assert call.kwargs["headers"]["X-Workspace-Id"] == "ws1"
    [plan] = res["plans"]
    assert plan["progress"] == {"total": 2, "by_task_status": {"done": 1, "todo": 1}}
    assert "decisionReason" not in plan["items"][0]
    assert res["latest_decomposition"]["status"] == "done"


@pytest.mark.asyncio
async def test_handler_fails_closed_without_workspace_scope():
    client = AsyncMock(spec=CompanyServiceClient)
    handler = create_operations_execution_plan_read_handler(client)
    with pytest.raises(ValueError, match="workspace_id missing"):
        await handler({"project_id": "proj1"}, {})
    client.get.assert_not_called()
