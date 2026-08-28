"""Sink cho business event phát từ `apps/cosa` — POST envelope tới endpoint
nội bộ của `services/company` để append vào `integration.event_outbox` (outbox
duy nhất, P0). `apps/cosa` không ghi trực tiếp bảng đó vì dùng DB khác.
"""
from __future__ import annotations

import logging
import os

import httpx

__all__ = ["CompanyOutboxEventSink"]

logger = logging.getLogger("cosa.events.sink")


class CompanyOutboxEventSink:
    def __init__(
        self,
        base_url: str | None = None,
        service_token: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._url = (base_url or os.environ.get("COMPANY_SERVICE_URL", "http://127.0.0.1:4000")).rstrip("/")
        self._token = service_token or os.environ.get("COSA_WORKER_SERVICE_TOKEN", "")
        self._client = client

    async def __call__(self, envelope: dict) -> None:
        client = self._client or httpx.AsyncClient(timeout=5.0)
        try:
            resp = await client.post(
                f"{self._url}/events/internal/knowledge-published",
                json={"envelope": envelope},
                headers={"X-Service-Token": self._token},
            )
            resp.raise_for_status()
        finally:
            if self._client is None:
                await client.aclose()
        logger.info(
            "emitted %s source=%s", envelope["eventType"], envelope["payload"].get("sourceId")
        )
