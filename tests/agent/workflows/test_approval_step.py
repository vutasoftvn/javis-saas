import pytest

from agent.workflows.approval_step import ApprovalGateStep
from agent.workflows.models import StepStatus


class _MockApproval:
    def __init__(self, id: str):
        self.id = id
        self.status = "PENDING"
        self.reason = ""


class _MockApprovalService:
    def __init__(self):
        self._approvals = {}

    def request_approval(self, **kw):
        appr = _MockApproval("appr-1")
        self._approvals["appr-1"] = appr
        return appr

    def get(self, approval_id: str):
        return self._approvals.get(approval_id)

    def decide(self, approval_id: str, reviewer: str, approved: bool, reason: str = ""):
        if approval_id in self._approvals:
            self._approvals[approval_id].status = "APPROVED" if approved else "DENIED"
            self._approvals[approval_id].reason = reason


class _MockPolicyEngine:
    def __init__(self, decision_map=None, default="REQUIRE_APPROVAL"):
        self.decision_map = decision_map or {}
        self.default = default

    def evaluate(self, p):
        return self.decision_map.get(p, self.default)


@pytest.mark.asyncio
async def test_allow_permission_completes_immediately():
    step = ApprovalGateStep(
        "gate",
        policy_engine=_MockPolicyEngine({"SEND_MESSAGE": "ALLOW"}),
        approval_service=_MockApprovalService(),
        permission="SEND_MESSAGE",
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )

    outcome = await step.run({"campaign_id": "camp-1"})
    assert outcome.status == StepStatus.COMPLETED


@pytest.mark.asyncio
async def test_deny_permission_fails_the_step():
    step = ApprovalGateStep(
        "gate",
        policy_engine=_MockPolicyEngine({"ACCESS_SECRET": "DENY"}),
        approval_service=_MockApprovalService(),
        permission="ACCESS_SECRET",
        action="read_secret",
        subject_key="campaign_id",
        requester="sales_agent",
    )

    outcome = await step.run({"campaign_id": "camp-1"})
    assert outcome.status == StepStatus.FAILED


@pytest.mark.asyncio
async def test_require_approval_pauses_and_creates_a_pending_approval():
    approval_service = _MockApprovalService()
    step = ApprovalGateStep(
        "gate",
        policy_engine=_MockPolicyEngine(default="REQUIRE_APPROVAL"),
        approval_service=approval_service,
        permission="SEND_MESSAGE",
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )

    outcome = await step.run({"campaign_id": "camp-1"})
    assert outcome.status == StepStatus.WAITING_APPROVAL
    assert outcome.approval_id is not None
    assert approval_service.get(outcome.approval_id).status == "PENDING"


@pytest.mark.asyncio
async def test_check_pending_reflects_approval_after_it_is_decided():
    approval_service = _MockApprovalService()
    step = ApprovalGateStep(
        "gate",
        policy_engine=_MockPolicyEngine(default="REQUIRE_APPROVAL"),
        approval_service=approval_service,
        permission="SEND_MESSAGE",
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )
    outcome = await step.run({"campaign_id": "camp-1"})
    approval_service.decide(outcome.approval_id, reviewer="founder", approved=True)

    resumed_outcome = step.check_pending(outcome.approval_id)
    assert resumed_outcome.status == StepStatus.COMPLETED


@pytest.mark.asyncio
async def test_check_pending_fails_when_denied():
    approval_service = _MockApprovalService()
    step = ApprovalGateStep(
        "gate",
        policy_engine=_MockPolicyEngine(default="REQUIRE_APPROVAL"),
        approval_service=approval_service,
        permission="SEND_MESSAGE",
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )
    outcome = await step.run({"campaign_id": "camp-1"})
    approval_service.decide(outcome.approval_id, reviewer="founder", approved=False, reason="too risky")

    resumed_outcome = step.check_pending(outcome.approval_id)
    assert resumed_outcome.status == StepStatus.FAILED
    assert "too risky" in resumed_outcome.error
