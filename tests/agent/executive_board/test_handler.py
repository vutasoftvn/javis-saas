import pytest
from unittest.mock import AsyncMock, MagicMock

from agent.executive_board.models import ExecutiveAnalysisOutcome
from apps.cosa.worker.executive_board_handler import (
    execute_executive_deliberation_framed_task,
)


@pytest.mark.asyncio
async def test_executive_board_handler_success():
    mock_client = MagicMock()
    mock_client.submit_analysis_callback = AsyncMock(return_value={"success": True})

    mock_runner = MagicMock()
    mock_runner.run = AsyncMock(
        return_value=ExecutiveAnalysisOutcome(
            kind="executive.analysis.completed.v1",
            deliberation_id="delib-1",
            frame_version=1,
            role_key="cfo",
            descriptor={
                "conclusion": "Financial viability is sound.",
                "confidence": "HIGH",
                "evidence_claims": [],
            },
        )
    )

    plane = MagicMock()
    plane.executive_board_client = mock_client
    plane.executive_board_runner = mock_runner

    payload = {
        "workspace_id": "ws-1",
        "project_id": "proj-1",
        "deliberation_id": "delib-1",
        "frame_version": 1,
        "title": "Evaluate Pricing Strategy",
        "problem_statement": "Should we increase subscription pricing?",
        "role_pins": [
            {
                "role_key": "cfo",
                "assignment_id": "assign-cfo",
                "spec_id": "cosa.agents.executive.cfo",
                "spec_version": "1.0.0",
                "spec_hash": "hash-cfo",
                "skill_pins": ["board-protocol", "cfo-advisor"],
            }
        ],
        "evidence_refs": [],
    }

    res = await execute_executive_deliberation_framed_task(plane, None, payload)
    assert res["status"] == "completed"
    assert len(res["results"]) == 1
    assert res["results"][0]["role_key"] == "cfo"
    assert res["results"][0]["outcome"] == "executive.analysis.completed.v1"

    mock_runner.run.assert_awaited_once()
    mock_client.submit_analysis_callback.assert_awaited_once()
    call_kwargs = mock_client.submit_analysis_callback.call_args.kwargs
    assert call_kwargs["workspace_id"] == "ws-1"
    assert call_kwargs["project_id"] == "proj-1"
    assert call_kwargs["deliberation_id"] == "delib-1"
    assert call_kwargs["payload"]["kind"] == "executive.analysis.completed.v1"
