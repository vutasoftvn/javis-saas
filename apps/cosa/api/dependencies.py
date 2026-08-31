from __future__ import annotations

from fastapi import HTTPException, Request, status

from apps.cosa.auth.dependency import AuthenticatedIdentity
from apps.cosa.composition.agent_plane import CosaAgentPlane


def get_cosa_plane(request: Request) -> CosaAgentPlane:
    """Dependency injection from `app.state.plane`."""
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError(
            "CosaAgentPlane is not ready — app.state.plane is empty. Lifespan startup "
            "has not executed or app was initialized improperly."
        )
    return plane


def require_workspace_access(identity: AuthenticatedIdentity, workspace_id: str) -> None:
    """Verify that authenticated identity has access to target workspace."""
    if identity.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: identity does not belong to the requested workspace",
        )
