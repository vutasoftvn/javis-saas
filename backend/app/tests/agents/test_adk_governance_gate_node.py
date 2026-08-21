# backend/app/tests/agents/test_adk_governance_gate_node.py
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.workforce.agents.governance.budget import BudgetCheckResult, MissionBudget
from app.workforce.agents.governance.stuck_detector import StuckAnalysisResult
from app.workforce.agents.orchestration.adk.nodes.governance_gate_node import (
    build_governance_gate_node,
    governance_gate_fn,
)


@pytest.mark.asyncio
async def test_governance_gate_fn_continues_when_within_budget():
    ctx = SimpleNamespace(
        state={"db": MagicMock(), "mission_run": MagicMock(id=1), "mission_budget": MissionBudget(), "current_step": 2},
        route=None,
    )
    with patch(
        "app.workforce.agents.orchestration.adk.nodes.governance_gate_node.BudgetTracker.check",
        return_value=BudgetCheckResult(is_exceeded=False),
    ), patch(
        "app.workforce.agents.orchestration.adk.nodes.governance_gate_node.StuckDetector.analyze_run",
        return_value=StuckAnalysisResult(is_stuck=False),
    ):
        result = await governance_gate_fn(ctx)

    assert result == {"blocked": False}
    assert ctx.route == "continue"
    assert "governance_block_reason" not in ctx.state


@pytest.mark.asyncio
async def test_governance_gate_fn_blocks_when_budget_exceeded():
    ctx = SimpleNamespace(
        state={"db": MagicMock(), "mission_run": MagicMock(id=1), "mission_budget": MissionBudget(), "current_step": 20},
        route=None,
    )
    with patch(
        "app.workforce.agents.orchestration.adk.nodes.governance_gate_node.BudgetTracker.check",
        return_value=BudgetCheckResult(is_exceeded=True, reason_code="STEP_LIMIT_EXCEEDED", message="quá số bước cho phép"),
    ):
        result = await governance_gate_fn(ctx)

    assert result == {"blocked": True, "reason_code": "STEP_LIMIT_EXCEEDED"}
    assert ctx.route == "blocked"
    assert ctx.state["governance_block_reason"] == "quá số bước cho phép"


def test_build_governance_gate_node_shape():
    node = build_governance_gate_node(name="governance_gate_pre_synthesis")
    assert node.name == "governance_gate_pre_synthesis"
