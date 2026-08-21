"""Centralized Authorization & RBAC for COSA OS Protected Resources.

Implements 15A OPC Admin Governance with consistent role levels and protected action rules.
"""

from typing import Any, Optional
from fastapi import HTTPException, status
from db.models import WorkspaceMember


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
    "project.create",
    "project.update",
    "project.delete",
    "project.confirm_roadmap",
    "organization.manage",
}

# Actions requiring a stricter level than the "admin" default applied to every other
# entry in PROTECTED_ACTIONS. Prompt edits change AI behavior for the whole workspace,
# so only the workspace owner (founder) may write or reset them.
ACTION_REQUIRED_LEVEL = {
    "prompt.update": "owner",
    "prompt.reset": "owner",
}


def authorize(member: WorkspaceMember, action: str, resource: Optional[Any] = None) -> None:
    """Authorize workspace member for an action against protected system resources.

    Raises 403 Forbidden if the action is protected and the member role is below the
    action's required level (ACTION_REQUIRED_LEVEL, defaulting to "admin").
    """
    if member is None or not hasattr(member, "role"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: workspace membership required",
        )

    member_level = PERMISSION_LEVELS.get(member.role, 0)
    required_role = ACTION_REQUIRED_LEVEL.get(action, "admin")
    required_level = PERMISSION_LEVELS[required_role]

    if action in PROTECTED_ACTIONS and member_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action '{action}' requires {required_role} role in this workspace",
        )
