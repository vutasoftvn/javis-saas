from __future__ import annotations

import hmac
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.cosa.api.event_stream import get_cosa_event_stream_manager
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
    # IA25: services/company giờ LUÔN mint và gửi delegation ngắn hạn
    # (mintCopilotDelegationToken, cùng shape {sub, auth_time} ký bằng
    # JWT_SECRET) cho ĐÚNG người dùng đã yêu cầu Copilot — route này KHÔNG
    # còn tự mint token khác dưới danh nghĩa "system:copilot" (sai secret,
    # secret platform cũ thay vì JWT_SECRET, khiến mọi lời gọi ngược lại
    # services/company để đọc thread/customer/knowledge context luôn fail
    # xác thực). Bắt buộc có — thiếu thì từ chối thẳng, không tự chế fallback.
    actor_id: str
    delegation_token: str


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

        if not token or not hmac.compare_digest(token.encode(), expected_token.encode()):
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

        await plane.scheduler.schedule(
            target_spec_id="cosa.customer_support",
            input_payload={
                "task_type": "run",
                "run_id": run_id,
                "agent_profile": "customer_support",
                "copilot": True,
                "workspace_id": body.workspace_id,
                "principal": f"user:{body.actor_id}",
                "actor_id": body.actor_id,
                # Forward NGUYÊN VẸN — KHÔNG tự mint token khác ở đây. Token
                # này đã được services/company ký cho đúng user thật (IA25).
                "delegation_token": body.delegation_token,
                "thread_ref": body.thread_ref.model_dump(),
                "intent": body.intent,
                "knowledge_scope": body.knowledge_scope,
                "identity_verified": body.identity_verified,
                "correlation_id": body.correlation_id,
            },
        )

        return {"run_id": run_id}

    return router
