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
import contextlib
import logging
import os
import uuid

from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.api.event_stream import get_cosa_event_stream_manager
from apps.cosa.composition.agent_plane import (
    CosaAgentPlane,
    build_cosa_agent_plane,
    close_cosa_agent_plane,
)
from apps.cosa.observability.logging import log_context, setup_logging
from apps.cosa.observability.metrics import (
    dec_active_leases,
    inc_active_leases,
    set_scheduler_queue_depth,
)
from apps.cosa.observability.otel import init_tracing, trace_span
from apps.cosa.worker.handlers import (
    execute_resume_task,
    execute_run_task,
    execute_scheduled_session_task,
)
from apps.cosa.worker.health import WorkerHealthState, start_worker_health_server

__all__ = ["WORKER_ID", "dispatch_one_task", "run_worker_loop"]

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


async def _heartbeat_task_claim_only(
    plane: CosaAgentPlane, task_id: str, claim_token: str, coro
) -> None:
    """Chạy `coro` (execute_knowledge_ingestion_task) đồng thời heartbeat task
    claim định kỳ — không heartbeat lease (knowledge_ingestion không dùng lease).
    """

    async def heartbeat_task_claim() -> None:
        while True:
            await asyncio.sleep(TASK_CLAIM_HEARTBEAT_SEC)
            renewed = await plane.scheduler.heartbeat_task(
                task_id, worker_id=WORKER_ID, claim_token=claim_token
            )
            if not renewed:
                logger.warning(
                    "worker=%s failed to heartbeat task claim for task_id=%s (may have been reclaimed by sweeper)",
                    WORKER_ID,
                    task_id,
                )

    hb_task = asyncio.create_task(heartbeat_task_claim())
    try:
        await coro
    finally:
        hb_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await hb_task


async def _dispatch_knowledge_ingestion_task(plane: CosaAgentPlane, task, payload: dict) -> None:
    """Dispatch knowledge_ingestion task with task claim fencing only (no run lease).

    knowledge_ingestion tasks use scheduler's claim/heartbeat/complete fencing,
    not RunLeaseManager. Idempotency is handled via expectedStates in control plane.
    """
    try:
        # Import here to avoid circular dependency
        from apps.cosa.knowledge_ingestion.handler import execute_knowledge_ingestion_task

        # Execute handler with task claim token for control plane fencing.
        # B1: truyền knowledge_ingestion_service ĐÃ WIRE trên plane (Postgres khi
        # AGENT_DATABASE_URL set — xem composition/storage_factory.py) vào handler.
        # Không truyền → handler fallback `KnowledgeIngestionService()` =
        # InMemoryKnowledgeStore (dev) hoặc raise (prod), nên đường ingestion thật
        # không bao giờ ghi `knowledge.source_versions` (ingestion_run_id luôn NULL).
        async def _execute_handler():
            await execute_knowledge_ingestion_task(
                payload,
                claim_token=task.claim_token,
                knowledge_service=plane.knowledge_ingestion_service,
            )

        await _heartbeat_task_claim_only(plane, task.task_id, task.claim_token, _execute_handler())

        # Complete task via scheduler (no lease release needed)
        ok = await plane.scheduler.complete_task(
            task.task_id, worker_id=WORKER_ID, claim_token=task.claim_token, success=True
        )
        if not ok:
            logger.warning(
                "worker=%s task=%s (knowledge_ingestion) completed but fencing rejected — task was reclaimed by sweeper mid-execution",
                WORKER_ID,
                task.task_id,
            )
    except Exception as exc:
        logger.exception("task=%s (knowledge_ingestion) failed during execution", task.task_id)
        await plane.scheduler.complete_task(
            task.task_id,
            worker_id=WORKER_ID,
            claim_token=task.claim_token,
            success=False,
            error=str(exc),
        )


async def _dispatch_wga_task(plane: CosaAgentPlane, task, payload: dict, task_type: str) -> None:
    """Dispatch WGA headless task (goal_decomposition / workspace_task_sweep) —
    task claim fencing only (no RunLeaseManager). Handler tự sinh run_id cho
    từng sub-run; idempotency ở tầng scheduler qua coalescing_key."""
    try:
        from apps.cosa.worker.wga_run import (
            execute_goal_decomposition_task,
            execute_workspace_task_sweep_task,
        )

        stream_mgr = get_cosa_event_stream_manager()
        handler = (
            execute_goal_decomposition_task
            if task_type == "goal_decomposition"
            else execute_workspace_task_sweep_task
        )

        async def _execute_handler():
            await handler(plane, stream_mgr, payload)

        await _heartbeat_task_claim_only(plane, task.task_id, task.claim_token, _execute_handler())

        ok = await plane.scheduler.complete_task(
            task.task_id, worker_id=WORKER_ID, claim_token=task.claim_token, success=True
        )
        if not ok:
            logger.warning(
                "worker=%s task=%s (%s) completed but fencing rejected",
                WORKER_ID,
                task.task_id,
                task_type,
            )
    except Exception as exc:
        logger.exception("task=%s (%s) failed during execution", task.task_id, task_type)
        await plane.scheduler.complete_task(
            task.task_id,
            worker_id=WORKER_ID,
            claim_token=task.claim_token,
            success=False,
            error=str(exc),
        )


