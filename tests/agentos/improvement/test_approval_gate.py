import pytest

from agentos.core.approval import ApprovalService
from agentos.improvement.approval_gate import (
    ProposalNotApprovedError,
    apply_approval_decision,
    mark_promoted,
    request_proposal_approval,
)
from agentos.improvement.gap_detection import CapabilityGap, CapabilityGapEvidence
from agentos.improvement.proposal import ImprovementProposal, ProposalStatus


def _make_proposal() -> ImprovementProposal:
    gap = CapabilityGap(
        capability="marketing.keyword-clustering",
        evidence=CapabilityGapEvidence(failed_tasks=8, average_eval=0.54),
    )
    return ImprovementProposal(
        gap=gap, candidate_skill_ids=["marketing.keyword-clustering"], expected_gain=0.8, risk="low"
    )


def test_request_proposal_approval_creates_pending_approval():
    service = ApprovalService()
    proposal = _make_proposal()

    approval = request_proposal_approval(proposal, service, requester="improvement_agent")

    assert approval.subject == "marketing.keyword-clustering"
    assert approval.action == "promote_skill_for_capability_gap"


def test_apply_approval_decision_marks_proposal_approved():
    service = ApprovalService()
    proposal = _make_proposal()
    approval = request_proposal_approval(proposal, service, requester="improvement_agent")
    service.decide(approval.id, reviewer="founder", approved=True)

    updated = apply_approval_decision(proposal, service.get(approval.id))

    assert updated.status == ProposalStatus.APPROVED


def test_apply_approval_decision_marks_proposal_rejected():
    service = ApprovalService()
    proposal = _make_proposal()
    approval = request_proposal_approval(proposal, service, requester="improvement_agent")
    service.decide(approval.id, reviewer="founder", approved=False, reason="too risky")

    updated = apply_approval_decision(proposal, service.get(approval.id))

    assert updated.status == ProposalStatus.REJECTED


def test_mark_promoted_requires_approved_status():
    proposal = _make_proposal()
    with pytest.raises(ProposalNotApprovedError):
        mark_promoted(proposal)


def test_mark_promoted_succeeds_after_approval():
    proposal = _make_proposal()
    proposal.status = ProposalStatus.APPROVED

    updated = mark_promoted(proposal)

    assert updated.status == ProposalStatus.PROMOTED
