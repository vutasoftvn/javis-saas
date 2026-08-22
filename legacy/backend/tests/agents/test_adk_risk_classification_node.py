# backend/app/tests/agents/test_adk_risk_classification_node.py
from types import SimpleNamespace

import pytest

from workforce.agents.orchestration.adk.nodes.risk_classification_node import (
    build_risk_classification_node,
    risk_classification_fn,
)


@pytest.mark.asyncio
async def test_risk_classification_fn_auto_start_for_r0_r1():
    ctx = SimpleNamespace(state={"active_domains": ["sales", "finance"]}, route=None)
    result = await risk_classification_fn(ctx)
    assert result == {"risk_level": "R0"}
    assert ctx.state["risk_level"] == "R0"
    assert ctx.route == "auto_start"


@pytest.mark.asyncio
async def test_risk_classification_fn_needs_confirmation_above_r1(monkeypatch):
    import workforce.agents.orchestration.specialist_registry as registry

    risky_spec = registry.SpecialistSpec(
        domain="finance", agent_key="finance_specialist", task="t",
        tool_flat_name="finance_get_financial_summary",
        fetch_snapshot=registry.SPECIALIST_REGISTRY["finance"].fetch_snapshot,
        risk_level="R2",
    )
    monkeypatch.setitem(registry.SPECIALIST_REGISTRY, "finance", risky_spec)

    ctx = SimpleNamespace(state={"active_domains": ["finance"]}, route=None)
    result = await risk_classification_fn(ctx)
    assert result == {"risk_level": "R2"}
    assert ctx.route == "needs_confirmation"


def test_build_risk_classification_node_shape():
    node = build_risk_classification_node()
    assert node.name == "risk_classification_node"
