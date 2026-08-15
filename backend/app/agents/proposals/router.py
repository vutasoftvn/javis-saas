"""REST API Router for Agent Proposals."""

from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.proposals.service import AgentProposalService
from app.core.auth import get_current_workspace_member
from app.db.session import get_db
from app.modules.iam.models import WorkspaceMember

router = APIRouter(prefix="/api/v1/agents/proposals", tags=["agent-proposals"])


class ReviewProposalRequest(BaseModel):
    action: str  # "approve" | "reject"
    reason: Optional[str] = None


def _serialize_proposal(p) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "workspace_id": str(p.workspace_id),
        "company_id": str(p.company_id) if p.company_id else None,
        "run_id": str(p.run_id) if p.run_id else None,
        "proposal_type": p.proposal_type,
        "created_by_agent": p.created_by_agent,
        "title": p.title,
        "description": p.description,
        "payload": p.payload_jsonb,
        "status": p.status,
        "reviewed_by": str(p.reviewed_by) if p.reviewed_by else None,
        "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
        "rejection_reason": p.rejection_reason,
        "applied_resource_id": p.applied_resource_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("")
def list_proposals(
    status: Optional[str] = Query(None, description="Filter by status (pending, approved, rejected, applied)"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """List agent proposals for the authenticated workspace."""
    proposals = AgentProposalService.list_proposals(
        db=db,
        workspace_id=member.workspace_id,
        status_filter=status,
    )
    return [_serialize_proposal(p) for p in proposals]


@router.post("/{proposal_id}/review")
def review_proposal(
    proposal_id: int,
    req: ReviewProposalRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Review (approve or reject) an agent proposal."""
    proposal = AgentProposalService.review_proposal(
        db=db,
        workspace_id=member.workspace_id,
        proposal_id=proposal_id,
        reviewed_by=member.user_id,
        action=req.action,
        rejection_reason=req.reason,
    )
    return _serialize_proposal(proposal)


@router.post("/{proposal_id}/apply")
def apply_proposal(
    proposal_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Apply an approved or pending proposal into real OKR Objective or Task."""
    return AgentProposalService.apply_proposal(
        db=db,
        workspace_id=member.workspace_id,
        proposal_id=proposal_id,
        reviewed_by=member.user_id,
    )
