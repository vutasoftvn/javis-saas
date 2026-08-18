"""FastAPI Router for Shared Work Orchestrator."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.workforce.agents.orchestrator.command import OrchestratorRequest, OrchestratorResponse
from app.workforce.agents.orchestrator.service import WorkOrchestratorService
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/orchestrator", tags=["orchestrator"])


@router.post("/command", response_model=OrchestratorResponse)
def execute_command(
    request: OrchestratorRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
) -> OrchestratorResponse:
    """Unified entrypoint for executing work commands and inquiries from Chat or Voice."""
    return WorkOrchestratorService.handle_command(
        db=db,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        request=request,
    )
