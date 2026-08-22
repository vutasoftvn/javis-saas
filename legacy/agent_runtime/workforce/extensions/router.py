from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from core.auth import get_current_workspace_member
from platform_core.auth.models import WorkspaceMember
from workforce.extensions.registry import ExtensionRegistry
from workforce.extensions.eligibility import resolve_eligible_capabilities
from workforce.extensions.contracts import ProviderProtocolError, ProviderUnavailableError
from workforce.extensions.mcp_provider import MCPProvider
from workforce.agents.runtime.execution_scope import ExecutionScope

router = APIRouter()

class ExtensionStatusUpdate(BaseModel):
    status: Literal["enabled", "disabled"]
    reason: str | None = None


def _require_workspace_admin(workspace_id: int, member: WorkspaceMember) -> WorkspaceMember:
    """Extension install/discover/status changes are workspace-admin actions - a
    member of a different workspace, or a non-owner/admin member of this one, must
    never reach the registry or an outbound discovery call."""
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Member does not belong to this workspace")
    if member.role not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin role required")
    return member


@router.get("/api/v1/workspaces/{workspace_id}/extensions")
def list_extensions(
    workspace_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    member = _require_workspace_admin(workspace_id, member)

    registry = ExtensionRegistry()
    registrations = registry.get_all(db, workspace_id)

    scope = ExecutionScope(
        workspace_id=workspace_id,
        company_id=workspace_id,
        principal_user_id=member.user_id,
        principal_member_id=member.id,
        principal_role=member.role,
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=()
    )
    
    eligible = resolve_eligible_capabilities(db, scope)
    eligible_by_extension: dict[str, list] = {}
    for ec in eligible:
        eligible_by_extension.setdefault(ec.extension_id, []).append(ec)

    result = []
    for reg in registrations:
        # Sourced from the discovered snapshot (via eligibility), not the manifest -
        # the manifest is install-time intent, the snapshot is what was actually
        # discovered and is what dispatch will actually use.
        ext_caps = [
            {
                "id": ec.capability_id,
                "name": ec.name,
                "eligible": ec.eligible,
                "reason_code": ec.reason_code,
            }
            for ec in eligible_by_extension.get(reg.extension_id, [])
        ]

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
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    _require_workspace_admin(workspace_id, member)
    registry = ExtensionRegistry()

    if update.status == "disabled":
        registry.disable(db, workspace_id, ext_id, update.reason or "operator disabled")
    else:
        try:
            registry.enable(db, workspace_id, ext_id)
        except LookupError:
            raise HTTPException(status_code=404, detail="Extension not found")

    return {"status": "ok"}


@router.post("/api/v1/workspaces/{workspace_id}/extensions/{ext_id}/discover")
async def discover_extension(
    workspace_id: int,
    ext_id: str,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    member = _require_workspace_admin(workspace_id, member)
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
        principal_user_id=member.user_id,
        principal_member_id=member.id,
        principal_role=member.role,
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
