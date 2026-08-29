from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from agent.contracts.capability import CapabilitySpec
from agent.contracts.wait import WaitKind
from agent.governance.contracts import (
    ApprovalPolicy,
    CapabilityRisk,
    PolicyDecision,
    PolicyOutcome,
)
from agent.capabilities.gateway import (
    CapabilityGateway,
    GatewayExecutionRequest,
)
from agent.capabilities.registry import CapabilityRegistry
from agent.runs.repository import InMemoryRunRepository
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.engagement_assignment_write import (
    ENGAGEMENT_ASSIGNMENT_WRITE_SPEC,
    create_engagement_assignment_write_handler,
)


@pytest.fixture
def assignment_gateway_setup():
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    mock_client = AsyncMock(spec=CompanyServiceClient)
    handler = create_engagement_assignment_write_handler(mock_client)
    registry.register(ENGAGEMENT_ASSIGNMENT_WRITE_SPEC, handler)

    def policy_evaluator(cap_id, payload, ctx):
        # Mặc định yêu cầu approval, trừ khi op=handoff_human được allow theo rule scope
        if payload.get("op") == "handoff_human":
            return PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("Handoff allow",))
        return PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, reasons=("Route require approval",))

    gateway = CapabilityGateway(
        registry=registry,
        repository=repo,
        policy_evaluator=policy_evaluator,
    )
    return gateway, repo, mock_client


@pytest.mark.asyncio
async def test_engagement_assignment_write_spec_metadata():
    assert ENGAGEMENT_ASSIGNMENT_WRITE_SPEC.id == "engagement.assignment.write"
    assert ENGAGEMENT_ASSIGNMENT_WRITE_SPEC.risk == CapabilityRisk.MEDIUM
    assert ENGAGEMENT_ASSIGNMENT_WRITE_SPEC.approval_policy == ApprovalPolicy.CONDITIONAL


@pytest.mark.asyncio
async def test_engagement_assignment_write_requires_approval_and_executes(assignment_gateway_setup):
    gateway, repo, mock_client = assignment_gateway_setup

    mock_client.post.return_value = {"status": "ok", "assigned": True}

    req = GatewayExecutionRequest(
        run_id="run_assign_1",
        capability_id="engagement.assignment.write",
        input_payload={
            "thread_id": "thread_100",
            "op": "route_team",
            "team_id": "team_tier2",
            "reason": "Escalate to Tier 2 support",
        },
        tool_call_id="call_assign_1",
        checkpoint_ref="ckpt_assign_1",
        workspace_id="ws_assign",
    )

    # 1. First execution requires approval
    res1 = await gateway.execute(req)
    assert res1.status == "waiting_approval"
    assert res1.wait_descriptor.kind == WaitKind.APPROVAL
    mock_client.post.assert_not_called()

    # 2. Approve via repo
    appr_id = res1.wait_descriptor.related_ref
    await repo.decide_approval(appr_id, reviewer="lead_agent", approved=True)

    # 3. Second execution succeeds
    res2 = await gateway.execute(req)
    assert res2.status == "completed"
    assert res2.output_payload["op"] == "route_team"
    assert res2.output_payload["status"] == "success"

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "/commercial/engagement/threads/thread_100/assign" in call_args[0][0]
    assert call_args[1]["json"]["teamId"] == "team_tier2"


@pytest.mark.asyncio
async def test_engagement_assignment_write_handoff_human_allowed_by_rule_scope(assignment_gateway_setup):
    gateway, repo, mock_client = assignment_gateway_setup

    mock_client.post.return_value = {"status": "ok", "mode": "team_queue"}

    req = GatewayExecutionRequest(
        run_id="run_assign_2",
        capability_id="engagement.assignment.write",
        input_payload={
            "thread_id": "thread_200",
            "op": "handoff_human",
            "reason": "Khách hàng yêu cầu hỗ trợ phức tạp ngoài FAQ",
        },
        tool_call_id="call_assign_2",
        checkpoint_ref="ckpt_assign_2",
        workspace_id="ws_assign",
    )

    res = await gateway.execute(req)
    assert res.status == "completed"
    assert res.output_payload["op"] == "handoff_human"
    assert res.output_payload["status"] == "success"

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "/commercial/engagement/threads/thread_200/assign" in call_args[0][0]
    assert call_args[1]["json"]["activeMode"] == "team_queue"
