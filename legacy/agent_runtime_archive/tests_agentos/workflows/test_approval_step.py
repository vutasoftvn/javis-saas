import pytest

from agentos.core.approval import ApprovalService
from agentos.core.policy import PermissionClass, PolicyDecision, PolicyEngine
from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.models import StepStatus


@pytest.mark.asyncio
async def test_allow_permission_completes_immediately():
    step = ApprovalGateStep(
        "gate",
        policy_engine=PolicyEngine({PermissionClass.SEND_MESSAGE: PolicyDecision.ALLOW}),
        approval_service=ApprovalService(),
        permission=PermissionClass.SEND_MESSAGE,
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
        policy_engine=PolicyEngine(),
        approval_service=ApprovalService(),
        permission=PermissionClass.ACCESS_SECRET,
        action="read_secret",
        subject_key="campaign_id",
        requester="sales_agent",
    )

    outcome = await step.run({"campaign_id": "camp-1"})

    assert outcome.status == StepStatus.FAILED


@pytest.mark.asyncio
async def test_require_approval_pauses_and_creates_a_pending_approval():
    approval_service = ApprovalService()
    step = ApprovalGateStep(
        "gate",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.SEND_MESSAGE,
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )

    outcome = await step.run({"campaign_id": "camp-1"})

    assert outcome.status == StepStatus.WAITING_APPROVAL
    assert outcome.approval_id is not None
    assert approval_service.get(outcome.approval_id).status.value == "PENDING"


@pytest.mark.asyncio
async def test_check_pending_reflects_approval_after_it_is_decided():
    approval_service = ApprovalService()
    step = ApprovalGateStep(
        "gate",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.SEND_MESSAGE,
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
    approval_service = ApprovalService()
    step = ApprovalGateStep(
        "gate",
        policy_engine=PolicyEngine(),
        approval_service=approval_service,
        permission=PermissionClass.SEND_MESSAGE,
        action="send_email",
        subject_key="campaign_id",
        requester="sales_agent",
    )
    outcome = await step.run({"campaign_id": "camp-1"})
    approval_service.decide(outcome.approval_id, reviewer="founder", approved=False, reason="too risky")

    resumed_outcome = step.check_pending(outcome.approval_id)

    assert resumed_outcome.status == StepStatus.FAILED
    assert "too risky" in resumed_outcome.error
