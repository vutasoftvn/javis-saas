from __future__ import annotations

from agentos.core.approval import Approval, ApprovalService, ApprovalStatus
from agentos.improvement.proposal import ImprovementProposal, ProposalStatus


class ProposalNotApprovedError(Exception):
    def __init__(self, proposal_id: str) -> None:
        super().__init__(f"Improvement proposal {proposal_id} has not been approved")
        self.proposal_id = proposal_id


def request_proposal_approval(
    proposal: ImprovementProposal, approval_service: ApprovalService, *, requester: str
) -> Approval:
    """Human approval stage of the self-improvement loop (blueprint §34)
    routes through the exact same ApprovalService everything else in the
    system uses (Phase 8) — there is no separate approval mechanism
    invented for self-improvement.
    """
    return approval_service.request_approval(
        action="promote_skill_for_capability_gap",
        subject=proposal.gap.capability,
        requester=requester,
    )


def apply_approval_decision(proposal: ImprovementProposal, approval: Approval) -> ImprovementProposal:
    if approval.status == ApprovalStatus.APPROVED:
        proposal.status = ProposalStatus.APPROVED
    elif approval.status == ApprovalStatus.DENIED:
        proposal.status = ProposalStatus.REJECTED
    return proposal


def mark_promoted(proposal: ImprovementProposal) -> ImprovementProposal:
    if proposal.status != ProposalStatus.APPROVED:
        raise ProposalNotApprovedError(proposal.id)
    proposal.status = ProposalStatus.PROMOTED
    return proposal