async def _dispatch_kickoff_suggestion_task(plane: CosaAgentPlane, task, payload: dict) -> None:
    """Dispatch kickoff wizard Bước 3 AI-suggestion task — task claim fencing
    only (no RunLeaseManager), giống `_dispatch_wga_task`. Handler tự callback
    company (completed/failed) trong mọi nhánh, không rơi vào im lặng."""
    try:
        from apps.cosa.worker.kickoff_suggestion_run import execute_kickoff_suggestion_task

        stream_mgr = get_cosa_event_stream_manager()

        async def _execute_handler():
            await execute_kickoff_suggestion_task(plane, stream_mgr, payload)

        await _heartbeat_task_claim_only(plane, task.task_id, task.claim_token, _execute_handler())

        ok = await plane.scheduler.complete_task(
            task.task_id, worker_id=WORKER_ID, claim_token=task.claim_token, success=True
        )
        if not ok:
            logger.warning(
                "worker=%s task=%s (kickoff_suggestion) completed but fencing rejected",
                WORKER_ID,
                task.task_id,
            )
    except Exception as exc:
        logger.exception("task=%s (kickoff_suggestion) failed during execution", task.task_id)
        await plane.scheduler.complete_task(
            task.task_id,
            worker_id=WORKER_ID,
            claim_token=task.claim_token,
            success=False,
            error=str(exc),
        )


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
            renewed = await plane.scheduler.heartbeat_task(
                task_id, worker_id=WORKER_ID, claim_token=claim_token
            )
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
            with contextlib.suppress(asyncio.CancelledError):
                await t


async def dispatch_one_task(plane: CosaAgentPlane, task) -> None:
    """Xử lý 1 `ScheduledTaskRecord` đã được `poll_due_tasks()` claim (atomic,
    status='processing', kèm `claim_token` fencing) — acquire lease cho
    run_id, dispatch theo `task_type`, release lease, đánh dấu task
    complete/failed. `complete_task()` có thể bị fencing từ chối (`ok=False`)
    nếu sweeper đã reclaim task này (worker treo quá lâu) — khi đó KHÔNG log
    lỗi, vì một worker khác (hoặc lần retry sau) đang/sẽ xử lý lại task.

    knowledge_ingestion tasks không dùng RunLeaseManager — chỉ dùng task claim
    fencing từ scheduler (heartbeat_task + complete_task).
    """
    stream_mgr = get_cosa_event_stream_manager()
    payload = task.input_payload
    task_type = payload.get("task_type")
    run_id = payload.get("run_id")
    if not run_id and task_type == "scheduled_session":
        run_id = f"run_sched_{payload.get('schedule_execution_id', task.task_id)}"
    claim_token = task.claim_token
    workspace_id = payload.get("workspace_id")

    with log_context(run_id=run_id, workspace_id=workspace_id):
        async with trace_span(
            "worker.dispatch_task",
            attributes={
                "task_id": task.task_id,
                "task_type": task_type,
                "run_id": run_id,
                "workspace_id": workspace_id,
                "worker_id": WORKER_ID,
            },
        ):
            # Branch: knowledge_ingestion tasks don't use run leases
            if task_type == "knowledge_ingestion":
                await _dispatch_knowledge_ingestion_task(plane, task, payload)
                return

            # Branch: WGA headless tasks — tự sinh run_id nội bộ (per sub-run),
            # idempotency qua coalescing_key ở scheduler; không dùng RunLeaseManager.
            if task_type in ("goal_decomposition", "workspace_task_sweep"):
                await _dispatch_wga_task(plane, task, payload, task_type)
                return

            # Branch: kickoff wizard Bước 3 AI-suggestion — task claim fencing
            # only, giống WGA headless task.
            if task_type == "kickoff_suggestion":
                await _dispatch_kickoff_suggestion_task(plane, task, payload)
                return

            if not run_id:
                logger.error("task=%s missing run_id in payload, marking failed", task.task_id)
                await plane.scheduler.complete_task(
                    task.task_id,
                    worker_id=WORKER_ID,
                    claim_token=claim_token,
                    success=False,
                    error="missing run_id in payload",
                )
                return

            lease_result = await plane.lease_client.acquire_lease(
                run_id, WORKER_ID, ttl_sec=LEASE_TTL_SEC
            )
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
            inc_active_leases()
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
                        await execute_scheduled_session_task(
                            plane, stream_mgr, payload, run_id=run_id
                        )

                    coro = _with_optional_delay()
                else:
                    logger.error("task=%s unknown task_type=%r", task.task_id, task_type)
                    await plane.scheduler.complete_task(
                        task.task_id,
                        worker_id=WORKER_ID,
                        claim_token=claim_token,
                        success=False,
                        error=f"unknown task_type={task_type!r}",
                    )
                    return

                await _run_with_heartbeats(
                    plane, run_id, lease_result.lease.lease_token, task.task_id, claim_token, coro
                )
                ok = await plane.scheduler.complete_task(
                    task.task_id, worker_id=WORKER_ID, claim_token=claim_token, success=True
                )
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
                    task.task_id,
                    worker_id=WORKER_ID,
                    claim_token=claim_token,
                    success=False,
                    error=str(exc),
                )
            finally:
                dec_active_leases()
                await plane.lease_client.release_lease(
                    run_id, WORKER_ID, lease_result.lease.lease_token
                )


