from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.cosa.agents.seed import seed_cosa_agent_specs
from apps.cosa.api.routes import router
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
        try:
            yield
        finally:
            if not injected:
                await close_cosa_agent_plane(app.state.plane)

    app = FastAPI(
        title="COSA Agent Platform API",
        version="1.0.0",
        description="Canonical API Gateway cho COSA AI Multi-Agent System.",
        lifespan=lifespan,
    )

    if injected:
        app.state.plane = plane

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

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
