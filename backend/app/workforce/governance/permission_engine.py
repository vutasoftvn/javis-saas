from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.workforce.models import UnifiedPermission
from app.core.snowflake import generate_snowflake_id


class UnifiedPermissionEngine:
    """Permission Engine hợp nhất kiểm tra quyền hạn (RBAC/ABAC) cho cả Human User và AI Agent."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def can(
        self,
        principal_type: str,  # 'USER' | 'AGENT'
        principal_id: int,
        resource_type: str,   # 'TOOL' | 'DATA' | 'MODULE' | 'BUDGET'
        resource_key: str,    # vd: 'crm.update', 'finance.post_entry', '*'
        action: str = "EXECUTE",
        workspace_id: Optional[int] = None,
    ) -> bool:
        """Kiểm tra xem Principal có quyền thực thi Action trên Resource hay không."""
        # 1. Tra cứu quyền chính xác
        stmt = select(UnifiedPermission).where(
            and_(
                UnifiedPermission.principal_type == principal_type.upper(),
                UnifiedPermission.principal_id == principal_id,
                UnifiedPermission.resource_type == resource_type.upper(),
                UnifiedPermission.resource_key.in_([resource_key, "*"]),
                UnifiedPermission.action.in_([action.upper(), "ADMIN", "*"]),
            )
        )
        if workspace_id is not None:
            stmt = stmt.where(UnifiedPermission.workspace_id == workspace_id)

        res = await self.db.execute(stmt)
        perm = res.scalars().first()

        if perm is not None:
            return perm.is_allowed

        # Mặc định Principle of Least Privilege: Cho phép READ/SEARCH an toàn, chặn MUTATE nhạy cảm nếu chưa grant
        safe_actions = ["READ", "SEARCH", "HELP", "EXECUTE"]
        if action.upper() in safe_actions and ("post_" not in resource_key and "delete_" not in resource_key and "publish" not in resource_key):
            return True

        return False

    async def grant_permission(
        self,
        principal_type: str,
        principal_id: int,
        resource_type: str,
        resource_key: str,
        action: str = "EXECUTE",
        is_allowed: bool = True,
        requires_approval: bool = False,
        workspace_id: Optional[int] = None,
    ) -> UnifiedPermission:
        """Cấp hoặc cập nhật quyền hạn cho Principal."""
        stmt = select(UnifiedPermission).where(
            and_(
                UnifiedPermission.principal_type == principal_type.upper(),
                UnifiedPermission.principal_id == principal_id,
                UnifiedPermission.resource_type == resource_type.upper(),
                UnifiedPermission.resource_key == resource_key,
                UnifiedPermission.action == action.upper(),
                UnifiedPermission.workspace_id == workspace_id,
            )
        )
        res = await self.db.execute(stmt)
        perm = res.scalars().first()

        if perm:
            perm.is_allowed = is_allowed
            perm.requires_approval = requires_approval
        else:
            perm = UnifiedPermission(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                principal_type=principal_type.upper(),
                principal_id=principal_id,
                resource_type=resource_type.upper(),
                resource_key=resource_key,
                action=action.upper(),
                is_allowed=is_allowed,
                requires_approval=requires_approval,
            )
            self.db.add(perm)

        await self.db.flush()
        return perm
