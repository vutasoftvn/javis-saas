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
        received_requests.append(
            {
                "method": request.method,
                "path": request.url.path,
                "authorization": request.headers.get("authorization"),
                "content_type": request.headers.get("content-type"),
                "json": body,
            }
        )
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

        # Chứng minh đầy đủ HTTP envelope — method, path, auth, content-type, payload
        # (không chỉ body) để một URL sai hay thiếu internal-auth header bị bắt ngay.
        assert len(received_requests) == 1
        captured = received_requests[0]
        assert captured["method"] == "POST"
        assert captured["path"] == "/events/internal/agent-runtime-signal"
        assert captured["authorization"] == "Bearer test-token"
        assert captured["content_type"].startswith("application/json")
        assert captured["json"] == {
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


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 404])
async def test_signal_delivery_treats_auth_and_route_errors_as_failure(status_code: int) -> None:
    """401 (sai/thiếu service token) và 404 (route cũ) phải được tính là
    delivery failure, KHÔNG được ghi nhận là publication thành công."""
    repo = InMemoryWorkforceRepository()
    now = datetime.now(UTC)
    await repo.enqueue_runtime_signal(
        workspace_id="ws_1001",
        source_kind="run",
        source_id="run_123",
        sequence=1,
        state="COMPLETED",
        observed_at=now,
    )

    async def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "denied"})

    mock_transport = httpx.MockTransport(_handler)
    async with httpx.AsyncClient(transport=mock_transport, base_url="http://test-company") as client:
        publisher = AgentRuntimeSignalPublisher(
            repository=repo,
            company_url="http://test-company",
            service_token="test-token",
            http_client=client,
        )

        delivered = await publisher.deliver_due()
        assert delivered == 0
