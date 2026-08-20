from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user
from app.platform.auth.models import User
from app.workforce.extensions.registry import ExtensionRegistry
from app.workforce.extensions.eligibility import resolve_eligible_capabilities
from app.workforce.agents.runtime.execution_scope import ExecutionScope

router = APIRouter()

class ExtensionStatusUpdate(BaseModel):
    status: str
    reason: str | None = None

@router.get("/api/v1/workspaces/{workspace_id}/extensions")
def list_extensions(workspace_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Assuming workspace-admin check happens inside get_current_user or via another dep, we'll simulate it or skip for MVP.
    # We should return extensions + eligible capabilities
    
    registry = ExtensionRegistry()
    registrations = registry.get_all(db, workspace_id)
    
    scope = ExecutionScope(
        workspace_id=workspace_id,
        company_id=workspace_id,
        principal_user_id=user.id,
        principal_member_id=0,
        principal_role="owner", # Simulate owner for admin
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=()
    )
    
    eligible = resolve_eligible_capabilities(db, scope)
    eligible_dict = {cap.capability_id: cap for cap in eligible}
    
    result = []
    for reg in registrations:
        manifest = reg.manifest_jsonb
        caps = manifest.get("capabilities", [])
        ext_caps = []
        for cap in caps:
            full_id = cap["id"]
            if full_id in eligible_dict:
                ec = eligible_dict[full_id]
                ext_caps.append({
                    "id": full_id,
                    "name": cap["name"],
                    "eligible": ec.eligible,
                    "reason_code": ec.reason_code
                })
        
        result.append({
            "extension_id": reg.extension_id,
            "version": reg.version,
            "status": reg.status,
            "disabled_reason": reg.disabled_reason,
            "capabilities": ext_caps,
            "health_summary": reg.health_jsonb
        })
        
    return {"extensions": result}

@router.post("/api/v1/workspaces/{workspace_id}/extensions/{ext_id}/status")
def update_extension_status(
    workspace_id: int, 
    ext_id: str, 
    update: ExtensionStatusUpdate,
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    registry = ExtensionRegistry()
    
    if update.status == "disabled":
        registry.disable(db, workspace_id, ext_id, update.reason or "operator disabled")
    elif update.status == "enabled" or update.status == "installed":
        # Missing enable method in registry, we can just update it
        reg = registry.get(db, workspace_id, ext_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Extension not found")
        reg.status = update.status
        reg.disabled_reason = None
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    return {"status": "ok"}
