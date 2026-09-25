from __future__ import annotations

import os
from typing import Any

import httpx

from apps.cosa.auth.jwt import mint_worker_service_jwt

__all__ = [
    "ExecutiveBoardAuthorityError",
    "ExecutiveBoardClient",
    "ExecutiveBoardClientError",
]


class ExecutiveBoardClientError(Exception):
    """Lỗi chung khi giao tiếp với Company plane cho Executive Advisory Board."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ExecutiveBoardAuthorityError(ExecutiveBoardClientError):
    """Lỗi khi bị từ chối quyền hoặc thông tin frame không khớp."""


class ExecutiveBoardClient:
    """Client gọi Company service internal endpoints cho Executive Advisory Board.

    Đảm bảo:
    - Xác thực bằng service token / JWT.
    - Không truy cập trực tiếp DB Company.
    - Gửi kết quả callback analysis (hoàn tất hoặc thất bại).
    """

    @property
    def service_token(self) -> str:
        return self._static_service_token or mint_worker_service_jwt(
            worker_id="executive-board-worker"
        )

    def __init__(
        self,
        base_url: str | None = None,
        service_token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("COMPANY_SERVICE_URL")
            or os.getenv("COMPANY_URL")
            or "http://localhost:4000"
        ).rstrip("/")
        # Không ký JWT ở constructor: token chỉ sống 5 phút nên client sống lâu
        # (tạo lúc worker khởi động) sẽ giữ token hết hạn; ký lại mỗi request.
        self._static_service_token = service_token
        self.timeout = timeout

    async def get_deliberation_authority(
        self,
        *,
        workspace_id: str,
        project_id: str,
        deliberation_id: str,
        role_key: str,
        frame_version: int | None = None,
    ) -> dict[str, Any]:
        """GET /internal/operations/projects/:projectId/deliberations/:deliberationId/authority?roleKey=:roleKey"""
        url = (
            f"{self.base_url}/internal/operations/projects/{project_id}/"
            f"deliberations/{deliberation_id}/authority"
        )
        headers = {
            "X-Workspace-Id": workspace_id,
            "X-Service-Token": self.service_token,
            "Authorization": f"Bearer {self.service_token}",
        }
        params: dict[str, Any] = {"roleKey": role_key}
        if frame_version is not None:
            params["frameVersion"] = frame_version
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=headers, params=params)
        except httpx.HTTPError as exc:
            raise ExecutiveBoardClientError(f"Company service unreachable: {exc}") from exc

        if res.status_code != 200:
            raise ExecutiveBoardAuthorityError(
                f"Company service denied authority for deliberation {deliberation_id} role {role_key} "
                f"(status {res.status_code}): {res.text}",
                status_code=res.status_code,
            )

        try:
            return res.json()
        except Exception as exc:
            raise ExecutiveBoardClientError(f"Malformed authority response: {exc}") from exc

    async def submit_analysis_callback(
        self,
        *,
        workspace_id: str,
        project_id: str,
        deliberation_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """POST /internal/operations/projects/:projectId/deliberations/:deliberationId/callback"""
        url = (
            f"{self.base_url}/internal/operations/projects/{project_id}/"
            f"deliberations/{deliberation_id}/callback"
        )
        headers = {
            "X-Workspace-Id": workspace_id,
            "X-Service-Token": self.service_token,
            "Authorization": f"Bearer {self.service_token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise ExecutiveBoardClientError(f"Company service unreachable: {exc}") from exc

        if res.status_code not in (200, 201):
            raise ExecutiveBoardClientError(
                f"Company service rejected analysis callback (status {res.status_code}): {res.text}",
                status_code=res.status_code,
            )

        try:
            return res.json()
        except Exception as exc:
            raise ExecutiveBoardClientError(f"Malformed callback response: {exc}") from exc
