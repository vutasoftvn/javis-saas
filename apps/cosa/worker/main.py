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

from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.event_stream import get_cosa_event_stream_manager
from apps.cosa.composition.agent_plane import CosaAgentPlane, build_cosa_agent_plane
from apps.cosa.worker.handlers import (
    execute_resume_task,
    execute_run_task,
    execute_scheduled_session_task,
)


__all__ = ["run_worker_loop", "dispatch_one_task", "WORKER_ID"]

logger = logging.getLogger("cosa.worker")

WORKER_ID = os.environ.get("COSA_WORKER_ID") or f"worker_{uuid.uuid4().hex[:8]}"
POLL_INTERVAL_SEC = float(os.environ.get("COSA_WORKER_POLL_INTERVAL_SEC", "1.0"))
LEASE_TTL_SEC = int(os.environ.get("COSA_WORKER_LEASE_TTL_SEC", "60"))
LEASE_HEARTBEAT_SEC = int(os.environ.get("COSA_WORKER_LEASE_HEARTBEAT_SEC", "20"))
# Phase 3 Durable Queue Recovery — heartbeat riêng cho claim scheduled_tasks
# (khác lease run-level ở trên): giữ visibility_timeout_at không hết hạn
# trong lúc worker vẫn đang xử lý, để sweeper không reclaim nhầm task đang
# chạy bình thường (chỉ reclaim khi worker THẬT SỰ chết/treo, không heartbeat kịp).
TASK_CLAIM_HEARTBEAT_SEC = int(os.environ.get("COSA_WORKER_TASK_CLAIM_HEARTBEAT_SEC", "40"))


async def _run_with_heartbeats(
    plane: CosaAgentPlane, run_id: str, lease_token: str, task_id: str, claim_token: str, coro
) -> None:
    """Chạy `coro` (execute_run_task/execute_resume_task) đồng thời renew
    lease run-level định kỳ VÀ heartbeat claim task-level trong lúc thực thi —
    đúng flow §5.2 tài liệu gốc: "execute kernel ... renew lease heartbeat ...
    release lease". Renew/heartbeat thất bại liên tục (bị reclaim) chỉ log
    cảnh báo, không huỷ execution đang chạy dở giữa chừng — tránh corrupt
    state; lần chạy sau tự phát hiện conflict qua exact invocation
    identity/idempotency claim đã có sẵn ở Capability Gateway (run-level) và
    fencing token (task-level, complete_task() sẽ bị từ chối nếu đã bị reclaim).
    """

    async def heartbeat_lease() -> None:
        while True:
            await asyncio.sleep(LEASE_HEARTBEAT_SEC)
            renewed = await plane.lease_client.renew_lease(run_id, WORKER_ID, lease_token)
            if not renewed:
                logger.warning(
                    "worker=%s failed to renew lease for run_id=%s (may have been reclaimed)",
                    WORKER_ID,
                    run_id,
                )

    async def heartbeat_task_claim() -> None:
        while True:
            await asyncio.sleep(TASK_CLAIM_HEARTBEAT_SEC)
            renewed = await plane.scheduler.heartbeat_task(task_id, worker_id=WORKER_ID, claim_token=claim_token)
            if not renewed:
                logger.warning(
                    "worker=%s failed to heartbeat task claim for task_id=%s (may have been reclaimed by sweeper)",
                    WORKER_ID,
                    task_id,
                )

    hb_tasks = [asyncio.create_task(heartbeat_lease()), asyncio.create_task(heartbeat_task_claim())]
    try:
        await coro
    finally:
        for t in hb_tasks:
            t.cancel()
        for t in hb_tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass


