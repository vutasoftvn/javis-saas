from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from agent.workforce.repository import InMemoryWorkforceRepository
from apps.cosa.events.runtime_signal import AgentRuntimeSignalPublisher


@pytest.mark.asyncio
async def test_signal_delivery_success() -> None:
    repo = InMemoryWorkforceRepository()
    now = datetime.now(UTC)
    sig = await repo.enqueue_runtime_signal(
        workspace_id="ws_1001",
        source_kind="run",
        source_id="run_123",
        sequence=1,
        state="COMPLETED",
        observed_at=now,
    )

    received_requests: list[dict[str, Any]] = []

    async def _handler(request: httpx.Request) -> httpx.Response:
        import json
        body = json.loads(request.content)
        received_requests.append(body)
        return httpx.Response(200, json={"stored": True})

    mock_transport = httpx.MockTransport(_handler)
    async with httpx.AsyncClient(transport=mock_transport, base_url="http://test-company") as client:
        publisher = AgentRuntimeSignalPublisher(
            repository=repo,
            company_url="http://test-company",
            service_token="test-token",
            http_client=client,
        )

        delivered = await publisher.deliver_due()
        assert delivered == 1

        # Check repository state
        signals = await repo.claim_pending_signals()
        assert len(signals) == 0  # no longer pending

        assert len(received_requests) == 1
        assert received_requests[0]["signal"]["workspaceId"] == "ws_1001"
        assert received_requests[0]["signal"]["sourceId"] == "run_123"
        assert received_requests[0]["signal"]["state"] == "COMPLETED"


@pytest.mark.asyncio
async def test_signal_delivery_failure_retry_backoff() -> None:
    repo = InMemoryWorkforceRepository()
    now = datetime.now(UTC)
    sig = await repo.enqueue_runtime_signal(
        workspace_id="ws_1001",
        source_kind="approval",
        source_id="appr_456",
        sequence=1,
        state="APPROVED",
        observed_at=now,
    )

    async def _failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "Database error"})

    mock_transport = httpx.MockTransport(_failing_handler)
    async with httpx.AsyncClient(transport=mock_transport, base_url="http://test-company") as client:
        publisher = AgentRuntimeSignalPublisher(
            repository=repo,
            company_url="http://test-company",
            service_token="test-token",
            http_client=client,
        )

        delivered = await publisher.deliver_due()
        assert delivered == 0

        # The signal is now in backoff so claim_pending_signals(now) won't return it until next_attempt_at
        signals = await repo.claim_pending_signals()
        assert len(signals) == 0
