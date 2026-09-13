"""Founder Asset Status Callback Client — Agent Platform → Company Control Plane.

POSTs signed status callback to Company control plane reporting command outcome:
SUCCESS, FAILED, or REJECTED with updated assetRef and evaluation summary.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_CALLBACK_PATH = "/internal/operations/founder/assets/status-callback"


class FounderAssetStatusCallbackClient:
    def __init__(
        self,
        base_url: str | None = None,
        service_token: str | None = None,
        client: httpx.AsyncClient | None = None,
        timeout_sec: float = 5.0,
    ) -> None:
        self._base_url = (
            base_url or os.getenv("COMPANY_SERVICE_URL") or "http://localhost:4000"
        ).rstrip("/")
        self._token = (
            service_token or os.getenv("COSA_WORKER_SERVICE_TOKEN") or "dev-worker-service-token"
        )
        self._client = client or httpx.AsyncClient(timeout=timeout_sec)

    def _headers(self) -> dict[str, str]:
        return {
            "X-Service-Token": self._token,
            "Content-Type": "application/json",
        }

    async def send_status_callback(
        self,
        *,
        command_id: str,
        workspace_id: str,
        asset_kind: str,
        operation: str,
        status: str,
        project_id: str | None = None,
        asset_ref: dict[str, Any] | None = None,
        evaluation_summary: dict[str, Any] | None = None,
        safe_reason_code: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "commandId": command_id,
            "workspaceId": workspace_id,
            "projectId": project_id,
            "assetKind": asset_kind,
            "operation": operation,
            "status": status,
            "assetRef": asset_ref or {},
            "evaluationSummary": evaluation_summary,
            "safeReasonCode": safe_reason_code,
        }
        try:
            resp = await self._client.post(
                f"{self._base_url}{_CALLBACK_PATH}",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning(
                "Failed to dispatch asset status callback for command %s: %s",
                command_id,
                exc,
            )
            return {"error": str(exc)}