async def dispatch_one_task(plane: CosaAgentPlane, task) -> None:
    """Xử lý 1 `ScheduledTaskRecord` đã được `poll_due_tasks()` claim (atomic,
    status='processing', kèm `claim_token` fencing) — acquire lease cho
    run_id, dispatch theo `task_type`, release lease, đánh dấu task
    complete/failed. `complete_task()` có thể bị fencing từ chối (`ok=False`)
    nếu sweeper đã reclaim task này (worker treo quá lâu) — khi đó KHÔNG log
    lỗi, vì một worker khác (hoặc lần retry sau) đang/sẽ xử lý lại task."""
    stream_mgr = get_cosa_event_stream_manager()
    payload = task.input_payload
    task_type = payload.get("task_type")
    run_id = payload.get("run_id")
    if not run_id and task_type == "scheduled_session":
        run_id = f"run_sched_{payload.get('schedule_execution_id', task.task_id)}"
    claim_token = task.claim_token

    if not run_id:
        logger.error("task=%s missing run_id in payload, marking failed", task.task_id)
        await plane.scheduler.complete_task(
            task.task_id, worker_id=WORKER_ID, claim_token=claim_token, success=False, error="missing run_id in payload"
        )
        return

    lease_result = await plane.lease_client.acquire_lease(run_id, WORKER_ID, ttl_sec=LEASE_TTL_SEC)
    if not lease_result.success:
        # Worker khác đang giữ lease hợp lệ cho run_id này — KHÔNG complete_task
        # (task coi như đang được xử lý bởi worker đó); claim của TASK này vẫn
        # còn hiệu lực, sweeper sẽ reclaim nếu không ai heartbeat kịp.
        logger.info(
            "worker=%s could not acquire lease for run_id=%s: %s — leaving task for original lease holder",
            WORKER_ID,
            run_id,
            lease_result.reason,
        )
        return

    assert lease_result.lease is not None
    try:
        delay = payload.get("delay_sec")
        if task_type == "run":
            async def _with_optional_delay():
                if delay:
                    await asyncio.sleep(float(delay))
                await execute_run_task(plane, stream_mgr, payload)

            coro = _with_optional_delay()
        elif task_type == "resume":
            async def _with_optional_delay():
                if delay:
                    await asyncio.sleep(float(delay))
                await execute_resume_task(plane, stream_mgr, payload)

            coro = _with_optional_delay()
        elif task_type == "scheduled_session":
            async def _with_optional_delay():
                if delay:
                    await asyncio.sleep(float(delay))
                await execute_scheduled_session_task(plane, stream_mgr, payload, run_id=run_id)

            coro = _with_optional_delay()
        else:
            logger.error("task=%s unknown task_type=%r", task.task_id, task_type)
            await plane.scheduler.complete_task(
                task.task_id, worker_id=WORKER_ID, claim_token=claim_token, success=False, error=f"unknown task_type={task_type!r}"
            )
            return


        await _run_with_heartbeats(plane, run_id, lease_result.lease.lease_token, task.task_id, claim_token, coro)
        ok = await plane.scheduler.complete_task(task.task_id, worker_id=WORKER_ID, claim_token=claim_token, success=True)
        if not ok:
            logger.warning(
                "worker=%s task=%s run_id=%s completed but fencing rejected — task was reclaimed by sweeper mid-execution",
                WORKER_ID,
                task.task_id,
                run_id,
            )
    except Exception as exc:
        logger.exception("task=%s run_id=%s failed during execution", task.task_id, run_id)
        await plane.scheduler.complete_task(
            task.task_id, worker_id=WORKER_ID, claim_token=claim_token, success=False, error=str(exc)
        )
    finally:
        await plane.lease_client.release_lease(run_id, WORKER_ID, lease_result.lease.lease_token)


async def run_worker_loop(
    plane: CosaAgentPlane,
    *,
    poll_limit: int = 10,
    max_iterations: Optional[int] = None,
    target_task_id: Optional[str] = None,
) -> None:
    """Vòng lặp chính: poll → claim (atomic ở tầng scheduler) → lease →
    execute → release → complete. `max_iterations` chỉ dùng cho test (chạy
    hữu hạn vòng thay vì `while True` mãi mãi trong production).

    Args:
        target_task_id: Nếu set, chỉ dispatch task có ID này (filter client-side).
            Dùng cho debugging hoặc targeting task cụ thể.
    """
    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        tasks = await plane.scheduler.poll_due_tasks(worker_id=WORKER_ID, limit=poll_limit)

        # Filter to target task if specified
        if target_task_id:
            tasks = [t for t in tasks if t.task_id == target_task_id]

        if tasks:
            await asyncio.gather(*(dispatch_one_task(plane, t) for t in tasks))
        else:
            await asyncio.sleep(POLL_INTERVAL_SEC)
        iterations += 1


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="COSA Agent Worker")
    parser.add_argument("--once", action="store_true", help="Run one dispatch cycle and exit (for testing)")
    parser.add_argument("--task-id", type=str, default=None,
                        help="Target specific task ID for dispatch (filters client-side)")
    args = parser.parse_args()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        from agent_testkit.fake_sdk_model import FakeSDKModel
        plane = build_cosa_agent_plane(model=FakeSDKModel())
    else:
        plane = build_cosa_agent_plane()
    await seed_cosa_agent_specs(plane.spec_registry)
    logger.info("COSA worker %s starting, polling every %.1fs", WORKER_ID, POLL_INTERVAL_SEC)

    if args.once:
        # Single dispatch cycle for testing
        await run_worker_loop(plane, max_iterations=1, target_task_id=args.task_id)
    else:
        # Infinite polling loop (production)
        await run_worker_loop(plane, target_task_id=args.task_id)


if __name__ == "__main__":
    asyncio.run(main())
