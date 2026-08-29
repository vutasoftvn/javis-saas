from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

__all__ = ["LeaseAcquisitionResult", "RunLease", "RunLeaseManager"]


class RunLease(BaseModel):
    """Khóa giữ quyền thực thi (Execution Lease) phân tán cho một Run theo P2 Hardening."""

    run_id: str
    worker_id: str
    lease_token: str = Field(default_factory=lambda: f"lease_{uuid.uuid4().hex[:12]}")
    acquired_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime
    heartbeat_interval_sec: int = 30


class LeaseAcquisitionResult(BaseModel):
    success: bool
    lease: RunLease | None = None
    reason: str


class RunLeaseManager:
    """Quản lý khóa thực thi phân tán chống split-brain giữa nhiều worker."""

    def __init__(self, default_lease_ttl_sec: int = 60) -> None:
        self._default_ttl = default_lease_ttl_sec
        self._leases: dict[str, RunLease] = {}  # run_id -> RunLease
        self._lock = asyncio.Lock()

    async def acquire_lease(
        self,
        run_id: str,
        worker_id: str,
        ttl_sec: int | None = None,
    ) -> LeaseAcquisitionResult:
        now = datetime.now(UTC)
        duration = ttl_sec or self._default_ttl

        async with self._lock:
            existing = self._leases.get(run_id)
            if existing and now < existing.expires_at and existing.worker_id != worker_id:
                return LeaseAcquisitionResult(
                    success=False,
                    reason=f"Run '{run_id}' is currently leased by worker '{existing.worker_id}' until {existing.expires_at.isoformat()}",
                )

            # Cấp phát lease mới
            lease = RunLease(
                run_id=run_id,
                worker_id=worker_id,
                expires_at=now + timedelta(seconds=duration),
            )
            self._leases[run_id] = lease
            return LeaseAcquisitionResult(
                success=True,
                lease=lease,
                reason="Lease successfully acquired",
            )

    async def renew_lease(
        self,
        run_id: str,
        worker_id: str,
        lease_token: str,
        additional_ttl_sec: int | None = None,
    ) -> bool:
        now = datetime.now(UTC)
        duration = additional_ttl_sec or self._default_ttl

        async with self._lock:
            existing = self._leases.get(run_id)
            if (
                not existing
                or existing.worker_id != worker_id
                or existing.lease_token != lease_token
            ):
                return False
            existing.expires_at = now + timedelta(seconds=duration)
            return True

    async def release_lease(self, run_id: str, worker_id: str, lease_token: str) -> bool:
        async with self._lock:
            existing = self._leases.get(run_id)
            if (
                not existing
                or existing.worker_id != worker_id
                or existing.lease_token != lease_token
            ):
                return False
            del self._leases[run_id]
            return True
