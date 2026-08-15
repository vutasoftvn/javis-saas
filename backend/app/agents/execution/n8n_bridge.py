import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional
import httpx

from app.agents.execution.types import ExecutionJobResult

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


async def dispatch_job_callback(
    callback_url: str,
    webhook_secret: str,
    job_result: ExecutionJobResult,
    timeout: float = 10.0,
) -> bool:
    """Send an authenticated HTTP POST callback with job execution results to n8n / external webhook."""
    if not callback_url or not callback_url.startswith(("http://", "https://")):
        logger.warning("[ExecutionCallback] Invalid callback URL: %s", callback_url)
        return False

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

    payload_str = json.dumps(payload_dict, sort_keys=True)
    timestamp = str(int(time.time()))
    signature = generate_hmac_signature(webhook_secret or "cosa-n8n-default-secret", payload_str, timestamp)

    headers = {
        "Content-Type": "application/json",
        "X-COSA-Signature": signature,
        "X-COSA-Timestamp": timestamp,
        "User-Agent": "COSA-Execution-Runtime/13.2",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(callback_url, content=payload_str, headers=headers)
            if resp.status_code in [200, 201, 202, 204]:
                logger.info(
                    "[ExecutionCallback] Successfully dispatched callback for job %s to %s (status %s)",
                    job_result.job_id,
                    callback_url,
                    resp.status_code,
                )
                return True
            else:
                logger.warning(
                    "[ExecutionCallback] Callback for job %s returned status %s: %s",
                    job_result.job_id,
                    resp.status_code,
                    resp.text[:200],
                )
                return False
    except Exception as exc:
        logger.error(
            "[ExecutionCallback] Error sending callback for job %s to %s: %s",
            job_result.job_id,
            callback_url,
            exc,
        )
        return False
