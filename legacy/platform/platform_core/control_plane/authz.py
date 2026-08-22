"""Authorization cho hành động quản trị Central Control Plane - mirror
`core.authz` (Local Business DB, WorkspaceMember.role) nhưng nhắm
2 trục quyền độc lập của control_plane:
- CompanyMembership.role_id (founder > co-founder > user) cho hành động
  trong phạm vi 1 company.
- PlatformUser.platform_role_id (superadmin > admin > support) cho hành
  động quản trị toàn nền tảng COSA - KHÔNG liên quan tới company nào."""
from typing import Optional
from fastapi import HTTPException, status

from platform_core.control_plane.models import CompanyMembership, PlatformUser

COMPANY_ROLE_LEVELS = {
    "founder": 3,
    "co-founder": 2,
    "user": 1,
}

COMPANY_ACTION_REQUIRED_ROLE = {
    "company.manage": "co-founder",
}

PLATFORM_STAFF_ROLE_LEVELS = {
    "superadmin": 3,
    "admin": 2,
    "support": 1,
}

PLATFORM_STAFF_ACTION_REQUIRED_ROLE = {
    "platform.manage": "admin",
}


def authorize_company(
    membership: Optional[CompanyMembership], action: str
) -> None:
    """Kiểm tra quyền của 1 CompanyMembership cho hành động trong phạm vi
    company (role_id: founder/co-founder/user).

    Raises 403 nếu không có membership hoặc role thấp hơn mức yêu cầu."""
    if membership is None or not hasattr(membership, "role_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: company membership required",
        )

    member_level = COMPANY_ROLE_LEVELS.get(membership.role_id, 0)
    required_role = COMPANY_ACTION_REQUIRED_ROLE.get(action, "co-founder")
    required_level = COMPANY_ROLE_LEVELS[required_role]

    if member_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action '{action}' requires {required_role} company role",
        )


def authorize_platform_staff(user: Optional[PlatformUser], action: str) -> None:
    """Kiểm tra hành động quản trị toàn nền tảng COSA (không thuộc 1 company
    cụ thể), vd. ký entitlement snapshot - chỉ PlatformUser có
    platform_role_id (superadmin/admin/support) mới gọi được. Đây là trục
    quyền độc lập với CompanyMembership.role_id: 1 founder của company không
    tự nhiên có quyền quản trị nền tảng."""
    role_id = getattr(user, "platform_role_id", None) if user is not None else None
    staff_level = PLATFORM_STAFF_ROLE_LEVELS.get(role_id, 0)
    required_role = PLATFORM_STAFF_ACTION_REQUIRED_ROLE.get(action, "admin")
    required_level = PLATFORM_STAFF_ROLE_LEVELS[required_role]

    if staff_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: action '{action}' requires {required_role} platform staff role",
        )
