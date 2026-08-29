from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.cosa.api.event_stream import get_cosa_event_stream_manager
from apps.cosa.auth.jwt import mint_delegation_token
from apps.cosa.config.service_identity import require_service_token

__all__ = ["create_copilot_router"]


class ThreadRefModel(BaseModel):
    thread_id: str
    contact_id: str | None = None


class CopilotCustomerSupportRequest(BaseModel):
    workspace_id: str
    thread_ref: ThreadRefModel
    intent: str
    knowledge_scope: dict[str, Any] = Field(default_factory=dict)
    identity_verified: bool = False
    correlation_id: str


def create_copilot_router() -> APIRouter:
    router = APIRouter(prefix="/agent/copilot", tags=["copilot"])

    @router.post("/customer-support", status_code=status.HTTP_202_ACCEPTED)
    async def dispatch_customer_support_copilot(
        body: CopilotCustomerSupportRequest,
        request: Request,
        x_cosa_service_token: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ) -> dict[str, str]:
        expected_token = require_service_token("COSA_SERVICE_TOKEN", purpose="copilot route auth")

        token = x_cosa_service_token
        if not token and authorization and authorization.startswith("Bearer "):
            token = authorization[7:].strip()

        if not token or token != expected_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing service token",
            )

        plane = getattr(request.app.state, "plane", None)
        if plane is None or getattr(plane, "scheduler", None) is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="COSA plane scheduler not available",
            )

        run_id = f"run_{uuid.uuid4().hex[:16]}"
        stream_mgr = get_cosa_event_stream_manager()
        stream_mgr.start_run(run_id)

        try:
            delegation_token = mint_delegation_token("system:copilot")
        except Exception:
            delegation_token = "system:copilot"

        await plane.scheduler.schedule(
            target_spec_id="cosa.customer_support",
            input_payload={
                "task_type": "run",
                "run_id": run_id,
                "agent_profile": "customer_support",
                "copilot": True,
                "workspace_id": body.workspace_id,
                "principal": "system:copilot",
                "delegation_token": delegation_token,
                "thread_ref": body.thread_ref.model_dump(),
                "intent": body.intent,
                "knowledge_scope": body.knowledge_scope,
                "identity_verified": body.identity_verified,
                "correlation_id": body.correlation_id,
            },
        )

        return {"run_id": run_id}

    return router
