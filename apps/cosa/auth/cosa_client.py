from __future__ import annotations

import os
from typing import Optional

import httpx
from pydantic import BaseModel

__all__ = ["CompanyMembership", "CosaControlPlaneAuthClient", "CosaControlPlaneAuthError"]


class CompanyMembership(BaseModel):
    """Khớp `CompanyMembershipInfo` trong services/cosa/services/company.service.ts."""

    company_id: str
    name: Optional[str] = None
    role_id: str


class CosaControlPlaneAuthError(Exception):
    """COSA control plane không xác nhận được membership — không được coi là
    ALLOW ngầm định khi gặp lỗi này (fail closed, theo §10.5 freshness invariant
    của COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md: thiếu
    observation = DENY/NOT_READY, không phải ALLOW)."""


class CosaControlPlaneAuthClient:
    """Client mỏng gọi `GET /platform/auth/me/companies` (services/cosa,
    expose:true, auth:true) để cross-check company membership của principal đã
    xác thực qua JWT — theo COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_
    2026-08-25.md §4.2: "Client header chỉ là requested scope, không phải
    nguồn sự thật". Không dùng endpoint internal `validate-membership`
    (expose:false) vì đó là RPC nội bộ Encore-to-Encore, không phải HTTP client
    thông thường gọi từ Python được.

    CHƯA có cross-check workspace_id (services/company chưa expose endpoint
    tương đương `resolveTenantContext` cho service ngoài gọi) — xem
    COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §29 mục theo dõi.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        timeout: float = 5.0,
    ) -> None:
        self._base_url = (base_url or os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")).rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, transport=transport, timeout=timeout)

    async def list_my_companies(self, bearer_token: str) -> list[CompanyMembership]:
        try:
            resp = await self._client.get(
                "/platform/auth/me/companies",
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
        except httpx.HTTPError as exc:
            raise CosaControlPlaneAuthError(f"không gọi được COSA control plane: {exc}") from exc

        if resp.status_code == 401:
            raise CosaControlPlaneAuthError("COSA control plane từ chối token")
        if resp.status_code != 200:
            raise CosaControlPlaneAuthError(
                f"COSA control plane trả lỗi {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise CosaControlPlaneAuthError(f"COSA control plane trả response không phải JSON: {exc}") from exc

        return [CompanyMembership(**c) for c in data.get("companies", [])]

    async def aclose(self) -> None:
        await self._client.aclose()
