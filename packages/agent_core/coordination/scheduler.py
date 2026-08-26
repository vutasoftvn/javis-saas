from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
import uuid
from pydantic import BaseModel, Field

__all__ = ["ScheduledTaskRecord", "RunScheduler"]


class ScheduledTaskRecord(BaseModel):
    """Bản ghi tác vụ được lập lịch trong hàng đợi theo P2 Hardening."""

    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    coalescing_key: Optional[str] = None
    target_spec_id: str
    target_spec_kind: str = "agent"  # "agent" or "workflow"
    input_payload: dict[str, Any] = Field(default_factory=dict)
    run_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "scheduled"  # "scheduled", "processing", "completed", "coalesced", "failed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Phase 3 Durable Queue Recovery (docs/implementation/production-runtime-
    # closure.md §7) — chỉ dùng bởi HttpControlPlaneSchedulerClient (durable
    # Postgres); RunScheduler in-memory không set các field này (giữ default).
    claim_token: Optional[str] = None
    attempt_count: int = 0
    max_attempts: int = 5


class RunScheduler:
    """Coalescing Work Queue & Task Scheduler."""

    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTaskRecord] = {}  # task_id -> record
        self._coalescing_index: dict[str, str] = {}  # coalescing_key -> task_id
        self._lock = asyncio.Lock()

    async def schedule(
        self,
        *,
        target_spec_id: str,
        input_payload: dict[str, Any],
        coalescing_key: Optional[str] = None,
        run_at: Optional[datetime] = None,
        target_spec_kind: str = "agent",
    ) -> ScheduledTaskRecord:
        now = datetime.now(timezone.utc)
        target_time = run_at or now

        async with self._lock:
            # Nếu có coalescing_key và đã có task scheduled đang chờ -> Coalesce (gộp dữ liệu)
            if coalescing_key and coalescing_key in self._coalescing_index:
                existing_id = self._coalescing_index[coalescing_key]
                existing_task = self._tasks.get(existing_id)
                if existing_task and existing_task.status == "scheduled":
                    existing_task.input_payload.update(input_payload)
                    return existing_task

            task = ScheduledTaskRecord(
                coalescing_key=coalescing_key,
                target_spec_id=target_spec_id,
                target_spec_kind=target_spec_kind,
                input_payload=input_payload,
                run_at=target_time,
                status="scheduled",
            )
            self._tasks[task.task_id] = task
            if coalescing_key:
                self._coalescing_index[coalescing_key] = task.task_id
            return task

    async def poll_due_tasks(self, worker_id: Optional[str] = None, limit: int = 10) -> list[ScheduledTaskRecord]:
        """`worker_id` optional (default nội bộ, không dùng để fencing — xem
        `complete_task`) để tương thích call site cũ gọi `poll_due_tasks()`
        không tham số trong test — bản durable Postgres
        (`HttpControlPlaneSchedulerClient`) bắt buộc `worker_id` vì cần ghi
        vào `claimed_by` thật cho fencing (Phase 3 Durable Queue Recovery)."""
        now = datetime.now(timezone.utc)
        due = []
        async with self._lock:
            for task in self._tasks.values():
                if task.status == "scheduled" and task.run_at <= now:
                    task.status = "processing"
                    task.claim_token = f"claim_{uuid.uuid4().hex[:12]}"
                    due.append(task)
                    if len(due) >= limit:
                        break
        return due

    async def heartbeat_task(
        self, task_id: str, worker_id: Optional[str] = None, claim_token: Optional[str] = None, extend_sec: Optional[int] = None
    ) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != "processing":
                return False
            if claim_token is not None and task.claim_token != claim_token:
                return False
            return True

    async def complete_task(
        self,
        task_id: str,
        worker_id: Optional[str] = None,
        claim_token: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> bool:
        """Fencing bằng `claim_token` (khớp với `HttpControlPlaneSchedulerClient`
        thật) — `worker_id` nhận nhưng KHÔNG dùng để fencing ở bản in-memory
        này (chỉ 1 process, không có khái niệm "worker khác" thật; test
        cross-process crash recovery thật phải dùng bản Postgres, xem
        CLAUDE.md #6)."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if claim_token is not None and task.claim_token != claim_token:
                return False

            task.status = "completed" if success else "failed"
            if task.coalescing_key and task.coalescing_key in self._coalescing_index:
                if self._coalescing_index[task.coalescing_key] == task_id:
                    del self._coalescing_index[task.coalescing_key]
            return True
