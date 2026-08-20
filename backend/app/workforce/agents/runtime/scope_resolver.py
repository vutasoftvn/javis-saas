from sqlalchemy.orm import Session
from app.platform.auth.models import WorkspaceMember
from core.organization.models import OperatingUnit, Offering
from core.strategy.initiative import Initiative
from app.workforce.agents.runtime.execution_scope import ScopeRequest, ExecutionScope, ScopeResolutionError

def resolve_execution_scope(db: Session, member: WorkspaceMember, request: ScopeRequest) -> ExecutionScope:
    workspace_id = member.workspace_id
    
    unit = db.query(OperatingUnit).filter(
        OperatingUnit.id == request.operating_unit_id, 
        OperatingUnit.workspace_id == workspace_id
    ).first() if request.operating_unit_id else None
    
    if request.operating_unit_id and unit is None:
        raise ScopeResolutionError("operating unit is outside workspace")
        
    offering = db.query(Offering).filter(
        Offering.id == request.offering_id, 
        Offering.workspace_id == workspace_id
    ).first() if request.offering_id else None
    
    if request.offering_id and offering is None:
        raise ScopeResolutionError("offering is outside workspace")
        
    if unit and offering and offering.operating_unit_id != unit.id:
        raise ScopeResolutionError("offering is outside operating unit")
        
    initiative = db.query(Initiative).filter(
        Initiative.id == request.initiative_id, 
        Initiative.workspace_id == workspace_id
    ).first() if request.initiative_id else None
    
    if request.initiative_id and initiative is None:
        raise ScopeResolutionError("initiative is outside workspace")
        
    if offering and initiative and initiative.offering_id != offering.id:
        raise ScopeResolutionError("initiative is outside offering")
        
    return ExecutionScope(
        workspace_id=workspace_id, 
        company_id=workspace_id,
        principal_user_id=member.user_id, 
        principal_member_id=member.id,
        principal_role=member.role, 
        operating_unit_id=unit.id if unit else None,
        offering_id=offering.id if offering else None,
        initiative_id=initiative.id if initiative else None,
        profile_id=request.profile_id, 
        session_id=request.session_id,
        grants=tuple(sorted(set(request.grants))),
    )
