"""Agent Runtime Signal Outbox Publisher to Company Service."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta

import httpx
from agent.workforce.repository import WorkforceRepository

logger = logging.getLogger(__name__)

__all__ = ["AgentRuntimeSignalPublisher"]


class AgentRuntimeSignalPublisher:
    def __init__(
        self,
        repository: WorkforceRepository,
        company_url: str | None = None,
        service_token: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._repository = repository
        self._company_url = (
            company_url or os.getenv("COMPANY_SERVICE_URL") or "http://127.0.0.1:4000"
        ).rstrip("/")
        self._service_token = service_token or os.getenv(
            "COSA_WORKER_SERVICE_TOKEN", "dev-worker-service-token"
        )
        self._http_client = http_client

    async def deliver_due(self, limit: int = 50, max_attempts: int = 10) -> int:
        signals = await self._repository.claim_pending_signals(
            limit=limit, max_attempts=max_attempts
        )
        if not signals:
            return 0

        delivered_count = 0
        client = self._http_client
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0)
            should_close = True

        try:
            for sig in signals:
                payload = {
                    "signal": {
                        "workspaceId": sig.workspace_id,
                        "sourceKind": sig.source_kind,
                        "sourceId": sig.source_id,
                        "sequence": sig.sequence,
                        "state": sig.state,
                        "observedAt": sig.observed_at.isoformat(),
                        "correlationId": sig.correlation_id,
                        "payloadHash": sig.payload_hash,
                    }
                }
                headers = {
                    "Authorization": f"Bearer {self._service_token}",
                    "Content-Type": "application/json",
                }

                try:
                    url = f"{self._company_url}/events/internal/agent-runtime-signal"
                    res = await client.post(url, json=payload, headers=headers)
                    if 200 <= res.status_code < 300:
                        await self._repository.mark_signal_delivered(sig.outbox_id)
                        delivered_count += 1
                    else:
                        logger.warning(
                            "Failed to deliver runtime signal %s (status %s): %s",
                            sig.outbox_id,
                            res.status_code,
                            res.text,
                        )
                        backoff = min(300, 2 ** (sig.attempt_count + 1))
                        next_attempt = datetime.now(UTC) + timedelta(seconds=backoff)
                        await self._repository.mark_signal_failed(sig.outbox_id, next_attempt)
                except Exception as exc:
                    logger.warning("Error delivering runtime signal %s: %s", sig.outbox_id, exc)
                    backoff = min(300, 2 ** (sig.attempt_count + 1))
                    next_attempt = datetime.now(UTC) + timedelta(seconds=backoff)
                    await self._repository.mark_signal_failed(sig.outbox_id, next_attempt)
        finally:
            if should_close:
                await client.aclose()

        return delivered_count
