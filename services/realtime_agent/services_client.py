from __future__ import annotations

import json as json_module
import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import httpx
import jwt

_DEV_PLATFORM_JWT_SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"
_DEV_JWT_SECRET = "cosa-dev-jwt-secret-do-not-use-in-prod"


def _is_staging_or_prod() -> bool:
    env_name = os.environ.get(
        "ENVIRONMENT", os.environ.get("APP_ENV", "development")
    ).lower()
    return env_name in ("production", "staging", "prod")


def _get_platform_jwt_secret() -> str:
    secret = os.environ.get("PLATFORM_JWT_SECRET")
    if _is_staging_or_prod():
        if not secret or secret == _DEV_PLATFORM_JWT_SECRET or len(secret) < 32:
            raise RuntimeError(
                "PLATFORM_JWT_SECRET must be explicitly set with >= 32 characters in staging/production"
            )
        return secret
    return secret or _DEV_PLATFORM_JWT_SECRET


PLATFORM_JWT_SECRET = _get_platform_jwt_secret()


def generate_service_token(
    user_id: int | str,
    workspace_id: int | str,
    role: str = "founder",
    company_id: int | str | None = None,
) -> str:
    """Generates a signed service-to-service JWT token for AgentOS authentication."""
    payload = {
        "sub": str(user_id),
        "workspace_id": str(workspace_id),
        "company_id": str(company_id or workspace_id),
        "role": role,
    }
    return jwt.encode(payload, PLATFORM_JWT_SECRET, algorithm="HS256")


class ServicesClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class ServicesClient:
    """Async HTTP Client for Realtime Voice Agent to interact with AgentOS API.

    Boundary Enforcement (§17.2, §17.3, §5.5):
    - NO direct database access or SessionLocal.
    - NO direct calls to REST domain endpoints (operations, commercial, finance-legal).
    - Calls AgentOS API (/agent/...) with full governance, approvals, and context continuity.
    - Transmits resolved TenantContext via signed service-to-service JWT and headers.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("AGENTOS_API_URL")
            or os.getenv("SERVICES_URL")
            # cosa-api (apps/cosa/api/routes.py) trên :8001 — không phải brain-api :8000,
            # service đó đang hỏng và bị đóng băng theo ADR-012.
            or "http://localhost:8001"
        ).rstrip("/")
        self.timeout = timeout

    def _headers(
        self,
        workspace_id: int | str,
        user_id: int | str | None = None,
        role: str = "founder",
        company_id: int | str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, str]:
        uid = str(user_id or "1")
        wid = str(workspace_id)
        cid = str(company_id or wid)
        token = generate_service_token(uid, wid, role=role, company_id=cid)
        corr_id = correlation_id or str(uuid.uuid4())
        return {
            "Authorization": f"Bearer {token}",
            "X-Workspace-Id": wid,
            "X-Company-Id": cid,
            "X-Correlation-Id": corr_id,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        workspace_id: int | str,
        user_id: int | str | None = None,
        role: str = "founder",
        company_id: int | str | None = None,
        correlation_id: str | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = self._headers(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            company_id=company_id,
            correlation_id=correlation_id,
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, params=params, json=json, headers=headers)
                if response.status_code >= 400:
                    try:
                        err_payload = response.json()
                        message = err_payload.get("message") or err_payload.get("detail", response.text)
                    except Exception:
                        message = response.text
                    raise ServicesClientError(
                        f"Agent API Error ({response.status_code}): {message}",
                        status_code=response.status_code,
                        details=response.text,
                    )
                return response.json()
            except httpx.RequestError as exc:
                raise ServicesClientError(f"Network error communicating with Agent API at {url}: {exc}") from exc

    # 1. Agent Conversations (§17.1, §17.3)
    async def create_conversation(
        self,
        workspace_id: int | str,
        user_id: int | str,
        title: str | None = None,
        active_agent_profile: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/agent/conversations",
            workspace_id=workspace_id,
            user_id=user_id,
            json={
                "title": title or "Voice Session",
                "active_agent_profile": active_agent_profile or "founder_assistant",
            },
            correlation_id=correlation_id,
        )

    async def get_conversation(
        self,
        conversation_id: str,
        workspace_id: int | str,
        user_id: int | str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/agent/conversations/{conversation_id}",
            workspace_id=workspace_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )

    # 2. Agent Messages & Runs
    async def send_message(
        self,
        conversation_id: str,
        content: str,
        workspace_id: int | str,
        user_id: int | str,
        role: str = "user",
        parent_message_id: str | None = None,
        attachments: list[dict] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"content": content, "role": role}
        if parent_message_id:
            payload["parent_message_id"] = parent_message_id
        if attachments:
            payload["attachments"] = attachments
        return await self._request(
            "POST",
            f"/agent/conversations/{conversation_id}/messages",
            workspace_id=workspace_id,
            user_id=user_id,
            json=payload,
            correlation_id=correlation_id,
        )

    # 3. Stream Run Events (SSE)
    async def stream_run_events(
        self,
        run_id: str,
        workspace_id: int | str,
        user_id: int | str,
        since_sequence: int | None = None,
        correlation_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        url = f"{self.base_url}/agent/runs/{run_id}/events"
        headers = self._headers(
            workspace_id=workspace_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )
        params = {"since_sequence": since_sequence} if since_sequence is not None else None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("GET", url, headers=headers, params=params) as resp:
                if resp.status_code >= 400:
                    raise ServicesClientError(
                        f"SSE stream error: status={resp.status_code}",
                        status_code=resp.status_code,
                    )
                buffer = ""
                async for chunk in resp.aiter_text():
                    buffer += chunk
                    while "\n\n" in buffer:
                        event_block, buffer = buffer.split("\n\n", 1)
                        event_data = None
                        event_type = None
                        for line in event_block.splitlines():
                            if line.startswith("event:"):
                                event_type = line[len("event:") :].strip()
                            elif line.startswith("data:"):
                                data_str = line[len("data:") :].strip()
                                try:
                                    event_data = json_module.loads(data_str)
                                except Exception:
                                    event_data = data_str
                        if event_type and event_data is not None:
                            yield {"event": event_type, "data": event_data}

    # 4. Approvals (§17.1.3, §17.2)
    async def decide_approval(
        self,
        approval_id: str,
        approved: bool,
        reason: str | None = None,
        workspace_id: int | str = "1",
        user_id: int | str = "1",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/agent/approvals/{approval_id}/decision",
            workspace_id=workspace_id,
            user_id=user_id,
            json={"approved": approved, "reason": reason},
            correlation_id=correlation_id,
        )

    # 5. Cancel Run
    async def cancel_run(
        self,
        run_id: str,
        workspace_id: int | str,
        user_id: int | str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/agent/runs/{run_id}/cancel",
            workspace_id=workspace_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )

    # 6. Execute Agent Turn (Helper)
    async def execute_agent_turn(
        self,
        conversation_id: str,
        content: str,
        workspace_id: int | str,
        user_id: int | str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        run_info = await self.send_message(
            conversation_id=conversation_id,
            content=content,
            workspace_id=workspace_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )
        run_id = run_info["run_id"]
        output_chunks: list[str] = []
        approval_info = None
        error_info = None

        async for ev in self.stream_run_events(
            run_id=run_id,
            workspace_id=workspace_id,
            user_id=user_id,
            correlation_id=correlation_id,
        ):
            event_type = ev.get("event")
            payload = ev.get("data", {})
            if event_type == "message.delta":
                delta = payload.get("delta", "")
                output_chunks.append(delta)
            elif event_type == "approval.required":
                approval_info = payload
                break
            elif event_type == "run.completed":
                if not output_chunks and payload.get("output"):
                    output_chunks.append(payload.get("output"))
                break
            elif event_type == "run.failed":
                error_info = payload.get("error", "Run failed")
                break

        full_output = "".join(output_chunks)
        return {
            "run_id": run_id,
            "output": full_output,
            "approval_required": approval_info is not None,
            "approval_info": approval_info,
            "error": error_info,
        }
