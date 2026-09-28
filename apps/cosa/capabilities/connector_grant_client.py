from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from agent.capabilities.grants import ConnectorGrant, ConnectorGrantDeniedError

from apps.cosa.config.planes import resolve_platform_control_plane_url

__all__ = ["ConnectorGrantHttpClient", "build_connector_grant_resolver"]

# Control plane trả `{ok:false}` không kèm mã (không nên xảy ra) → mã chung, vẫn DENY.
_GENERIC_DENY_CODE = "connector_grant_denied"


class ConnectorGrantHttpClient:
    """Gọi `/cosa/connectors/assert` thật (đã hardened Task 1-3) để lấy trạng
    thái grant hiện tại — dùng làm `connector_grant_resolver` cho
    `CapabilityGateway`. Không tự cache lâu dài: mỗi lần gateway gọi lại,
    client này gọi lại HTTP thật, đúng yêu cầu re-check tại thời điểm side
    effect.

    Hợp đồng kết quả (review Task 4 / plan hub đợt 2 B3):
    - `ok:true` → `ConnectorGrant` với `principal="*"`: control plane đã scope grant theo
      organization + conversation (session grant) + connector + action (+ scope); principal của
      run (`user:<id>`, `system:copilot`, `service:scheduler`...) không có trong grant control
      plane nên không có gì để so. Trước đây đặt `"system"` làm `verify_connector_grant` DENY
      "Principal mismatch" mọi run thật. Tenant vẫn = workspace_id (gateway so với run).
    - `ok:false` → raise `ConnectorGrantDeniedError(code)` với mã control plane
      (`connector_reauth_required`, `connector_not_granted_to_session`,
      `connector_installation_disabled`, `connector_scope_missing`,
      `connector_action_not_allowed`) — không nuốt lý do thành `None`.
    - HTTP ≠ 200 / JSON hỏng → raise lỗi thường ⇒ gateway `resolver_error`, fail-closed.
    """

    def __init__(
        self,
        base_url: str | None = None,
        worker_token_provider: Callable[[], str] | None = None,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or resolve_platform_control_plane_url()).rstrip("/")
        self._worker_token_provider = worker_token_provider
        self.timeout = timeout
        self._transport = transport

    async def assert_usable(
        self,
        connector_key: str,
        *,
        workspace_id: str,
        conversation_id: str,
        action: str,
        required_scope: str | None = None,
    ) -> ConnectorGrant:
        token = (
            self._worker_token_provider()
            if self._worker_token_provider
            else os.environ.get("COSA_WORKER_SERVICE_TOKEN", "")
        )
        body: dict[str, Any] = {
            "organizationId": workspace_id,
            "conversationId": conversation_id,
            "connectorKey": connector_key,
            "action": action,
        }
        if required_scope:
            body["requiredScope"] = required_scope
        async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
            res = await client.post(
                f"{self.base_url}/cosa/connectors/assert",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
        if res.status_code != 200:
            raise RuntimeError(f"connector assert failed: HTTP {res.status_code}")
        data = res.json()
        if not isinstance(data, dict):
            raise RuntimeError("connector assert returned a non-object response")
        if not data.get("ok"):
            raise ConnectorGrantDeniedError(str(data.get("error") or _GENERIC_DENY_CODE))
        return ConnectorGrant(
            grant_id=f"{connector_key}:{conversation_id}",
            tenant_id=workspace_id,
            principal="*",
            connector_id=connector_key,
            allowed_actions=(action,),
            is_revoked=False,
            metadata={"secret_ref": data.get("secretRef", "")},
        )

    async def assert_usable_for_execution(
        self,
        connector_key: str,
        *,
        workspace_id: str,
        execution_id: str,
        action: str,
        required_scope: str | None = None,
    ) -> dict[str, Any]:
        """B5 (Task 6b) — preflight connector cho lịch nền uỷ quyền trước
        (`execute_scheduled_session_task`), TRƯỚC khi tạo conversation/gọi
        model. Đường `/cosa/connectors/assert` với `executionId` thay
        `conversationId` (xem `assertConnectorInvocationForExecution` ở
        `services/cosa/services/workspace-connector.service.ts`) — kiểm theo
        `connectorGrantIdsSnapshot` đã chốt lúc founder duyệt kế hoạch, không
        phải session grant theo conversation (lịch nền không có).

        Khác `assert_usable`: KHÔNG raise khi `ok:false` — trả nguyên
        `{"ok": bool, "secretRef"?: str, "error"?: str}` để caller (worker)
        tự map mã lỗi sang `blocked_reauth`/`failed`, không cần try/except.
        HTTP lỗi hạ tầng vẫn raise (fail-closed, caller coi là `failed` tạm
        thời — không phải "founder cần xử lý lại")."""
        token = (
            self._worker_token_provider()
            if self._worker_token_provider
            else os.environ.get("COSA_WORKER_SERVICE_TOKEN", "")
        )
        body: dict[str, Any] = {
            "organizationId": workspace_id,
            "executionId": execution_id,
            "connectorKey": connector_key,
            "action": action,
        }
        if required_scope:
            body["requiredScope"] = required_scope
        async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
            res = await client.post(
                f"{self.base_url}/cosa/connectors/assert",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
        if res.status_code != 200:
            raise RuntimeError(f"connector assert (execution) failed: HTTP {res.status_code}")
        data = res.json()
        if not isinstance(data, dict):
            raise RuntimeError("connector assert (execution) returned a non-object response")
        return {
            "ok": bool(data.get("ok")),
            "secretRef": data.get("secretRef"),
            "error": data.get("error"),
        }


def build_connector_grant_resolver(
    client: ConnectorGrantHttpClient, registry: Any
) -> Callable[[str, Any], Awaitable[ConnectorGrant | None]]:
    """Resolver production cho `CapabilityGateway(connector_grant_resolver=...)`.

    `action` = capability id (hợp đồng với `allowedActions` của session grant);
    `required_scope` = `spec.metadata["scope"]` nếu capability khai báo (vd. `email.digest.read`
    → `mail:read`), để control plane kiểm scope của authorization (`connector_scope_missing`).
    """

    async def resolver(connector_id: str, req: Any) -> ConnectorGrant | None:
        reg = registry.get(req.capability_id)
        scope = (reg.spec.metadata or {}).get("scope") if reg else None
        ctx = req.context
        meta = ctx if isinstance(ctx, dict) else (getattr(ctx, "metadata", None) or {})
        return await client.assert_usable(
            connector_id,
            workspace_id=req.workspace_id or "",
            conversation_id=str(meta.get("conversation_id", "") or ""),
            action=req.capability_id,
            required_scope=scope if isinstance(scope, str) and scope else None,
        )

    return resolver
