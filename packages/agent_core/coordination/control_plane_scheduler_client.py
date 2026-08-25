from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from agent_core.coordination.scheduler import ScheduledTaskRecord

__all__ = ["HttpControlPlaneSchedulerClient", "sweep_stuck_tasks"]


class HttpControlPlaneSchedulerClient:
    """HTTP client gọi `services/cosa` control-plane scheduled-tasks endpoint
    (Wave 7 H.3, ADR-CONTROLPLANE-001) — thay thế `RunScheduler` in-memory
    bằng hàng đợi durable, chống mất task khi HTTP process chết giữa chừng.

    Giữ nguyên interface `schedule`/`poll_due_tasks`/`complete_task` của
    `RunScheduler` để call site khác không cần đổi khi cutover.

    CHƯA runtime-verify bằng Encore CLI/Postgres thật (không có trong môi
    trường phiên viết code này) — xem
    COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §29.6 Phase 4.
    """

    def __init__(self, *, base_url: str, timeout_sec: float = 5.0, client: Optional[httpx.AsyncClient] = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout_sec)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def schedule(
        self,
        *,
        target_spec_id: str,
        input_payload: dict[str, Any],
        coalescing_key: Optional[str] = None,
        run_at: Optional[datetime] = None,
        target_spec_kind: str = "agent",
    ) -> ScheduledTaskRecord:
        payload: dict[str, Any] = {
            "targetSpecId": target_spec_id,
            "inputPayload": input_payload,
            "targetSpecKind": target_spec_kind,
        }
        if coalescing_key is not None:
            payload["coalescingKey"] = coalescing_key
        if run_at is not None:
            payload["runAt"] = run_at.isoformat()

        resp = await self._client.post(f"{self._base_url}/control-plane/internal/scheduled-tasks", json=payload)
        resp.raise_for_status()
        return self._row_to_record(resp.json())

    async def poll_due_tasks(self, limit: int = 10) -> list[ScheduledTaskRecord]:
        resp = await self._client.get(
            f"{self._base_url}/control-plane/internal/scheduled-tasks/due", params={"limit": limit}
        )
        resp.raise_for_status()
        return [self._row_to_record(row) for row in resp.json().get("tasks", [])]

    async def complete_task(self, task_id: str, success: bool = True) -> None:
        resp = await self._client.post(
            f"{self._base_url}/control-plane/internal/scheduled-tasks/{task_id}/complete",
            json={"success": success},
        )
        resp.raise_for_status()

    @staticmethod
    def _row_to_record(row: dict[str, Any]) -> ScheduledTaskRecord:
        return ScheduledTaskRecord(
            task_id=row["id"],
            coalescing_key=row.get("coalescingKey"),
            target_spec_id=row["targetSpecId"],
            target_spec_kind=row.get("targetSpecKind", "agent"),
            input_payload=row.get("inputPayload") or {},
            run_at=row["runAt"],
            status=row.get("status", "scheduled"),
            created_at=row.get("createdAt", row["runAt"]),
        )


async def sweep_stuck_tasks(dsn: str, stale_after_seconds: int = 300) -> int:
    """Tìm task bị stuck (status='processing') với lease đã hết hạn, reset về 'scheduled'.

    Được gọi định kỳ từ background job/cron để tự phục hồi từ crash không graceful.

    Args:
        dsn: Postgres connection string trỏ tới control_plane database.
            Có thể dùng "postgresql://" hoặc "postgresql+asyncpg://" format.
        stale_after_seconds: Task coi là "bị stuck" nếu lease hết hạn quá
            stale_after_seconds giây trước (default 5 phút — tránh race condition
            với lease heartbeat)

    Returns:
        Số task đã được reset về 'scheduled'
    """
    # Normalize DSN to async format if needed
    async_dsn = dsn
    if "postgresql+asyncpg://" not in async_dsn:
        async_dsn = async_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
        async_dsn = async_dsn.replace("postgres://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(async_dsn)

    try:
        async with engine.begin() as conn:
            now = datetime.now(timezone.utc)

            # Find all expired leases (expires_at > stale_after_seconds ago)
            result = await conn.execute(
                text("""
                    SELECT DISTINCT l.run_id
                    FROM control_plane.runtime_leases l
                    WHERE l.expires_at < :stale_threshold
                """),
                {"stale_threshold": now},
            )

            expired_run_ids = [row[0] for row in result.fetchall()]

            if not expired_run_ids:
                return 0

            # For each expired lease, find & reset processing tasks with matching run_id
            # Task payload contains {"run_id": "...", ...}, so we need to check JSONB
            count = await conn.execute(
                text("""
                    UPDATE control_plane.scheduled_tasks
                    SET status = 'scheduled'
                    WHERE status = 'processing'
                        AND (input_payload->>'run_id') = ANY(:run_ids)
                """),
                {"run_ids": expired_run_ids},
            )

            return count.rowcount or 0

    finally:
        await engine.dispose()
