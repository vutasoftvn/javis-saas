from __future__ import annotations

import os
from typing import Any, Optional
import httpx


class EncoreClientError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class EncoreClient:
    """Async HTTP Client for invoking Encore TypeScript Business Services Clusters:
    - identity (/identity/...)
    - operations (/operations/...)
    - commercial (/commercial/...)
    - finance-legal (/finance-legal/...)
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 15.0) -> None:
        self.base_url = (base_url or os.getenv("ENCORE_SERVICE_URL", "http://localhost:4000")).rstrip("/")
        self.timeout = timeout

    async def get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Optional[dict[str, Any]] = None, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return await self._request("POST", path, json=json, params=params)

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, params=params, json=json)
                if response.status_code >= 400:
                    try:
                        err_payload = response.json()
                        message = err_payload.get("message", response.text)
                    except Exception:
                        message = response.text
                    raise EncoreClientError(
                        f"Encore API Error ({response.status_code}): {message}",
                        status_code=response.status_code,
                        details=response.text,
                    )
                return response.json()
            except httpx.RequestError as exc:
                raise EncoreClientError(f"Network error communicating with Encore service at {url}: {exc}") from exc
