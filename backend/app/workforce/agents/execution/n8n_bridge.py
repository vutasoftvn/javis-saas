import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Dict, Optional
import httpx

from app.workforce.agents.execution.types import ExecutionJobResult
from app.core.snowflake import generate_snowflake_id

logger = logging.getLogger(__name__)


def generate_hmac_signature(secret: str, payload_str: str, timestamp: str) -> str:
    """Generate SHA-256 HMAC signature for execution callback payload authentication."""
    data_to_sign = f"{timestamp}:{payload_str}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), data_to_sign, hashlib.sha256).hexdigest()


def verify_hmac_signature(
    secret: str,
    payload_str: str,
    timestamp: str,
    signature: str,
    max_age_seconds: int = 300,
) -> bool:
    """Verify incoming SHA-256 HMAC signature and timestamp replay window."""
    try:
        ts = int(timestamp)
        now = int(time.time())
        if abs(now - ts) > max_age_seconds:
            logger.warning("[HMAC] Replay window expired: timestamp=%s, now=%s", ts, now)
            return False
    except (ValueError, TypeError):
        return False

    expected = generate_hmac_signature(secret, payload_str, timestamp)
    return hmac.compare_digest(expected, signature)


async def _send_signed_payload(
    url: str,
    secret: Optional[str],
    payload_dict: Dict[str, Any],
    timeout: float = 10.0,
) -> bool:
    """Send an authenticated HMAC-signed HTTP POST payload."""
    if not url or not url.startswith(("http://", "https://")):
        logger.warning("[n8n_bridge] Invalid webhook URL: %s", url)
        return False

    payload_str = json.dumps(payload_dict, sort_keys=True)
    timestamp = str(int(time.time()))
    signature = generate_hmac_signature(secret or "cosa-n8n-default-secret", payload_str, timestamp)

    headers = {
        "Content-Type": "application/json",
        "X-COSA-Signature": signature,
        "X-COSA-Timestamp": timestamp,
        "User-Agent": "COSA-Execution-Runtime/13.2",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, content=payload_str, headers=headers)
            if resp.status_code in [200, 201, 202, 204]:
                logger.info("[n8n_bridge] Dispatched signed payload to %s (status %s)", url, resp.status_code)
                return True
            else:
                logger.warning("[n8n_bridge] Webhook returned status %s: %s", resp.status_code, resp.text[:200])
                return False
    except Exception as exc:
        logger.error("[n8n_bridge] Error sending signed payload to %s: %s", url, exc)
        return False


async def dispatch_job_callback(
    callback_url: str,
    webhook_secret: str,
    job_result: ExecutionJobResult,
    timeout: float = 10.0,
) -> bool:
    """Send an authenticated HTTP POST callback with job execution results to n8n / external webhook."""
    payload_dict = {
        "event": "execution_job_completed",
        "job_id": job_result.job_id,
        "workspace_id": str(job_result.workspace_id),
        "status": job_result.status.value,
        "provider": job_result.provider,
        "artifacts": [a.model_dump() for a in job_result.artifacts],
        "error_code": job_result.error_code,
        "error_message": job_result.error_message,
        "completed_at": job_result.completed_at.isoformat() if job_result.completed_at else None,
    }
    return await _send_signed_payload(
        url=callback_url,
        secret=webhook_secret,
        payload_dict=payload_dict,
        timeout=timeout,
    )


async def dispatch_outbound_action(
    webhook_url: Optional[str],
    webhook_secret: Optional[str],
    action_type: str,
    payload: Dict[str, Any],
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Generic HMAC-signed outbound action dispatcher for n8n domain capabilities."""
    correlation_id = payload.get("correlation_id") or str(generate_snowflake_id())
    payload_dict = {
        "action_type": action_type,
        "correlation_id": correlation_id,
        "timestamp": int(time.time()),
        "payload": payload,
    }

    if webhook_url:
        delivered = await _send_signed_payload(
            url=webhook_url,
            secret=webhook_secret,
            payload_dict=payload_dict,
            timeout=timeout,
        )
        return {
            "success": delivered,
            "action_type": action_type,
            "correlation_id": correlation_id,
            "status": "delivered_to_n8n" if delivered else "delivery_failed",
            "delivered": delivered,
        }

    return {
        "success": True,
        "action_type": action_type,
        "correlation_id": correlation_id,
        "status": "mock_delivered",
        "delivered": False,
        "note": "Webhook URL not configured, processed in simulated mode",
    }