async def run_worker_loop(
    plane: CosaAgentPlane,
    *,
    poll_limit: int = 10,
    max_iterations: int | None = None,
    target_task_id: str | None = None,
    health_state: WorkerHealthState | None = None,
) -> None:
    """Vòng lặp chính: poll → claim (atomic ở tầng scheduler) → lease →
    execute → release → complete. `max_iterations` chỉ dùng cho test (chạy
    hữu hạn vòng thay vì `while True` mãi mãi trong production).

    Args:
        target_task_id: Nếu set, chỉ dispatch task có ID này (filter client-side).
            Dùng cho debugging hoặc targeting task cụ thể.
        health_state: Trạng thái sức khoẻ dùng cho /ready endpoint (Part 1E).
    """
    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        if health_state is not None:
            health_state.last_poll_ts = asyncio.get_event_loop().time()

        tasks = await plane.scheduler.poll_due_tasks(worker_id=WORKER_ID, limit=poll_limit)
        set_scheduler_queue_depth(len(tasks) if tasks else 0)

        # Filter to target task if specified
        if target_task_id:
            tasks = [t for t in tasks if t.task_id == target_task_id]

        if tasks:
            await asyncio.gather(*(dispatch_one_task(plane, t) for t in tasks))
        else:
            await asyncio.sleep(POLL_INTERVAL_SEC)
        iterations += 1


async def main() -> None:
    setup_logging("cosa-worker")
    init_tracing("cosa-worker")
    parser = argparse.ArgumentParser(description="COSA Agent Worker")
    parser.add_argument(
        "--once", action="store_true", help="Run one dispatch cycle and exit (for testing)"
    )
    parser.add_argument(
        "--task-id",
        type=str,
        default=None,
        help="Target specific task ID for dispatch (filters client-side)",
    )
    args = parser.parse_args()

    # Reject APP_ENV=test when using real API key — this seam is for test execution only.
    # APP_ENV=test + no DEEPSEEK_API_KEY is allowed (uses FakeSDKModel).
    # APP_ENV=test + DEEPSEEK_API_KEY is suspicious (mixing test mode with production API).
    env_name = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
    if env_name == "test" and os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError(
            "APP_ENV=test with DEEPSEEK_API_KEY is not allowed. "
            "Test mode (APP_ENV=test) should only use FakeSDKModel (no DEEPSEEK_API_KEY). "
            "Production deployments must use APP_ENV=production, staging, or development."
        )

    # Fail-closed danh tính service ở startup worker: token company-callback và
    # COMPANY_SERVICE_URL phải là giá trị thật trong staging/production
    # (development/test vẫn resolve dev default).
    from apps.cosa.config.service_identity import validate_service_identity

    validate_service_identity(
        need_secret=False,
        tokens=[("COSA_SERVICE_TOKEN", "company callback auth")],
        urls=[("COMPANY_SERVICE_URL", "company callback", "http://127.0.0.1:4000")],
    )

    if not os.environ.get("DEEPSEEK_API_KEY"):
        from agent_testkit.fake_sdk_model import FakeSDKModel

        plane = build_cosa_agent_plane(model=FakeSDKModel())
    else:
        plane = build_cosa_agent_plane()
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry,
        capability_registry=plane.capability_registry,
    )
    logger.info("COSA worker %s starting, polling every %.1fs", WORKER_ID, POLL_INTERVAL_SEC)

    health_state = WorkerHealthState(poll_interval_sec=POLL_INTERVAL_SEC)
    health_port = int(os.environ.get("COSA_WORKER_HEALTH_PORT", "8090"))
    health_host = os.environ.get("COSA_WORKER_HEALTH_HOST", "0.0.0.0")

    server, server_task = start_worker_health_server(
        plane, health_state, worker_id=WORKER_ID, host=health_host, port=health_port
    )

    try:
        if args.once:
            # Single dispatch cycle for testing
            await run_worker_loop(
                plane,
                max_iterations=1,
                target_task_id=args.task_id,
                health_state=health_state,
            )
        else:
            # Infinite polling loop (production)
            await run_worker_loop(
                plane,
                target_task_id=args.task_id,
                health_state=health_state,
            )
    finally:
        health_state.is_running = False
        server.should_exit = True
        server_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await server_task
        await close_cosa_agent_plane(plane)


if __name__ == "__main__":
    asyncio.run(main())
