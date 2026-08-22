from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentos.api.chat.routes import router as chat_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AgentOS Chat API",
        version="1.0.0",
        description="REST and SSE API for AgentOS Conversations, Runs, Approvals, and Multi-layer Context.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)

    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "service": "agentos-api"}

    return app


app = create_app()
