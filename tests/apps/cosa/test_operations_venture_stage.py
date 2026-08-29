from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from apps.cosa.capabilities.operations_write import (
    OPERATIONS_TASK_CREATE_DRAFT_SPEC,
    create_operations_task_create_draft_handler,
)
from apps.cosa.capabilities.venture_stage import (
    VENTURE_STAGE_ASSESS_SPEC,
    VENTURE_STAGE_TRANSITION_PROPOSE_SPEC,
    create_venture_stage_assess_handler,
    create_venture_stage_transition_propose_handler,
)


@pytest.mark.asyncio
async def test_operations_task_create_draft_handler():
    client = AsyncMock()
    client.post.return_value = {"id": "task_123", "title": "Run 5 customer interviews", "status": "todo"}

    handler = create_operations_task_create_draft_handler(client)

    # Missing decision_reason -> ValueError
    with pytest.raises(ValueError, match="decision_reason is required"):
        await handler(
            {"workspace_id": 1001, "title": "Run 5 customer interviews", "decision_reason": ""},
            context=None,
        )

    res = await handler(
        {
            "workspace_id": 1001,
            "title": "Run 5 customer interviews",
            "decision_reason": "Stage S1 requires qualitative problem validation before building MVP",
            "priority": "high",
        },
        context=None,
    )

    assert res["task"]["id"] == "task_123"
    assert res["advisory"]["layer"] == "CURRENT_LAW"
    assert res["advisory"]["label"] == "proposal"


@pytest.mark.asyncio
async def test_venture_stage_handlers():
    client = AsyncMock()
    client.get.return_value = {"profile": {"ventureStage": "S1_PROBLEM_DISCOVERY"}}

    assess_handler = create_venture_stage_assess_handler(client)
    assess_res = await assess_handler({"workspace_id": 1001}, context=None)

    assert assess_res["assessment"]["current_stage"] == "S1_PROBLEM_DISCOVERY"
    assert assess_res["advisory"]["label"] == "insight"

    transition_handler = create_venture_stage_transition_propose_handler(client)
    trans_res = await transition_handler(
        {
            "workspace_id": 1001,
            "to_stage": "S2_SOLUTION_VALIDATION",
            "reason": "Problem has been validated by 10 independent target customers",
            "evidence_refs": ["ev_101", "ev_102"],
        },
        context=None,
    )

    assert trans_res["proposal"]["toStage"] == "S2_SOLUTION_VALIDATION"
    assert trans_res["advisory"]["label"] == "proposal"
