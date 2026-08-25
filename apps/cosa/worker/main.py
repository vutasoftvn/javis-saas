"""COSA Agent Worker — entrypoint riêng ngoài HTTP process, poll scheduled
task durable (`plane.scheduler`) thay cho `asyncio.create_task` sống trong
`apps/cosa/api/routes.py` (Master Guide §5, COSA_FINAL_INTEGRATION_AND_
LEGACY_EXIT_PLAN_2026-08-25.md §29.6 Phase 4).

Chạy: python -m apps.cosa.worker.main
Nhiều instance chạy song song AN TOÀN — atomic claim ở tầng scheduler
(`FOR UPDATE SKIP LOCKED` phía services/cosa) + lease durable
(`plane.lease_client`) chống 2 worker cùng thực thi 1 run_id.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import uuid
from typing import Optional

from apps.cosa.api.event_stream import get_cosa_event_stream_manager
from apps.cosa.composition.agent_plane import CosaAgentPlane, build_cosa_agent_plane
from apps.cosa.worker.handlers import execute_resume_task, execute_run_task

__all__ = ["run_worker_loop", "dispatch_one_task", "WORKER_ID"]

logger = logging.getLogger("cosa.worker")

WORKER_ID = os.environ.get("COSA_WORKER_ID") or f"worker_{uuid.uuid4().hex[:8]}"
POLL_INTERVAL_SEC = float(os.environ.get("COSA_WORKER_POLL_INTERVAL_SEC", "1.0"))
LEASE_TTL_SEC = int(os.environ.get("COSA_WORKER_LEASE_TTL_SEC", "60"))
LEASE_HEARTBEAT_SEC = int(os.environ.get("COSA_WORKER_LEASE_HEARTBEAT_SEC", "20"))


async def _run_with_lease_heartbeat(plane: CosaAgentPlane, run_id: str, lease_token: str, coro) -> None:
    """Chạy `coro` (execute_run_task/execute_resume_task) đồng thời renew
    lease định kỳ trong lúc thực thi — đúng flow §5.2 tài liệu gốc: "execute
    kernel ... renew lease heartbeat ... release lease". Renew thất bại liên
    tục (lease bị reclaim) chỉ log cảnh báo, không huỷ execution đang chạy dở
    giữa chừng — tránh corrupt state; lần chạy sau tự phát hiện conflict qua
    exact invocation identity/idempotency claim đã có sẵn ở Capability Gateway.
    """

    async def heartbeat() -> None:
        while True:
            await asyncio.sleep(LEASE_HEARTBEAT_SEC)
            renewed = await plane.lease_client.renew_lease(run_id, WORKER_ID, lease_token)
            if not renewed:
                logger.warning(
                    "worker=%s failed to renew lease for run_id=%s (may have been reclaimed)",
                    WORKER_ID,
                    run_id,
                )

    hb_task = asyncio.create_task(heartbeat())
    try:
        await coro
    finally:
        hb_task.cancel()
        try:
            await hb_task
        except asyncio.CancelledError:
            pass


async def dispatch_one_task(plane: CosaAgentPlane, task) -> None:
    """Xử lý 1 `ScheduledTaskRecord` đã được `poll_due_tasks()` claim (atomic,
    status='processing') — acquire lease cho run_id, dispatch theo
    `task_type`, release lease, đánh dấu task complete/failed."""
    stream_mgr = get_cosa_event_stream_manager()
    payload = task.input_payload
    run_id = payload.get("run_id")
    task_type = payload.get("task_type")

    if not run_id:
        logger.error("task=%s missing run_id in payload, marking failed", task.task_id)
        await plane.scheduler.complete_task(task.task_id, success=False)
        return

    lease_result = await plane.lease_client.acquire_lease(run_id, WORKER_ID, ttl_sec=LEASE_TTL_SEC)
    if not lease_result.success:
        # Worker khác đang giữ lease hợp lệ cho run_id này — KHÔNG complete_task
        # (task coi như đang được xử lý bởi worker đó). Nếu lease hết hạn mà
        # không ai hoàn tất task, đây là gap đã biết (chưa có stuck-task
        # sweeper định kỳ) — ghi rõ trong
        # COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §29.6 Phase 4.
        logger.info(
            "worker=%s could not acquire lease for run_id=%s: %s — leaving task for original lease holder",
            WORKER_ID,
            run_id,
            lease_result.reason,
        )
        return

    assert lease_result.lease is not None
    try:
        if task_type == "run":
            coro = execute_run_task(plane, stream_mgr, payload)
        elif task_type == "resume":
            coro = execute_resume_task(plane, stream_mgr, payload)
        else:
            logger.error("task=%s unknown task_type=%r", task.task_id, task_type)
            await plane.scheduler.complete_task(task.task_id, success=False)
            return

        await _run_with_lease_heartbeat(plane, run_id, lease_result.lease.lease_token, coro)
        await plane.scheduler.complete_task(task.task_id, success=True)
    except Exception:
        logger.exception("task=%s run_id=%s failed during execution", task.task_id, run_id)
        await plane.scheduler.complete_task(task.task_id, success=False)
    finally:
        await plane.lease_client.release_lease(run_id, WORKER_ID, lease_result.lease.lease_token)


async def run_worker_loop(
    plane: CosaAgentPlane,
    *,
    poll_limit: int = 10,
    max_iterations: Optional[int] = None,
) -> None:
    """Vòng lặp chính: poll → claim (atomic ở tầng scheduler) → lease →
    execute → release → complete. `max_iterations` chỉ dùng cho test (chạy
    hữu hạn vòng thay vì `while True` mãi mãi trong production)."""
    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        tasks = await plane.scheduler.poll_due_tasks(limit=poll_limit)
        if tasks:
            await asyncio.gather(*(dispatch_one_task(plane, t) for t in tasks))
        else:
            await asyncio.sleep(POLL_INTERVAL_SEC)
        iterations += 1


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="COSA Agent Worker")
    parser.add_argument("--once", action="store_true", help="Run one dispatch cycle and exit (for testing)")
    args = parser.parse_args()

    plane = build_cosa_agent_plane()
    logger.info("COSA worker %s starting, polling every %.1fs", WORKER_ID, POLL_INTERVAL_SEC)

    if args.once:
        # Single dispatch cycle for testing
        await run_worker_loop(plane, max_iterations=1)
    else:
        # Infinite polling loop (production)
        await run_worker_loop(plane)


if __name__ == "__main__":
    asyncio.run(main())
