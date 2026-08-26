from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from agent_core.coordination.scheduler import ScheduledTaskRecord

__all__ = ["HttpControlPlaneSchedulerClient"]


class HttpControlPlaneSchedulerClient:
    """HTTP client gọi `services/cosa` control-plane scheduled-tasks endpoint
    (Wave 7 H.3, ADR-CONTROLPLANE-001) — thay thế `RunScheduler` in-memory
    bằng hàng đợi durable, chống mất task khi HTTP process chết giữa chừng.

    Phase 3 Durable Queue Recovery (docs/implementation/production-runtime-
    closure.md §7) — `poll_due_tasks()` giờ claim bằng fencing token
    (`claim_token`), `complete_task()`/`heartbeat_task()` phải truyền lại
    đúng `worker_id`+`claim_token` để server chấp nhận (worker cũ đã bị
    sweeper reclaim sẽ bị từ chối, tránh ghi đè kết quả của lần claim mới).

    Giữ nguyên interface `schedule`/`complete_task` của `RunScheduler` gốc
    (đổi chữ ký `poll_due_tasks`/`complete_task` cho claim/fencing — call
    site duy nhất là `apps/cosa/worker/main.py`, đã cập nhật theo).
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
        max_attempts: Optional[int] = None,
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
        if max_attempts is not None:
            payload["maxAttempts"] = max_attempts

        resp = await self._client.post(f"{self._base_url}/control-plane/internal/scheduled-tasks", json=payload)
        resp.raise_for_status()
        return self._row_to_record(resp.json())

    async def poll_due_tasks(
        self, *, worker_id: str, limit: int = 10, visibility_timeout_sec: Optional[int] = None
    ) -> list[ScheduledTaskRecord]:
        payload: dict[str, Any] = {"workerId": worker_id, "limit": limit}
        if visibility_timeout_sec is not None:
            payload["visibilityTimeoutSec"] = visibility_timeout_sec

        resp = await self._client.post(f"{self._base_url}/control-plane/internal/scheduled-tasks/poll", json=payload)
        resp.raise_for_status()
        return [self._row_to_record(row) for row in resp.json().get("tasks", [])]

    async def heartbeat_task(
        self, task_id: str, *, worker_id: str, claim_token: str, extend_sec: Optional[int] = None
    ) -> bool:
        payload: dict[str, Any] = {"taskId": task_id, "workerId": worker_id, "claimToken": claim_token}
        if extend_sec is not None:
            payload["extendSec"] = extend_sec

        resp = await self._client.post(
            f"{self._base_url}/control-plane/internal/scheduled-tasks/{task_id}/heartbeat", json=payload
        )
        resp.raise_for_status()
        return bool(resp.json().get("ok", False))

    async def complete_task(
        self,
        task_id: str,
        *,
        worker_id: str,
        claim_token: str,
        success: bool = True,
        error: Optional[str] = None,
    ) -> bool:
        """Trả về False nếu fencing từ chối (task đã bị reclaim bởi sweeper
        hoặc claim_token không khớp) — caller KHÔNG được coi execution vừa
        chạy là "task đã ghi nhận xong", vì 1 worker khác đang xử lý lại task
        này (crash test #6: stale worker cố completeTask)."""
        payload: dict[str, Any] = {
            "taskId": task_id,
            "workerId": worker_id,
            "claimToken": claim_token,
            "success": success,
        }
        if error is not None:
            payload["error"] = error

        resp = await self._client.post(
            f"{self._base_url}/control-plane/internal/scheduled-tasks/{task_id}/complete", json=payload
        )
        resp.raise_for_status()
        return bool(resp.json().get("ok", False))

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
            claim_token=row.get("claimToken"),
            attempt_count=row.get("attemptCount", 0),
            max_attempts=row.get("maxAttempts", 5),
        )
