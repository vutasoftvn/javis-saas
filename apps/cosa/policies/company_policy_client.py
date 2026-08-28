from __future__ import annotations

import os
from typing import Optional

import httpx

from apps.cosa.config.planes import resolve_platform_control_plane_url
from apps.cosa.policies.snapshot import PolicySnapshot, TenantPolicyRule

__all__ = ["CosaTenantPolicyClient", "CosaTenantPolicyError"]


class CosaTenantPolicyError(Exception):
    """Không resolve được PolicySnapshot thật — call site PHẢI coi đây là
    DENY/NOT_READY, không phải ALLOW ngầm (§10.5 freshness invariant của
    COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md)."""


class CosaTenantPolicyClient:
    """Client mỏng gọi `GET /platform/auth/me/agent-policy-snapshot`
    (services/cosa, expose:true auth:true — mới thêm trong phiên này, xem
    services/cosa/handlers/agent-policy.handler.ts::getMyTenantPolicySnapshot)
    để lấy toàn bộ `cosa.company_agent_policy` rows của company đang xác thực
    + trạng thái company/user hiện tại, resolve 1 lần tại boundary (run-start
    hoặc trước resume), không gọi lại mỗi tool call.

    CHƯA runtime-verify bằng Encore CLI thật (môi trường phiên này không có
    Docker/Encore CLI) — chỉ verify tĩnh (type-check thủ công, đối chiếu
    pattern với `getTenantPolicy`/`listMyCompanies` đã có sẵn và đang chạy).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        timeout: float = 5.0,
    ) -> None:
        self._base_url = (base_url or resolve_platform_control_plane_url()).rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, transport=transport, timeout=timeout)

    async def get_snapshot(self, bearer_token: str, workspace_id: str) -> PolicySnapshot:
        try:
            resp = await self._client.get(
                "/platform/auth/me/agent-policy-snapshot",
                params={"workspaceId": workspace_id},
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
        except httpx.HTTPError as exc:
            raise CosaTenantPolicyError(f"không gọi được COSA control plane: {exc}") from exc

        if resp.status_code != 200:
            raise CosaTenantPolicyError(
                f"COSA control plane trả lỗi {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise CosaTenantPolicyError(f"COSA control plane trả response không phải JSON: {exc}") from exc

        try:
            return PolicySnapshot(
                workspace_id=data["workspaceId"],
                workspace_status=data["workspaceStatus"],
                principal_status=data["principalStatus"],
                rules=[
                    TenantPolicyRule(
                        tool_pattern=r["toolPattern"],
                        decision=r["decision"],
                        reason=r.get("reason"),
                    )
                    for r in data["rules"]
                ],
                snapshot_hash=data["snapshotHash"],
            )
        except KeyError as exc:
            raise CosaTenantPolicyError(f"response thiếu field bắt buộc: {exc}") from exc

    async def aclose(self) -> None:
        await self._client.aclose()
