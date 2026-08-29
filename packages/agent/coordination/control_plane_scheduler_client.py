from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx

from agent.coordination.scheduler import ScheduledTaskRecord

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

    async def schedule(
        self,
        *,
        target_spec_id: str,
        input_payload: dict[str, Any],
        coalescing_key: str | None = None,
        run_at: datetime | None = None,
        target_spec_kind: str = "agent",
        max_attempts: int | None = None,
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

        resp = await self._client.post(
            f"{self._base_url}/control-plane/internal/scheduled-tasks",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return self._row_to_record(resp.json())

    async def poll_due_tasks(
        self, *, worker_id: str, limit: int = 10, visibility_timeout_sec: int | None = None
    ) -> list[ScheduledTaskRecord]:
        payload: dict[str, Any] = {"workerId": worker_id, "limit": limit}
        if visibility_timeout_sec is not None:
            payload["visibilityTimeoutSec"] = visibility_timeout_sec

        resp = await self._client.post(
            f"{self._base_url}/control-plane/internal/scheduled-tasks/poll",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return [self._row_to_record(row) for row in resp.json().get("tasks", [])]

    async def heartbeat_task(
        self, task_id: str, *, worker_id: str, claim_token: str, extend_sec: int | None = None
    ) -> bool:
        payload: dict[str, Any] = {
            "taskId": task_id,
            "workerId": worker_id,
            "claimToken": claim_token,
        }
        if extend_sec is not None:
            payload["extendSec"] = extend_sec

        resp = await self._client.post(
            f"{self._base_url}/control-plane/internal/scheduled-tasks/{task_id}/heartbeat",
            json=payload,
            headers=self._headers(),
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
        error: str | None = None,
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
            f"{self._base_url}/control-plane/internal/scheduled-tasks/{task_id}/complete",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return bool(resp.json().get("ok", False))

    # --- Durable hierarchical supervisor child tasks (P1 Task 7) ---
    # Khớp ChildSchedulerProtocol của agent.coordination.durable_supervisor.

    async def schedule_child_task(
        self,
        *,
        parent_task_id: str,
        child_id: str,
        depends_on: list[str],
        join_policy: str,
        join_quorum: int | None,
        blocked: bool,  # server tự tính từ depends_on — tham số này bị bỏ qua
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> str:
        target_spec_id = (
            (payload.get("agent_spec") or {}).get("id") or payload.get("target_spec_id") or "agent"
        )
        resp = await self._client.post(
            f"{self._base_url}/control-plane/internal/child-tasks",
            json={
                "parentTaskId": parent_task_id,
                "childId": child_id,
                "targetSpecId": target_spec_id,
                "inputPayload": payload,
                "dependsOn": depends_on,
                "joinPolicy": join_policy,
                "joinQuorum": join_quorum,
            },
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()["scheduledTaskId"]

    async def list_children(self, parent_task_id: str) -> list[dict[str, Any]]:
        resp = await self._client.get(
            f"{self._base_url}/control-plane/internal/child-tasks/{parent_task_id}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        out: list[dict[str, Any]] = []
        for c in resp.json().get("children", []):
            out.append(
                {
                    "child_id": c["childId"],
                    "status": c["status"],
                    "scheduled_task_id": c["scheduledTaskId"],
                    "depends_on": c.get("dependsOn") or [],
                    "join_policy": c.get("joinPolicy"),
                    "join_quorum": c.get("joinQuorum"),
                    "result": c.get("result"),
                    "idempotency_key": c.get("completionKey"),
                }
            )
        return out

    async def complete_child(
        self, *, parent_task_id: str, child_id: str, result: dict[str, Any], idempotency_key: str
    ) -> bool:
        resp = await self._client.post(
            f"{self._base_url}/control-plane/internal/child-tasks/complete",
            json={
                "parentTaskId": parent_task_id,
                "childId": child_id,
                "result": result,
                "idempotencyKey": idempotency_key,
            },
            headers=self._headers(),
        )
        resp.raise_for_status()
        body = resp.json()
        return bool(body.get("ok")) and not body.get("deduped", False)

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
