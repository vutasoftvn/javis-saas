"""COSA Agent Worker — Health & Readiness HTTP Server (Part 1E §1E.1).

Cung cấp hai endpoints chuẩn cho Kubernetes/Docker/LoadBalancer probes:
- GET /live: 200 nếu process còn sống.
- GET /ready: 200 nếu scheduler reachable, lease store reachable, và polling loop đang hoạt động.
  Ngược lại trả 503 kèm trạng thái chi tiết của từng check (tuyệt đối không để lộ DSN/secrets).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

__all__ = [
    "WorkerHealthState",
    "check_lease_store_health",
    "check_polling_health",
    "check_scheduler_health",
    "create_worker_health_app",
    "start_worker_health_server",
]

logger = logging.getLogger("cosa.worker.health")


@dataclass
class WorkerHealthState:
    """Trạng thái sức khoẻ nội bộ của worker process."""

    last_poll_ts: float | None = None
    poll_interval_sec: float = 1.0
    is_running: bool = True


async def check_scheduler_health(scheduler: Any) -> bool:
    """Kiểm tra tính sẵn sàng của scheduler client."""
    if scheduler is None:
        return False

    base_url = getattr(scheduler, "_base_url", None)
    if base_url:
        try:
            client = getattr(scheduler, "_client", None)
            if (
                client is not None
                and isinstance(client, httpx.AsyncClient)
                and not client.is_closed
            ):
                resp = await client.get(f"{base_url}/healthz", timeout=2.0)
                return resp.status_code == 200
            async with httpx.AsyncClient(timeout=2.0) as temp_client:
                resp = await temp_client.get(f"{base_url}/healthz")
                return resp.status_code == 200
        except Exception:
            return False

    if hasattr(scheduler, "is_healthy") and callable(scheduler.is_healthy):
        try:
            res = scheduler.is_healthy()
            if asyncio.iscoroutine(res):
                return bool(await res)
            return bool(res)
        except Exception:
            return False

    # In-memory scheduler hoặc local object
    return True


async def check_lease_store_health(lease_client: Any) -> bool:
    """Kiểm tra tính sẵn sàng của lease client / store."""
    if lease_client is None:
        return False

    base_url = getattr(lease_client, "_base_url", None)
    if base_url:
        try:
            client = getattr(lease_client, "_client", None)
            if (
                client is not None
                and isinstance(client, httpx.AsyncClient)
                and not client.is_closed
            ):
                resp = await client.get(f"{base_url}/healthz", timeout=2.0)
                return resp.status_code == 200
            async with httpx.AsyncClient(timeout=2.0) as temp_client:
                resp = await temp_client.get(f"{base_url}/healthz")
                return resp.status_code == 200
        except Exception:
            return False

    if hasattr(lease_client, "is_healthy") and callable(lease_client.is_healthy):
        try:
            res = lease_client.is_healthy()
            if asyncio.iscoroutine(res):
                return bool(await res)
            return bool(res)
        except Exception:
            return False

    # In-memory lease store hoặc local object
    return True


def check_polling_health(health_state: WorkerHealthState) -> bool:
    """Kiểm tra vòng lặp polling: phải đã poll ít nhất 1 lần và không bị treo quá 5x poll_interval."""
    if not health_state.is_running or health_state.last_poll_ts is None:
        return False
    elapsed = time.monotonic() - health_state.last_poll_ts
    max_allowed = max(health_state.poll_interval_sec * 5.0, 5.0)
    return elapsed < max_allowed


def create_worker_health_app(
    plane: Any,
    health_state: WorkerHealthState,
    worker_id: str = "worker",
) -> FastAPI:
    """Tạo FastAPI application tối giản phục vụ /live và /ready."""
    app = FastAPI(title="COSA Worker Health", docs_url=None, redoc_url=None)

    @app.get("/live")
    async def live():
        return {
            "status": "ok" if health_state.is_running else "error",
            "app": "cosa-worker",
            "worker_id": worker_id,
            "live": health_state.is_running,
        }

    @app.get("/ready")
    async def ready():
        scheduler_ok = await check_scheduler_health(getattr(plane, "scheduler", None))
        lease_store_ok = await check_lease_store_health(getattr(plane, "lease_client", None))
        polling_ok = check_polling_health(health_state)

        all_ok = scheduler_ok and lease_store_ok and polling_ok
        status_code = 200 if all_ok else 503

        # Body phản ánh trạng thái các thành phần — KHÔNG chứa DSN, secrets hay credentials
        return JSONResponse(
            {
                "status": "ok" if all_ok else "error",
                "app": "cosa-worker",
                "worker_id": worker_id,
                "checks": {
                    "scheduler": scheduler_ok,
                    "lease_store": lease_store_ok,
                    "polling": polling_ok,
                },
            },
            status_code=status_code,
        )

    @app.get("/metrics")
    async def metrics():
        from fastapi import Response

        from apps.cosa.observability.metrics import get_prometheus_metrics_payload

        payload, content_type = get_prometheus_metrics_payload()
        return Response(content=payload, media_type=content_type)

    return app


def start_worker_health_server(
    plane: Any,
    health_state: WorkerHealthState,
    *,
    worker_id: str = "worker",
    host: str = "0.0.0.0",
    port: int = 8090,
) -> tuple[uvicorn.Server, asyncio.Task]:
    """Khởi động health HTTP server trong background task của event loop hiện tại."""
    app = create_worker_health_app(plane, health_state, worker_id=worker_id)
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    return server, server_task
