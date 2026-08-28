from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.routes import router
from apps.cosa.api.skill_registry_routes import create_skill_registry_router
from apps.cosa.api.event_intake_routes import create_event_intake_router
from apps.cosa.api.event_rule_routes import create_event_rule_router
from apps.cosa.api.event_operations_routes import create_event_operations_router
from apps.cosa.composition.agent_plane import CosaAgentPlane, build_cosa_agent_plane, close_cosa_agent_plane

__all__ = ["create_cosa_app"]


def create_cosa_app(plane: Optional[CosaAgentPlane] = None) -> FastAPI:
    """Khởi tạo FastAPI Application cho COSA Agent Platform.

    Phase 5 Composition Lifecycle (docs/implementation/production-runtime-
    closure.md §10) — `CosaAgentPlane` được tạo ĐÚNG 1 LẦN, ở `lifespan`
    startup, không còn lazy singleton tạo trên request đầu tiên
    (`apps/cosa/api/routes.py::get_cosa_plane()` cũ). Thiếu config
    (`AGENT_CORE_DATABASE_URL`/`DEEPSEEK_API_KEY`) làm ASGI startup fail
    ngay — app không bao giờ chuyển sang trạng thái phục vụ traffic với
    provider chưa cấu hình đúng.

    `plane=` cho phép test/dev inject `CosaAgentPlane` đã build sẵn (in-memory
    repository, `FakeSDKModel`, ...) — gán thẳng vào `app.state.plane` ngay
    khi tạo app, KHÔNG phụ thuộc lifespan có chạy hay không (test hiện tại
    dùng `httpx.ASGITransport` không tự trigger ASGI lifespan protocol).
    Caller truyền `plane=` tự sở hữu vòng đời của nó — lifespan shutdown sẽ
    KHÔNG đóng plane đó (chỉ đóng plane app tự build khi không có injection).
    """
    injected = plane is not None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if not injected:
            # Fail-fast: build_cosa_agent_plane() raise ngay nếu thiếu
            # AGENT_CORE_DATABASE_URL/DEEPSEEK_API_KEY — exception ở đây làm
            # ASGI server từ chối start, không serve traffic với config thiếu.
            app.state.plane = build_cosa_agent_plane()
            # Seed registry sau khi plane đã dựng (Wave M2b) — publish_agent_spec()
            # sẽ reject nếu Prompt/ModelPolicy chưa publish, nên seed phải chạy
            # trước request đầu tiên tới execute_run_task.
            await seed_cosa_agent_specs(app.state.plane.spec_registry)

            # Dựng event_intake_deps production (async — asyncpg pool) sau khi
            # plane sẵn sàng. Không có DB ⇒ giữ None; endpoint /agent/internal/events
            # trả 500 "not configured" (an toàn, không im lặng).
            _db_url = os.environ.get("AGENT_CORE_DATABASE_URL")
            if _db_url:
                from apps.cosa.events.deps import build_event_intake_deps

                app.state.plane.event_intake_deps = await build_event_intake_deps(
                    database_url=_db_url,
                    spec_registry=app.state.plane.spec_registry,
                    capability_registry=app.state.plane.capability_registry,
                )
        try:
            yield
        finally:
            if not injected:
                _deps = getattr(app.state.plane, "event_intake_deps", None)
                if _deps is not None and hasattr(_deps, "aclose"):
                    await _deps.aclose()
                await close_cosa_agent_plane(app.state.plane)

    app = FastAPI(
        title="COSA Agent Platform API",
        version="1.0.0",
        description="Canonical API Gateway cho COSA AI Multi-Agent System.",
        lifespan=lifespan,
    )

    if injected:
        app.state.plane = plane

    import os
    env_name = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()

    # Reject APP_ENV=test outside of test execution — this seam is for deterministic
    # test fixtures only (FakeSDKModel), not for production use
    if env_name == "test" and not injected:
        raise RuntimeError(
            "APP_ENV=test is reserved for test execution with injected planes. "
            "Production deployments must use APP_ENV=production, staging, or development."
        )

    is_staging_or_prod = env_name in ("production", "staging", "prod")

    cors_origins_env = os.environ.get("CORS_ORIGINS")
    if cors_origins_env:
        cors_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    else:
        if is_staging_or_prod:
            raise RuntimeError(
                f"CORS_ORIGINS must be explicitly configured in {env_name} environment"
            )
        cors_origins = ["*"]

    if is_staging_or_prod and "*" in cors_origins:
        raise RuntimeError("Wildcard CORS origin '*' is not permitted in staging/production with allow_credentials=True")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(create_skill_registry_router())
    app.include_router(create_event_intake_router())
    app.include_router(create_event_rule_router())
    app.include_router(create_event_operations_router())

    @app.get("/healthz")
    async def health_check():
        # app.state.plane luôn tồn tại khi endpoint này reachable (lifespan
        # startup fail-fast ở trên nếu build thất bại) — readiness thật, không
        # còn trả "ok" cố định bất kể provider có sẵn sàng hay không.
        current_plane = getattr(app.state, "plane", None)
        return {
            "status": "ok" if current_plane is not None else "not_ready",
            "app": "cosa-agent-platform",
            "version": "1.0.0",
        }

    return app
