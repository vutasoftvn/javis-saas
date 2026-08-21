"""Authorization cho hành động quản trị Central Control Plane - mirror
`core.authz` (Local Business DB, WorkspaceMember.role) nhưng nhắm
CompanyMembership.platform_role / PlatformUser.is_platform_admin."""
from typing import Optional
from fastapi import HTTPException, status

from platform_core.control_plane.models import CompanyMembership, PlatformUser

PLATFORM_PERMISSION_LEVELS = {
    "owner": 3,
    "admin": 2,
    "member": 1,
}

PLATFORM_ACTION_REQUIRED_LEVEL = {
    "company.manage": "admin",
}


def authorize_platform(
    membership: Optional[CompanyMembership], action: str
) -> None:
    """Kiểm tra quyền của 1 CompanyMembership cho hành động quản trị company.

    Raises 403 nếu không có membership hoặc role thấp hơn mức yêu cầu."""
    if membership is None or not hasattr(membership, "platform_role"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: company membership required",
        )

    member_level = PLATFORM_PERMISSION_LEVELS.get(membership.platform_role, 0)
    required_role = PLATFORM_ACTION_REQUIRED_LEVEL.get(action, "admin")
    required_level = PLATFORM_PERMISSION_LEVELS[required_role]

    if member_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action '{action}' requires {required_role} platform role",
        )


def require_platform_admin(user: PlatformUser) -> None:
    """Kiểm tra hành động toàn nền tảng (không thuộc 1 company cụ thể), vd.
    ký entitlement snapshot - chỉ PlatformUser.is_platform_admin=True mới gọi được."""
    if user is None or not getattr(user, "is_platform_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: platform admin required",
        )
