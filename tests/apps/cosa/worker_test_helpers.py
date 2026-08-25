from __future__ import annotations

from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.worker.main import dispatch_one_task

__all__ = ["drain_worker_queue"]


async def drain_worker_queue(plane: CosaAgentPlane, *, limit: int = 10) -> int:
    """Poll + dispatch toàn bộ scheduled task đang due 1 lần — mô phỏng
    `apps/cosa/worker/main.py::run_worker_loop` cho test HTTP integration mà
    không cần chạy `while True` thật. Trả số task đã dispatch."""
    tasks = await plane.scheduler.poll_due_tasks(limit=limit)
    for task in tasks:
        await dispatch_one_task(plane, task)
    return len(tasks)
