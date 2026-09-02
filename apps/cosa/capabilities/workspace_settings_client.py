"""Thin HTTP client cho COSA Control Plane workspace skill policy endpoints.

Task 4 (Truthful MVP Hardening) — apps/cosa (Agent Platform composition
layer) KHÔNG tự lưu `workspace_skill_policies`. Nguồn sự thật thật sự nằm ở
`services/cosa` (Encore/TS, bảng `control_plane.workspace_skill_policies`,
migration 30). Client này chỉ forward bearer token + workspace ID sang
`/platform/workspaces/:workspaceId/skill-policies[...]` — mọi validate
skillKey với registry riêng của Agent Platform xảy ra ở caller
(`apps/cosa/api/settings_routes.py`) TRƯỚC khi gọi client này.
"""

from __future__ import annotations

from typing import Any

import httpx

from apps.cosa.config.planes import resolve_platform_control_plane_url

__all__ = ["WorkspaceSettingsClient", "WorkspaceSettingsClientError"]


class WorkspaceSettingsClientError(Exception):
    """Control plane không phản hồi được (mạng lỗi, timeout, hoặc status lỗi).

    Caller (settings_routes.py) PHẢI map exception này thành HTTP 503 —
    tuyệt đối không được nuốt lỗi rồi trả `data: []`/success giả (đây chính
    là bug đã phát hiện ở `settings_routes.py` cũ: `except Exception: pass`
    khiến registry lỗi bị báo cáo thành "danh sách rỗng" thay vì "không rõ").
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class WorkspaceSettingsClient:
    """Gọi COSA Control Plane (`services/cosa`) để đọc/ghi
    `workspace_skill_policies` thay mặt Agent Platform composition layer."""

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = (base_url or resolve_platform_control_plane_url()).rstrip("/")
        self.timeout = timeout

    async def list_policies(self, *, workspace_id: str, bearer_token: str) -> list[dict[str, Any]]:
        """`GET /platform/workspaces/:workspaceId/skill-policies` — trả danh
        sách policy đã persist (có thể rỗng nếu workspace chưa cấu hình skill
        nào — khác với "control plane không phản hồi được")."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(
                    f"{self.base_url}/platform/workspaces/{workspace_id}/skill-policies",
                    headers={"Authorization": f"Bearer {bearer_token}"},
                )
        except httpx.HTTPError as exc:
            raise WorkspaceSettingsClientError(
                f"workspace settings control plane unreachable: {exc}"
            ) from exc

        if res.status_code >= 400:
            raise WorkspaceSettingsClientError(
                f"control plane returned {res.status_code} listing skill policies",
                status_code=res.status_code,
            )

        try:
            body = res.json()
        except ValueError as exc:
            raise WorkspaceSettingsClientError(
                "control plane returned malformed JSON listing skill policies"
            ) from exc

        data = body.get("data") if isinstance(body, dict) else None
        return data if isinstance(data, list) else []

    async def put_policy(
        self,
        *,
        workspace_id: str,
        skill_key: str,
        enabled: bool,
        config: dict[str, Any],
        bearer_token: str,
    ) -> dict[str, Any]:
        """`PUT /platform/workspaces/:workspaceId/skill-policies/:skillKey` —
        trả policy đã persist (đã tăng `revision`) từ control plane, KHÔNG
        phải giá trị echo lại từ request."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.put(
                    f"{self.base_url}/platform/workspaces/{workspace_id}/skill-policies/{skill_key}",
                    headers={"Authorization": f"Bearer {bearer_token}"},
                    json={"enabled": enabled, "config": config},
                )
        except httpx.HTTPError as exc:
            raise WorkspaceSettingsClientError(
                f"workspace settings control plane unreachable: {exc}"
            ) from exc

        if res.status_code >= 400:
            raise WorkspaceSettingsClientError(
                f"control plane returned {res.status_code} updating skill policy",
                status_code=res.status_code,
            )

        try:
            body = res.json()
        except ValueError as exc:
            raise WorkspaceSettingsClientError(
                "control plane returned malformed JSON updating skill policy"
            ) from exc

        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict):
            raise WorkspaceSettingsClientError(
                "control plane returned malformed skill policy payload"
            )
        return data
