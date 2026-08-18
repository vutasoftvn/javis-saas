"""Unit tests for AI Program Service and Fallback Runtimes."""

import pytest
import os
from app.workforce.ai.programs.schemas import AIProgramRequest
from app.workforce.ai.programs.runtime import (
    DSPyProgramRuntime,
    LegacyPromptProgramRuntime,
    MockProgramRuntime,
)
from app.workforce.ai.service import AIProgramService


@pytest.mark.asyncio
async def test_legacy_fallback_runtime():
    """Verify legacy prompt runtime returns structured fallback output."""
    runtime = LegacyPromptProgramRuntime()
    req = AIProgramRequest(
        workspace_id="test_ws",
        program_key="ceo.brief",
        input={"pending_approvals": [{"id": 1}]},
    )
    res = await runtime.run(req)
    assert res.status == "completed"
    assert res.engine == "legacy"
    assert "headline" in res.output
    assert "today_top_3" in res.output


@pytest.mark.asyncio
async def test_mock_program_runtime():
    """Verify mock runtime returns expected response."""
    runtime = MockProgramRuntime(mock_output={"custom_field": 123})
    req = AIProgramRequest(
        workspace_id="test_ws",
        program_key="sales.lead_qualification",
        input={},
    )
    res = await runtime.run(req)
    assert res.status == "completed"
    assert res.output["custom_field"] == 123
    assert res.engine == "mock"


@pytest.mark.asyncio
async def test_service_routes_to_legacy_when_dspy_disabled(monkeypatch):
    """Verify AIProgramService falls back when DSPy is disabled via flag."""
    monkeypatch.setenv("COSA_DSPY_ENABLED", "false")
    service = AIProgramService()
    
    req = AIProgramRequest(
        workspace_id="test_ws",
        program_key="ceo.brief",
        input={},
    )
    res = await service.run_program(req)
    assert res.status == "completed"
    assert res.engine == "legacy"
