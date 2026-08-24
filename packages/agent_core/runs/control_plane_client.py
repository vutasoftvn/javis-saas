from __future__ import annotations

from typing import Any, Optional

import httpx

from agent_core.runs.leases import LeaseAcquisitionResult, RunLease

__all__ = ["HttpControlPlaneLeaseClient"]


class HttpControlPlaneLeaseClient:
    """HTTP client gọi `services/cosa` control-plane lease endpoint (Wave 7 H.3,
    ADR-CONTROLPLANE-001) — thay thế `RunLeaseManager` in-memory bằng lease
    durable, chống split-brain THẬT giữa nhiều process/replica.

    Giữ nguyên interface `acquire_lease`/`renew_lease`/`release_lease` của
    `RunLeaseManager` để call site khác trong `agent_core` không cần đổi khi
    cutover — chỉ đổi implementation bên trong (đúng nguyên tắc Phần H.3 của
    COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md).

    CHƯA wire làm default ở bất kỳ đâu — `RunLeaseManager` (in-memory) hiện tại
    KHÔNG có consumer production nào (chỉ có test riêng gọi trực tiếp), nên
    chưa có "cutover" thật để làm; class này tồn tại sẵn cho khi có consumer
    thật, tránh phải thiết kế lại giao diện lúc đó. CHƯA verify bằng
    services/cosa thật đang chạy (không có Encore CLI/Postgres trong môi
    trường phát triển này — xem ghi chú Wave 7 trong plan doc).
    """

    def __init__(self, *, base_url: str, timeout_sec: float = 5.0, client: Optional[httpx.AsyncClient] = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout_sec)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def acquire_lease(
        self,
        run_id: str,
        worker_id: str,
        ttl_sec: Optional[int] = None,
    ) -> LeaseAcquisitionResult:
        payload: dict[str, Any] = {"runId": run_id, "workerId": worker_id}
        if ttl_sec is not None:
            payload["ttlSec"] = ttl_sec
        resp = await self._client.post(f"{self._base_url}/control-plane/internal/leases/acquire", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            return LeaseAcquisitionResult(success=False, reason=data.get("reason", "acquire failed"))
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
        additional_ttl_sec: Optional[int] = None,
    ) -> bool:
        payload: dict[str, Any] = {"runId": run_id, "workerId": worker_id, "leaseToken": lease_token}
        if additional_ttl_sec is not None:
            payload["additionalTtlSec"] = additional_ttl_sec
        resp = await self._client.post(f"{self._base_url}/control-plane/internal/leases/renew", json=payload)
        resp.raise_for_status()
        return bool(resp.json().get("success"))

    async def release_lease(self, run_id: str, worker_id: str, lease_token: str) -> bool:
        payload = {"runId": run_id, "workerId": worker_id, "leaseToken": lease_token}
        resp = await self._client.post(f"{self._base_url}/control-plane/internal/leases/release", json=payload)
        resp.raise_for_status()
        return bool(resp.json().get("success"))
