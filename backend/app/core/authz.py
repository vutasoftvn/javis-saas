"""Centralized Authorization & RBAC for COSA OS Protected Resources.

Implements 15A OPC Admin Governance with consistent role levels and protected action rules.
"""

from typing import Any, Optional
from fastapi import HTTPException, status
from app.db.models import WorkspaceMember


# Role levels matching vault_repo.py ROLE_LEVELS
PERMISSION_LEVELS = {
    "owner": 4,
    "admin": 3,
    "editor": 2,
    "member": 2,
    "viewer": 1,
}

PROTECTED_ACTIONS = {
    "spec.read",
    "spec.update",
    "spec.approve",
    "spec.reset",
    "prompt.read",
    "prompt.update",
    "prompt.reset",
    "skill.read",
    "skill.update",
    "skill.reset",
    "policy.read",
    "policy.update",
    "policy.reset",
    "agent.configure",
    "tool.configure",
    "approval_policy.configure",
    "employee.invite",
    "employee.role.assign",
    "employee.disable",
}


def authorize(member: WorkspaceMember, action: str, resource: Optional[Any] = None) -> None:
    """Authorize workspace member for an action against protected system resources.

    Raises 403 Forbidden if the action is protected and the member role is below admin.
    """
    if member is None or not hasattr(member, "role"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: workspace membership required",
        )

    member_level = PERMISSION_LEVELS.get(member.role, 0)
    required_level = PERMISSION_LEVELS["admin"]

    if action in PROTECTED_ACTIONS and member_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action '{action}' requires admin role in this workspace",
        )
