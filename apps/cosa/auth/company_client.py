from __future__ import annotations

import os
from typing import Optional

import httpx
from pydantic import BaseModel

__all__ = ["ResolvedTenantContext", "CompanyTenantContextClient", "CompanyTenantContextError"]


class ResolvedTenantContext(BaseModel):
    """Khớp `TenantContext` trong services/company/shared/types/tenant_context.ts."""

    company_id: str
    workspace_id: str
    user_id: str
    membership_role: str
    permissions: list[str]
    correlation_id: str


class CompanyTenantContextError(Exception):
    """Không resolve được TenantContext thật từ services/company — call site
    PHẢI coi đây là DENY, không phải ALLOW ngầm (cùng nguyên tắc §10.5
    freshness invariant đã áp dụng cho CosaControlPlaneAuthError)."""


class CompanyTenantContextClient:
    """Client mỏng gọi `POST /identity/tenant-context/resolve`
    (services/company, expose:true — apps/cosa/auth/company_client.py,
    xem services/company/identity/handlers/tenant-context.handler.ts) để
    cross-check workspace membership của principal đã xác thực — theo
    COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §6.1."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        timeout: float = 5.0,
    ) -> None:
        self._base_url = (base_url or os.environ.get("COMPANY_SERVICE_URL", "http://localhost:4000")).rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, transport=transport, timeout=timeout)

    async def resolve(self, bearer_token: str, company_id: str) -> ResolvedTenantContext:
        try:
            resp = await self._client.post(
                "/identity/tenant-context/resolve",
                json={"companyId": company_id},
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
        except httpx.HTTPError as exc:
            raise CompanyTenantContextError(f"không gọi được services/company: {exc}") from exc

        if resp.status_code != 200:
            raise CompanyTenantContextError(
                f"services/company trả lỗi {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise CompanyTenantContextError(f"services/company trả response không phải JSON: {exc}") from exc

        try:
            return ResolvedTenantContext(
                company_id=data["companyId"],
                workspace_id=data["workspaceId"],
                user_id=data["userId"],
                membership_role=data["membershipRole"],
                permissions=data.get("permissions", []),
                correlation_id=data["correlationId"],
            )
        except KeyError as exc:
            raise CompanyTenantContextError(f"response thiếu field bắt buộc: {exc}") from exc

    async def aclose(self) -> None:
        await self._client.aclose()
