from __future__ import annotations

import os
from typing import Any

import httpx

__all__ = ["CompanyServiceClient", "CompanyServiceError"]


class CompanyServiceError(Exception):
    def __init__(self, message: str, status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class CompanyServiceClient:
    """Async HTTP Client kết nối tới Encore Business Services (services/company).

    Phục vụ các Capability của COSA:
    - Operations (/operations/...)
    - Commercial (/commercial/...)
    - Finance & Legal (/finance-legal/...)
    - Identity (/identity/...)
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 15.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("COMPANY_SERVICE_URL") or "http://localhost:4000"
        ).rstrip("/")
        self.timeout = timeout
        self.default_headers = headers or {}

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("POST", path, json=json, params=params, headers=headers)

    async def patch(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("PATCH", path, json=json, params=params, headers=headers)

    async def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("PUT", path, json=json, params=params, headers=headers)

    async def delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("DELETE", path, params=params, headers=headers)

    async def list_tasks(self, workspace_id: str) -> dict[str, Any]:
        return await self.get("/operations/tasks", params={"workspaceId": workspace_id})

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        from agent.capabilities.outbound_headers import get_outbound_headers

        from apps.cosa.observability.otel import inject_trace_carrier

        url = f"{self.base_url}/{path.lstrip('/')}"
        req_headers = dict(self.default_headers)
        # Task 5 — header xác thực (Authorization, X-Workspace-Id,
        # X-COSA-Run-Id, X-COSA-Capability-Id) do kernel set ambient TỪ
        # InvocationContext của tool call đang chạy (KHÔNG phải từ đối số của
        # handler/tool). Merge SAU default_headers nhưng TRƯỚC `headers`
        # tường minh (nếu caller truyền `headers=` rõ ràng cho nhu cầu khác,
        # nó vẫn thắng — không có call site nào hiện tại truyền Authorization
        # tường minh qua tham số này).
        req_headers.update(get_outbound_headers())
        if headers:
            req_headers.update(headers)
        req_headers = inject_trace_carrier(req_headers)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method, url, params=params, json=json, headers=req_headers
                )
                if response.status_code >= 400:
                    try:
                        err_payload = response.json()
                        message = err_payload.get("message", response.text)
                    except Exception:
                        message = response.text
                    raise CompanyServiceError(
                        f"Company Service Error ({response.status_code}): {message}",
                        status_code=response.status_code,
                        details=response.text,
                    )
                return response.json()
            except httpx.RequestError as exc:
                raise CompanyServiceError(
                    f"Network error communicating with Company Service at {url}: {exc}"
                ) from exc
