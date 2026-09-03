from __future__ import annotations

import os

import httpx
from pydantic import BaseModel

__all__ = [
    "ResolvedWorkspaceTenantContext",
    "WorkspaceTenantContextClient",
    "WorkspaceTenantContextError",
]


class ResolvedWorkspaceTenantContext(BaseModel):
    """Khớp workspace-only part của `TenantContext` trong
    services/company/shared/types/tenant_context.ts."""

    workspace_id: str
    user_id: str
    membership_role: str
    permissions: list[str]
    correlation_id: str
    # B5 fix — platform_user_id thật của user local này (None nếu chưa từng
    # sync qua platform) — dùng để mint control-plane delegation khi identity
    # gốc là local_session. Xem apps/cosa/auth/jwt.py::mint_control_plane_delegation.
    platform_user_id: str | None = None


class WorkspaceTenantContextError(Exception):
    """Không resolve được workspace context thật từ services/company — call site
    PHẢI coi đây là DENY, không phải ALLOW ngầm (cùng nguyên tắc §10.5
    freshness invariant)."""


class WorkspaceTenantContextClient:
    """Client mỏng gọi `POST /identity/tenant-context/resolve` với workspace scope
    (services/company, expose:true) để cross-check workspace membership của
    principal đã xác thực."""

    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._base_url = (
            base_url or os.environ.get("COMPANY_SERVICE_URL", "http://localhost:4000")
        ).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url, transport=transport, timeout=timeout
        )

    async def resolve(self, bearer_token: str, workspace_id: str) -> ResolvedWorkspaceTenantContext:
        """Resolve workspace tenant context for workspace-only scope."""
        try:
            resp = await self._client.post(
                "/identity/tenant-context/resolve",
                json={"workspaceId": workspace_id},
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
        except httpx.HTTPError as exc:
            raise WorkspaceTenantContextError(f"không gọi được services/company: {exc}") from exc

        if resp.status_code != 200:
            raise WorkspaceTenantContextError(
                f"services/company trả lỗi {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise WorkspaceTenantContextError(
                f"services/company trả response không phải JSON: {exc}"
            ) from exc

        try:
            return ResolvedWorkspaceTenantContext(
                workspace_id=data["workspaceId"],
                user_id=data["userId"],
                membership_role=data["membershipRole"],
                permissions=data.get("permissions", []),
                correlation_id=data["correlationId"],
                platform_user_id=data.get("platformUserId"),
            )
        except KeyError as exc:
            raise WorkspaceTenantContextError(f"response thiếu field bắt buộc: {exc}") from exc

    async def aclose(self) -> None:
        await self._client.aclose()
