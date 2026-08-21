# backend/app/tests/agents/test_adk_quality_gate_node.py
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from workforce.agents.governance.quality_gate import QualityGateResult, QualityGateVerdict
from workforce.agents.orchestration.adk.nodes.quality_gate_node import (
    build_quality_gate_node,
    quality_gate_fn,
)


@pytest.mark.asyncio
async def test_quality_gate_fn_passes_when_all_gates_pass():
    ctx = SimpleNamespace(
        state={"specialist_reports": {"sales": {"status": "success"}, "finance": {"status": "success"}}},
        route=None,
    )
    with patch(
        "workforce.agents.orchestration.adk.nodes.quality_gate_node.QualityGateEvaluator.evaluate",
        return_value=QualityGateResult(verdict=QualityGateVerdict.PASS, domain="sales"),
    ):
        result = await quality_gate_fn(ctx)

    assert result["any_failed"] is False
    assert ctx.route == "passed"


@pytest.mark.asyncio
async def test_quality_gate_fn_fails_when_any_gate_fails():
    ctx = SimpleNamespace(state={"specialist_reports": {"sales": {"status": "success"}}}, route=None)
    with patch(
        "workforce.agents.orchestration.adk.nodes.quality_gate_node.QualityGateEvaluator.evaluate",
        return_value=QualityGateResult(verdict=QualityGateVerdict.FAIL, domain="sales", issues=["no evidence"]),
    ):
        result = await quality_gate_fn(ctx)

    assert result["any_failed"] is True
    assert ctx.route == "failed"


def test_build_quality_gate_node_shape():
    node = build_quality_gate_node()
    assert node.name == "quality_gate_node"
