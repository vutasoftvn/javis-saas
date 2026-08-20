from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user
from app.platform.auth.models import User
from app.workforce.extensions.registry import ExtensionRegistry
from app.workforce.extensions.eligibility import resolve_eligible_capabilities
from app.workforce.extensions.contracts import ProviderProtocolError, ProviderUnavailableError
from app.workforce.extensions.mcp_provider import MCPProvider
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
        try:
            registry.enable(db, workspace_id, ext_id)
        except LookupError:
            raise HTTPException(status_code=404, detail="Extension not found")
    else:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    return {"status": "ok"}


@router.post("/api/v1/workspaces/{workspace_id}/extensions/{ext_id}/discover")
async def discover_extension(
    workspace_id: int,
    ext_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registry = ExtensionRegistry()
    registration = registry.get(db, workspace_id, ext_id)
    if registration is None:
        raise HTTPException(status_code=404, detail="Extension not found")

    manifest = registration.manifest_jsonb
    config = dict(manifest["provider_config"])
    config["extension_id"] = registration.extension_id
    scope = ExecutionScope(
        workspace_id=workspace_id,
        company_id=workspace_id,
        principal_user_id=user.id,
        principal_member_id=0,
        principal_role="owner",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=(),
    )
    try:
        capabilities = await MCPProvider().discover(scope, config)
    except (ProviderProtocolError, ProviderUnavailableError):
        registry.record_discovery_failure(db, workspace_id, ext_id)
        raise HTTPException(status_code=502, detail="Extension discovery failed")
    saved = registry.record_discovery(db, workspace_id, ext_id, capabilities)

    return {
        "extension_id": saved.extension_id,
        "status": saved.status,
        "capability_count": len(saved.capabilities_jsonb["capabilities"]),
    }
