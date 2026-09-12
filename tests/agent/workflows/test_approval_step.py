from __future__ import annotations

import pytest
from agent.capabilities.approval_service import DurableApprovalService
from agent.runs.repository import InMemoryRunRepository
from agent.workflows.approval_step import ApprovalGateStep
from agent.workflows.models import StepStatus


class _MockPolicyEngine:
    def __init__(self, decision_map=None, default="REQUIRE_APPROVAL"):
        self.decision_map = decision_map or {}
        self.default = default

    def evaluate(self, p):
        return self.decision_map.get(p, self.default)


@pytest.mark.asyncio
async def test_allow_permission_completes_immediately():
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repo)
    step = ApprovalGateStep(
        "gate",
        policy_engine=_MockPolicyEngine({"SEND_MESSAGE": "ALLOW"}),
        approval_service=service,
        permission="SEND_MESSAGE",
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )

    outcome = await step.run({"campaign_id": "camp-1", "workspace_id": "ws-1"})
    assert outcome.status == StepStatus.COMPLETED


@pytest.mark.asyncio
async def test_deny_permission_fails_the_step():
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repo)
    step = ApprovalGateStep(
        "gate",
        policy_engine=_MockPolicyEngine({"ACCESS_SECRET": "DENY"}),
        approval_service=service,
        permission="ACCESS_SECRET",
        action="read_secret",
        subject_key="campaign_id",
        requester="sales_agent",
    )

    outcome = await step.run({"campaign_id": "camp-1", "workspace_id": "ws-1"})
    assert outcome.status == StepStatus.FAILED


@pytest.mark.asyncio
async def test_require_approval_pauses_and_creates_a_pending_approval():
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repo)
    step = ApprovalGateStep(
        "gate",
        policy_engine=_MockPolicyEngine(default="REQUIRE_APPROVAL"),
        approval_service=service,
        permission="SEND_MESSAGE",
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )

    outcome = await step.run({"campaign_id": "camp-1", "workspace_id": "ws-1"})
    assert outcome.status == StepStatus.WAITING_APPROVAL
    assert outcome.approval_id is not None
    record = await service.get_approval(outcome.approval_id)
    assert record is not None
    assert record.status == "pending"


@pytest.mark.asyncio
async def test_check_pending_reflects_approval_after_it_is_decided():
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repo)
    step = ApprovalGateStep(
        "gate",
        policy_engine=_MockPolicyEngine(default="REQUIRE_APPROVAL"),
        approval_service=service,
        permission="SEND_MESSAGE",
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )
    outcome = await step.run({"campaign_id": "camp-1", "workspace_id": "ws-1"})
    await service.submit_decision(approval_id=outcome.approval_id, reviewer="founder", approved=True)

    resumed_outcome = await step.check_pending(outcome.approval_id)
    assert resumed_outcome.status == StepStatus.COMPLETED


@pytest.mark.asyncio
async def test_check_pending_fails_when_denied():
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repo)
    step = ApprovalGateStep(
        "gate",
        policy_engine=_MockPolicyEngine(default="REQUIRE_APPROVAL"),
        approval_service=service,
        permission="SEND_MESSAGE",
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )
    outcome = await step.run({"campaign_id": "camp-1", "workspace_id": "ws-1"})
    await service.submit_decision(approval_id=outcome.approval_id, reviewer="founder", approved=False, reason="too risky")

    resumed_outcome = await step.check_pending(outcome.approval_id)
    assert resumed_outcome.status == StepStatus.FAILED
    assert "too risky" in resumed_outcome.error


@pytest.mark.asyncio
async def test_approval_gate_creates_durable_change_request() -> None:
    repo = InMemoryRunRepository()
    service = DurableApprovalService(repo)
    outcome = await ApprovalGateStep(
        name="publish",
        approval_service=service,
        action="publish_report",
        subject_key="report_ref",
        subject_hash_key="report_hash",
    ).run({"workspace_id": "ws-a", "report_ref": "report-7", "report_hash": "sha256:r7"})
    assert outcome.status is StepStatus.WAITING_APPROVAL
    assert outcome.approval_id is not None
