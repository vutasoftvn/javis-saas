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

    async def poll_due_tasks(self, limit: int = 10) -> list[ScheduledTaskRecord]:
        now = datetime.now(timezone.utc)
        due = []
        async with self._lock:
            for task in self._tasks.values():
                if task.status == "scheduled" and task.run_at <= now:
                    task.status = "processing"
                    due.append(task)
                    if len(due) >= limit:
                        break
        return due

    async def complete_task(self, task_id: str, success: bool = True) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "completed" if success else "failed"
                if task.coalescing_key and task.coalescing_key in self._coalescing_index:
                    if self._coalescing_index[task.coalescing_key] == task_id:
                        del self._coalescing_index[task.coalescing_key]
