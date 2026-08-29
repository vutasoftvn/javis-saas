from __future__ import annotations

import os

import httpx
from agent.capabilities.grants import ConnectorGrant

from apps.cosa.config.planes import resolve_platform_control_plane_url

__all__ = ["ConnectorGrantHttpClient"]


class ConnectorGrantHttpClient:
    """Gọi `/cosa/connectors/assert` thật (đã hardened Task 1-3) để lấy trạng
    thái grant hiện tại — dùng làm `connector_grant_resolver` cho
    `CapabilityGateway`. Không tự cache lâu dài: mỗi lần gateway gọi lại,
    client này gọi lại HTTP thật, đúng yêu cầu re-check tại thời điểm side
    effect."""

    def __init__(
        self, base_url: str | None = None, worker_token_provider=None, timeout: float = 10.0
    ) -> None:
        self.base_url = (base_url or resolve_platform_control_plane_url()).rstrip("/")
        self._worker_token_provider = worker_token_provider
        self.timeout = timeout

    async def assert_usable(
        self, connector_key: str, *, workspace_id: str, conversation_id: str, action: str
    ) -> ConnectorGrant | None:
        token = (
            self._worker_token_provider()
            if self._worker_token_provider
            else os.environ.get("COSA_WORKER_SERVICE_TOKEN", "")
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(
                f"{self.base_url}/cosa/connectors/assert",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "workspaceId": workspace_id,
                    "conversationId": conversation_id,
                    "connectorKey": connector_key,
                    "action": action,
                },
            )
            data = res.json()
        if not data.get("ok"):
            return None
        return ConnectorGrant(
            grant_id=f"{connector_key}:{conversation_id}",
            tenant_id=workspace_id,
            principal="system",
            connector_id=connector_key,
            allowed_actions=(action,),
            is_revoked=False,
            metadata={"secret_ref": data.get("secretRef", "")},
        )
