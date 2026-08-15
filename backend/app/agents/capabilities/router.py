from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.capabilities.registry import list_capabilities
from app.agents.capabilities.service import CapabilityCheckResult, CapabilityGateway
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db

router = APIRouter()


class CapabilityCheckRequest(BaseModel):
    subject_type: str = "agent"  # agent, user, mini_app, workflow
    subject_id: str
    capability: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    permission_profile: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class CapabilityGrantCreateRequest(BaseModel):
    subject_type: str = "agent"
    subject_id: str
    capability: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    scope: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class CapabilityExecuteRequest(BaseModel):
    subject_type: str = "agent"
    subject_id: str
    capability: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None
    approval_id: Optional[int] = None
    run_id: Optional[int] = None


def _format_grant(grant) -> Dict[str, Any]:
    return {
        "id": str(grant.id),
        "workspace_id": str(grant.workspace_id),
        "subject_type": grant.subject_type,
        "subject_id": grant.subject_id,
        "capability": grant.capability,
        "resource_type": grant.resource_type,
        "resource_id": grant.resource_id,
        "scope": grant.scope_jsonb or {},
        "granted_by": str(grant.granted_by) if grant.granted_by else None,
        "created_at": grant.created_at.isoformat() if grant.created_at else None,
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
        "revoked_at": grant.revoked_at.isoformat() if grant.revoked_at else None,
        "notes": grant.notes,
    }


@router.post("/check", response_model=CapabilityCheckResult)
async def check_capability(
    payload: CapabilityCheckRequest,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> CapabilityCheckResult:
    """Evaluate whether a subject is authorized for a specific capability."""
    return await CapabilityGateway.check(
        db=db,
        workspace_id=current_member.workspace_id,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        capability=payload.capability,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        permission_profile=payload.permission_profile,
        params=payload.params,
    )


@router.post("/grants", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_grant(
    payload: CapabilityGrantCreateRequest,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> Dict[str, Any]:
    """Grant a capability authorization to an agent or subject."""
    grant = CapabilityGateway.grant(
        db=db,
        workspace_id=current_member.workspace_id,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        capability=payload.capability,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        scope=payload.scope,
        granted_by=current_member.user_id,
        expires_at=payload.expires_at,
        notes=payload.notes,
    )
    return _format_grant(grant)


@router.get("/grants", response_model=List[Dict[str, Any]])
def list_grants(
    subject_id: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> List[Dict[str, Any]]:
    """List capability grants in the current workspace."""
    grants = CapabilityGateway.list_grants(
        db=db,
        workspace_id=current_member.workspace_id,
        subject_id=subject_id,
        active_only=active_only,
    )
    return [_format_grant(g) for g in grants]


@router.post("/grants/{grant_id}/revoke", response_model=Dict[str, Any])
def revoke_grant(
    grant_id: int,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> Dict[str, Any]:
    """Revoke an existing capability grant."""
    grant = CapabilityGateway.revoke(
        db=db,
        workspace_id=current_member.workspace_id,
        grant_id=grant_id,
        user_id=current_member.user_id,
    )
    if not grant:
        raise HTTPException(status_code=404, detail="Capability grant not found")
    return _format_grant(grant)


@router.get("/catalog", response_model=List[Dict[str, Any]])
def get_catalog(
    domain: Optional[str] = None,
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> List[Dict[str, Any]]:
    """Retrieve catalog of all registered capabilities."""
    defs = list_capabilities(domain=domain)
    return [
        {
            "name": d.name,
            "domain": d.domain,
            "resource": d.resource,
            "action": d.action,
            "risk_level": d.risk_level.value,
            "permission_level": d.permission_level.value,
            "requires_approval": d.requires_approval,
            "is_strong_approval": d.is_strong_approval,
            "description": d.description,
        }
        for d in defs
    ]


@router.post("/execute", response_model=Dict[str, Any])
async def execute_capability(
    payload: CapabilityExecuteRequest,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> Dict[str, Any]:
    """Execute action through Capability Gateway with idempotency and authorization."""
    return await CapabilityGateway.execute_with_capability(
        db=db,
        workspace_id=current_member.workspace_id,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        capability=payload.capability,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        params=payload.params,
        idempotency_key=payload.idempotency_key,
        approval_id=payload.approval_id,
        run_id=payload.run_id,
        user_id=current_member.user_id,
    )
