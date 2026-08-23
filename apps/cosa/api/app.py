from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.cosa.api.routes import router

__all__ = ["create_cosa_app"]


def create_cosa_app() -> FastAPI:
    """Khởi tạo FastAPI Application cho COSA Agent Platform."""
    app = FastAPI(
        title="COSA Agent Platform API",
        version="1.0.0",
        description="Canonical API Gateway cho COSA AI Multi-Agent System.",
    )

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
        return {"status": "ok", "app": "cosa-agent-platform", "version": "1.0.0"}

    return app
