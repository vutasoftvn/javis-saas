from __future__ import annotations

import pytest
from google.adk.workflow import FunctionNode

from agentos.core.approval import ApprovalService
from agentos.core.context_builder import ContextBuilder
from agentos.core.model_provider import ModelResponse, StubModelProvider
from agentos.core.policy import PermissionLevel, PolicyEngine
from agentos.orchestration.adk.nodes.approval_gate_node import build_approval_gate_node
from agentos.orchestration.adk.nodes.build_company_context_node import build_company_context_node
from agentos.orchestration.adk.nodes.create_mission_node import (
    build_create_mission_node,
    create_mission_fn,
)
from agentos.orchestration.adk.nodes.execution_node import build_execution_node
from agentos.orchestration.adk.nodes.governance_gate_node import build_governance_gate_node
from agentos.orchestration.adk.nodes.planning_node import build_planning_node, planning_fn
from agentos.orchestration.adk.nodes.quality_gate_node import build_quality_gate_node, quality_gate_fn
from agentos.orchestration.adk.nodes.risk_classification_node import (
    build_risk_classification_node,
    risk_classification_fn,
)
from agentos.orchestration.adk.nodes.specialist_delegation_node import (
    build_specialist_delegation_node,
)
from agentos.orchestration.adk.nodes.synthesis_node import build_synthesis_node
from agentos.profiles.registry import AgentProfileRegistry
from agentos.tools.registry import ToolRegistry


class _MockContext:
    def __init__(self, state: dict | None = None) -> None:
        self.state = state or {}
        self.route: str | None = None


@pytest.mark.asyncio
async def test_create_mission_node():
    node = build_create_mission_node()
    assert isinstance(node, FunctionNode)

    ctx = _MockContext({"goal": "Scale enterprise revenue to 10M", "workspace_id": "ws_enterprise"})
    res = await create_mission_fn(ctx)

    assert "mission_id" in res
    assert ctx.state["status"] == "created"
    assert ctx.state["workspace_id"] == "ws_enterprise"
    assert "sales" in ctx.state["active_domains"]


@pytest.mark.asyncio
async def test_planning_node():
    node = build_planning_node()
    assert isinstance(node, FunctionNode)

    ctx = _MockContext({"active_domains": ["sales", "finance"]})
    res = await planning_fn(ctx)

    assert ctx.state["status"] == "planning"
    assert res["active_domains"] == ["sales", "finance"]


@pytest.mark.asyncio
async def test_risk_classification_node():
    node = build_risk_classification_node()
    assert isinstance(node, FunctionNode)

    # Low/medium risk -> auto_start
    ctx_low = _MockContext({"active_domains": ["strategy"]})
    await risk_classification_fn(ctx_low)
    assert ctx_low.route == "auto_start"

    # High risk -> needs_confirmation
    ctx_high = _MockContext({"active_domains": ["production_deploy", "legal"]})
    await risk_classification_fn(ctx_high)
    assert ctx_high.route == "needs_confirmation"


@pytest.mark.asyncio
async def test_build_company_context_node():
    tool_registry = ToolRegistry()
    context_builder = ContextBuilder(tool_registry)
    node = build_company_context_node(context_builder=context_builder)
    assert isinstance(node, FunctionNode)

    ctx = _MockContext({
        "goal": "Prepare quarterly financial analysis",
        "workspace_id": "ws1",
        "agent_key": "chief_of_staff",
    })

    # The internal function is wrapped in the builder
    # We can test the node builder behavior
    builder_fn = node._func if hasattr(node, "_func") else None


@pytest.mark.asyncio
async def test_specialist_delegation_node():
    profile_registry = AgentProfileRegistry()
    node = build_specialist_delegation_node(profile_registry=profile_registry)
    assert isinstance(node, FunctionNode)


@pytest.mark.asyncio
async def test_governance_gate_node():
    policy_engine = PolicyEngine()
    node = build_governance_gate_node(policy_engine=policy_engine)
    assert isinstance(node, FunctionNode)


@pytest.mark.asyncio
async def test_approval_gate_node():
    approval_service = ApprovalService()
    node = build_approval_gate_node(approval_service=approval_service)
    assert isinstance(node, FunctionNode)


@pytest.mark.asyncio
async def test_execution_node():
    node = build_execution_node()
    assert isinstance(node, FunctionNode)


@pytest.mark.asyncio
async def test_quality_gate_node():
    node = build_quality_gate_node()
    assert isinstance(node, FunctionNode)

    # Valid reports -> passed
    ctx_pass = _MockContext({
        "specialist_reports": {
            "sales": {"findings": "Target pipeline is healthy"},
            "finance": {"findings": "Budget approved"},
        }
    })
    await quality_gate_fn(ctx_pass)
    assert ctx_pass.route == "passed"

    # Empty report -> failed
    ctx_fail = _MockContext({
        "specialist_reports": {
            "sales": {"findings": ""},
        }
    })
    await quality_gate_fn(ctx_fail)
    assert ctx_fail.route == "failed"


@pytest.mark.asyncio
async def test_synthesis_node():
    model_provider = StubModelProvider([ModelResponse(text="Executive Strategic Plan: Proceed with expansion.")])
    node = build_synthesis_node(model_provider=model_provider)
    assert isinstance(node, FunctionNode)
