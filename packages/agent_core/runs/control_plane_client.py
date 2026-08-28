import os
from typing import Any

import httpx

from agent_core.runs.leases import LeaseAcquisitionResult, RunLease

__all__ = ["HttpControlPlaneLeaseClient"]


class HttpControlPlaneLeaseClient:
    """HTTP client gọi `services/cosa` control-plane lease endpoint (Wave 7 H.3,
    ADR-CONTROLPLANE-001) — thay thế `RunLeaseManager` in-memory bằng lease
    durable, chống split-brain THẬT giữa nhiều process/replica.
    """

    def __init__(
        self,
        *,
        base_url: str,
        timeout_sec: float = 5.0,
        token: str | None = None,
        service_token: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = service_token or token or os.environ.get("COSA_WORKER_SERVICE_TOKEN")
        self._client = client or httpx.AsyncClient(timeout=timeout_sec)
        self._owns_client = client is None

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def acquire_lease(
        self,
        run_id: str,
        worker_id: str,
        ttl_sec: int | None = None,
    ) -> LeaseAcquisitionResult:
        payload: dict[str, Any] = {"runId": run_id, "workerId": worker_id}
        if ttl_sec is not None:
            payload["ttlSec"] = ttl_sec
        resp = await self._client.post(
            f"{self._base_url}/control-plane/internal/leases/acquire",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            return LeaseAcquisitionResult(
                success=False, reason=data.get("reason", "acquire failed")
            )
        lease = RunLease(
            run_id=run_id,
            worker_id=worker_id,
            lease_token=data["leaseToken"],
            expires_at=data["expiresAt"],
        )
        return LeaseAcquisitionResult(success=True, lease=lease, reason=data.get("reason", ""))

    async def renew_lease(
        self,
        run_id: str,
        worker_id: str,
        lease_token: str,
        additional_ttl_sec: int | None = None,
    ) -> bool:
        payload: dict[str, Any] = {
            "runId": run_id,
            "workerId": worker_id,
            "leaseToken": lease_token,
        }
        if additional_ttl_sec is not None:
            payload["additionalTtlSec"] = additional_ttl_sec
        resp = await self._client.post(
            f"{self._base_url}/control-plane/internal/leases/renew",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return bool(resp.json().get("success"))

    async def release_lease(self, run_id: str, worker_id: str, lease_token: str) -> bool:
        payload = {"runId": run_id, "workerId": worker_id, "leaseToken": lease_token}
        resp = await self._client.post(
            f"{self._base_url}/control-plane/internal/leases/release",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return bool(resp.json().get("success"))
