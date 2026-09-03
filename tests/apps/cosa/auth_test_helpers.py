from __future__ import annotations

from fastapi import FastAPI

from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity

__all__ = ["override_authenticated_identity"]


_UNSET = object()


def override_authenticated_identity(
    app: FastAPI,
    *,
    principal_id: str = "user:test_user",
    platform_user_id: str = "test_user",
    workspace_id: str = "test_ws_1",
    role_id: str = "founder",
    resolved_platform_user_id: str | None = _UNSET,  # type: ignore[assignment]
) -> AuthenticatedIdentity:
    """Override `get_authenticated_identity` (cùng cơ chế FastAPI
    `dependency_overrides` chuẩn) để test HTTP endpoint không cần JWT/COSA
    control plane thật. Trả về identity đã set để test có thể tái sử dụng
    (vd. kiểm tra tenant isolation bằng 1 identity khác). Workspace-only scope.

    B5 fix — `resolved_platform_user_id` mặc định LẤY THEO `platform_user_id`
    (identity test coi như đã sync qua platform, giống đại đa số user thật) để
    `mint_control_plane_delegation()` hoạt động được trong test hiện có mà
    không cần sửa từng call site. Truyền tường minh `resolved_platform_user_id=
    None` để test riêng nhánh "chưa sync qua platform" (MissingPlatformIdentityError)."""
    resolved = platform_user_id if resolved_platform_user_id is _UNSET else resolved_platform_user_id
    identity = AuthenticatedIdentity(
        principal_id=principal_id,
        platform_user_id=platform_user_id,
        workspace_id=workspace_id,
        role_id=role_id,
        bearer_token="test-bearer-token",
        resolved_platform_user_id=resolved,
    )

    async def _fake_identity() -> AuthenticatedIdentity:
        return identity

    app.dependency_overrides[get_authenticated_identity] = _fake_identity
    return identity
