"""Unified WorkspaceContext (G2 §6.4 P0.4 / G3 §9.4).

Trước fix này, một số endpoint (`workforce/api/cofounder_api.py`,
`workforce/api/packs_api.py`) tin thẳng `workspace_id` nhận từ query/body của
client mà không verify user thực sự thuộc workspace đó — cho phép user A đọc
dữ liệu workspace B chỉ bằng cách đổi số trên URL/payload. Khi `workspace_id`
bị bỏ trống (mặc định của mọi call hiện tại từ Flutter), các service method
lại không filter theo workspace nào cả — tức là leak dữ liệu toàn bộ workspace
khác nhau vào cùng 1 response.

`get_workspace_context`/`resolve_workspace_context` đóng cả hai lỗ hổng:
- Nếu `workspace_id` được cung cấp: verify qua `WorkspaceMember`, reject 403
  nếu user không thuộc workspace đó.
- Nếu không cung cấp (đúng hành vi thật hiện tại của Flutter — mọi call của
  `founder_command_center_controller.dart` đều không truyền workspace_id):
  tự resolve về workspace duy nhất mà user thuộc về, KHÔNG fallback về "không
  filter gì cả".

`company_id`/`company_stage`/`entitlement_*` được derive server-side, không
bao giờ lấy trực tiếp từ input của client.
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.platform.auth.models import User, Workspace, WorkspaceMember
from app.platform.sync.entitlement_manager import EntitlementManager


@dataclass(frozen=True)
class WorkspaceContext:
    user_id: int
    workspace_id: int
    company_id: Optional[str]
    role: str
    company_stage: str
    entitlement_plan: str
    entitlement_mode: str


def _load_entitlement(platform_company_id: Optional[str]) -> tuple[str, str]:
    """Best-effort entitlement lookup; never raises — an unlicensed/unlinked
    workspace should still resolve a WorkspaceContext (Free tier), it just
    won't unlock paid features downstream."""
    if not platform_company_id:
        return "free", "ACTIVE"
    try:
        snapshot = EntitlementManager.get_snapshot(platform_company_id)
        mode = EntitlementManager.get_status_mode(platform_company_id)
        return snapshot.plan, mode.value
    except Exception:
        return "free", "ACTIVE"


def resolve_workspace_context(
    db: Session,
    user: User,
    workspace_id: Optional[int] = None,
) -> WorkspaceContext:
    """Build a verified WorkspaceContext for `user`.

    Raises 403 if `workspace_id` is given and `user` is not a member.
    Raises 404 if `workspace_id` is omitted and `user` belongs to no
    workspace at all (should not happen post-registration, but fail closed
    rather than silently scope to nothing).
    """
    if workspace_id is not None:
        member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
            )
            .first()
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of this workspace",
            )
    else:
        member = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.user_id == user.id)
            .first()
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User does not belong to any workspace",
            )
        workspace_id = member.workspace_id

    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    entitlement_plan, entitlement_mode = _load_entitlement(workspace.platform_company_id)

    return WorkspaceContext(
        user_id=user.id,
        workspace_id=workspace_id,
        company_id=workspace.platform_company_id,
        role=member.role,
        company_stage=workspace.company_stage,
        entitlement_plan=entitlement_plan,
        entitlement_mode=entitlement_mode,
    )


def get_workspace_context(
    workspace_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceContext:
    """FastAPI dependency for endpoints that take `workspace_id` as a query param.

    For endpoints where `workspace_id` instead lives inside a request body,
    call `resolve_workspace_context(db, current_user, req.workspace_id)`
    directly in the handler instead of using this dependency.
    """
    return resolve_workspace_context(db, current_user, workspace_id)
