from __future__ import annotations

import os
from typing import Any, Optional
import httpx

__all__ = ["CompanyServiceClient", "CompanyServiceError"]


class CompanyServiceError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None) -> None:
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
        base_url: Optional[str] = None,
        timeout: float = 15.0,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("COMPANY_SERVICE_URL", "http://localhost:4000")).rstrip("/")
        self.timeout = timeout
        self.default_headers = headers or {}

    async def get(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        return await self._request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        return await self._request("POST", path, json=json, params=params, headers=headers)

    async def patch(
        self,
        path: str,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        return await self._request("PATCH", path, json=json, params=params, headers=headers)

    async def put(
        self,
        path: str,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        return await self._request("PUT", path, json=json, params=params, headers=headers)

    async def delete(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        return await self._request("DELETE", path, params=params, headers=headers)

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        req_headers = dict(self.default_headers)
        if headers:
            req_headers.update(headers)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, params=params, json=json, headers=req_headers)
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
                raise CompanyServiceError(f"Network error communicating with Company Service at {url}: {exc}") from exc
