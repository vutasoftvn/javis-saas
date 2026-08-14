import hashlib
import hmac
import json
import logging
from typing import Any, Optional
import httpx

from app.automations.runtime.base import AutomationProvider
from app.automations.runtime.types import (
    AutomationHealth,
    AutomationRequest,
    AutomationRunStatus,
    AutomationStartResult,
)

logger = logging.getLogger(__name__)


def generate_hmac_signature(secret: str, payload_str: str, timestamp: str) -> str:
    """Generate SHA256 HMAC signature for payload authentication."""
    data_to_sign = f"{timestamp}:{payload_str}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), data_to_sign, hashlib.sha256).hexdigest()


def verify_hmac_signature(secret: str, payload_str: str, timestamp: str, signature: str) -> bool:
    """Verify incoming SHA256 HMAC signature against expected."""
    expected = generate_hmac_signature(secret, payload_str, timestamp)
    return hmac.compare_digest(expected, signature)


class N8nAdapter(AutomationProvider):
    """Production adapter communicating with customer-owned n8n instance via authenticated Webhook / REST."""

    def __init__(
        self,
        base_url: str = "http://localhost:5678",
        api_key: Optional[str] = None,
        webhook_secret: str = "cosa-n8n-default-secret",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._webhook_secret = webhook_secret
        self._timeout = timeout

    async def health(self) -> AutomationHealth:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.get(f"{self._base_url}/healthz")
                if res.status_code == 200:
                    return AutomationHealth(
                        status="healthy",
                        provider="n8n",
                        details={"endpoint": self._base_url, "n8n_status": "ok"},
                    )
                return AutomationHealth(
                    status="degraded",
                    provider="n8n",
                    details={"endpoint": self._base_url, "status_code": res.status_code},
                )
        except Exception as exc:
            return AutomationHealth(
                status="unavailable",
                provider="n8n",
                details={"endpoint": self._base_url, "error": str(exc)},
            )

    async def execute(self, request: AutomationRequest) -> AutomationStartResult:
        payload_data = {
            "automation_key": request.automation_key,
            "execution_id": request.execution_id,
            "workspace_id": request.workspace_id,
            "company_id": request.company_id,
            "payload": request.payload,
            "correlation_id": request.correlation_id,
            "idempotency_key": request.idempotency_key,
            "callback_url": request.callback_url,
            "requested_at": request.requested_at,
        }

        payload_json = json.dumps(payload_data, sort_keys=True)
        sig = generate_hmac_signature(self._webhook_secret, payload_json, request.requested_at)

        headers = {
            "Content-Type": "application/json",
            "X-COSA-Signature": sig,
            "X-COSA-Timestamp": request.requested_at,
        }
        if self._api_key:
            headers["X-N8N-API-KEY"] = self._api_key

        url = f"{self._base_url}/webhook/cosa/{request.automation_key}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.post(url, content=payload_json, headers=headers)
                if res.status_code in (200, 201, 202):
                    res_data = res.json() if res.content else {}
                    provider_exec_id = str(res_data.get("execution_id", f"n8n_{request.execution_id}"))
                    return AutomationStartResult(
                        execution_id=request.execution_id,
                        provider_execution_id=provider_exec_id,
                        status="running",
                    )
                return AutomationStartResult(
                    execution_id=request.execution_id,
                    provider_execution_id="",
                    status="failed",
                    error=f"n8n responded with status {res.status_code}: {res.text}",
                )
        except Exception as exc:
            logger.error(f"[N8nAdapter] Execution error for {request.automation_key}: {exc}")
            return AutomationStartResult(
                execution_id=request.execution_id,
                provider_execution_id="",
                status="failed",
                error=f"Connection error to n8n: {exc}",
            )

    async def get_status(self, external_run_id: str) -> AutomationRunStatus:
        """Poll n8n's execution status via its REST API.

        Requires `api_key` (n8n's own REST API is separate from the webhook trigger this
        adapter uses for `execute`). Without one, we cannot honestly report anything beyond
        "still running" - COSA's own callback endpoint remains the authoritative source of
        truth for completion either way (see automations/router.py::receive_automation_callback).
        """
        if not self._api_key:
            return AutomationRunStatus(
                status="running",
                error="status polling unavailable: N8N_API_KEY is not configured",
            )
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.get(
                    f"{self._base_url}/api/v1/executions/{external_run_id}",
                    headers={"X-N8N-API-KEY": self._api_key},
                )
                if res.status_code == 404:
                    return AutomationRunStatus(status="failed", error="execution not found in n8n")
                if res.status_code != 200:
                    return AutomationRunStatus(
                        status="running",
                        error=f"n8n status endpoint returned {res.status_code}",
                    )
                data = res.json()
                finished = bool(data.get("finished"))
                execution_error = (
                    (data.get("data") or {}).get("resultData", {}).get("error")
                    if isinstance(data.get("data"), dict)
                    else None
                )
                if not finished:
                    return AutomationRunStatus(status="running")
                if execution_error:
                    return AutomationRunStatus(status="failed", error=str(execution_error), result=data.get("data"))
                return AutomationRunStatus(status="succeeded", result=data.get("data"))
        except Exception as exc:
            logger.error(f"[N8nAdapter] Status polling error for {external_run_id}: {exc}")
            return AutomationRunStatus(status="running", error=f"status polling failed: {exc}")

    async def cancel(self, external_run_id: str) -> None:
        """n8n's REST API does not expose an endpoint to stop an in-progress execution.

        Raise rather than silently no-op: a cancel() that appears to succeed but does nothing
        is more dangerous than one that tells the caller it was not honored. Callers needing
        this must stop/deactivate the workflow directly in the customer's n8n instance.
        """
        raise NotImplementedError(
            "N8nAdapter.cancel is not supported: n8n's REST API has no endpoint to stop an "
            "in-progress execution. Stop it from the n8n instance directly."
        )

    async def list_capabilities(self) -> list[str]:
        return [
            "system.telegram_notification",
            "system.email_notification",
            "sales.followup_email",
            "marketing.publish_social",
        ]
