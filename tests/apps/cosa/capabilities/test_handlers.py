"""Unit tests for COSA capability handlers (apps/cosa/capabilities/*).

Uses httpx.MockTransport to isolate tests from actual external network services.
Asserts:
- Finance handlers: correct endpoint routes, idempotency keys, parameters.
- Marketing handlers: optimistic locking (expected_revision), asset refs, experiment specs.
- Operations handlers: task listing and task reading query params.
- Web search handler: empty query fast-path, quota accounting, provider delegation.
"""

from __future__ import annotations

import json

import httpx
import pytest
from agent_core.capabilities.web_search.budget import InMemoryWebSearchBudgetStore
from agent_core.capabilities.web_search.provider import (
    WebSearchProvider,
    WebSearchResult,
)

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.finance_write import (
    create_finance_payout_execute_handler,
    create_finance_transaction_record_handler,
)
from apps.cosa.capabilities.marketing_write import (
    create_campaign_asset_write_handler,
    create_experiment_write_handler,
    create_marketing_context_write_handler,
)
from apps.cosa.capabilities.operations_read import (
    create_operations_task_list_handler,
    create_operations_task_read_handler,
)
from apps.cosa.capabilities.web_search import (
    create_web_search_handler,
)


def _make_mock_client(handler_fn) -> CompanyServiceClient:
    transport = httpx.MockTransport(handler_fn)
    client = CompanyServiceClient(base_url="http://mock-company-service")

    # Override _request to use MockTransport directly
    async def _mock_request(
        method: str,
        path: str,
        params: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        url = f"{client.base_url}/{path.lstrip('/')}"
        req_headers = dict(client.default_headers)
        if headers:
            req_headers.update(headers)
        async with httpx.AsyncClient(transport=transport) as hc:
            resp = await hc.request(method, url, params=params, json=json, headers=req_headers)
            return resp.json()

    client._request = _mock_request
    return client


# --- 1. Finance Capabilities ---


@pytest.mark.asyncio
async def test_finance_payout_execute_handler():
    """finance.payout.execute handler posts payout with idempotency_key."""
    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200, json={"payout_id": "po_123", "status": "executed", "transaction_ref": "tx_456"}
        )

    client = _make_mock_client(mock_handler)
    handler = create_finance_payout_execute_handler(client)

    payload = {
        "workspace_id": 42,
        "amount": 1500.0,
        "vendor": "Acme Supplies",
        "currency": "USD",
        "description": "Office hardware",
        "idempotency_key": "idem_payout_42",
    }
    ctx = {"workspace_id": 42}

    res = await handler(payload, ctx)

    assert res["status"] == "executed"
    assert res["payout_id"] == "po_123"
    assert len(captured_requests) == 1

    req = captured_requests[0]
    assert req.method == "POST"
    assert "/finance-legal/payouts" in str(req.url)

    body = json.loads(req.content)
    assert body["workspaceId"] == 42
    assert body["amount"] == 1500.0
    assert body["vendor"] == "Acme Supplies"
    assert body["idempotencyKey"] == "idem_payout_42"


@pytest.mark.asyncio
async def test_finance_transaction_record_handler():
    """finance.transaction.record handler posts transaction to ledger."""
    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"transaction_id": "tx_789", "status": "recorded"})

    client = _make_mock_client(mock_handler)
    handler = create_finance_transaction_record_handler(client)

    payload = {
        "workspace_id": 10,
        "amount": 250.0,
        "account_id": "acc_main",
        "type": "debit",
        "description": "SaaS Subscription",
    }
    ctx = {"workspace_id": 10}

    res = await handler(payload, ctx)

    assert res["status"] == "recorded"
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.method == "POST"
    assert "/finance-legal/transactions" in str(req.url)
    body = json.loads(req.content)
    assert body["accountId"] == "acc_main"
    assert body["type"] == "debit"


# --- 2. Marketing Capabilities ---


@pytest.mark.asyncio
async def test_marketing_context_write_handler_optimistic_locking():
    """commercial.marketing_context.write validates expected_revision and sends patch."""
    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"id": "mc_1", "revision": 3, "status": "updated"})

    client = _make_mock_client(mock_handler)
    handler = create_marketing_context_write_handler(client)

    # Missing expected_revision raises ValueError
    with pytest.raises(ValueError, match="expected_revision"):
        await handler({"workspace_id": "ws_1", "product_marketing": {}}, {"workspace_id": "ws_1"})

    payload = {
        "workspace_id": "ws_1",
        "expected_revision": 2,
        "product_marketing": {"positioning": "AI SaaS"},
        "change_reason": "Updated ICP positioning",
    }
    res = await handler(payload, {"workspace_id": "ws_1"})

    assert res["status"] == "updated"
    assert res["revision"] == 3
    assert len(captured_requests) == 1

    req = captured_requests[0]
    assert req.method == "PATCH"
    assert "/commercial/marketing-context" in str(req.url)
    assert req.headers["X-Workspace-Id"] == "ws_1"


@pytest.mark.asyncio
async def test_campaign_asset_and_experiment_write_handlers():
    """commercial.campaign_asset.write and experiment.write produce valid response descriptors."""
    client = CompanyServiceClient()

    asset_handler = create_campaign_asset_write_handler(client)
    asset_res = await asset_handler(
        {"asset_name": "Landing Copy", "asset_type": "copy", "content": "# Hero"},
        {"workspace_id": "ws_alpha"},
    )
    assert asset_res["status"] == "saved"
    assert asset_res["asset_name"] == "Landing Copy"
    assert "artifact://ws_alpha/campaign-assets/" in asset_res["object_ref"]

    exp_handler = create_experiment_write_handler(client)
    exp_res = await exp_handler(
        {"hypothesis": "Shorter CTA increases conversions", "metric": "CTR", "target_value": 0.05},
        {"workspace_id": "ws_alpha"},
    )
    assert exp_res["status"] == "pending_approval"
    assert exp_res["hypothesis"] == "Shorter CTA increases conversions"


# --- 3. Operations Capabilities ---


@pytest.mark.asyncio
async def test_operations_task_handlers():
    """operations.task.list and operations.task.read query endpoints correctly."""
    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        if "/operations/tasks/" in str(request.url):
            return httpx.Response(200, json={"task": {"id": 101, "title": "Onboard Client"}})
        return httpx.Response(200, json={"tasks": [{"id": 101}], "total": 1})

    client = _make_mock_client(mock_handler)
    list_handler = create_operations_task_list_handler(client)
    read_handler = create_operations_task_read_handler(client)

    # List tasks
    list_res = await list_handler(
        {"workspace_id": 5, "status": "open", "limit": 10}, {"workspace_id": 5}
    )
    assert list_res["total"] == 1
    assert captured_requests[0].method == "GET"
    assert "workspaceId=5" in str(captured_requests[0].url)
    assert "status=open" in str(captured_requests[0].url)

    # Read task
    read_res = await read_handler({"task_id": 101}, {"workspace_id": 5})
    assert read_res["task"]["id"] == 101
    assert "/operations/tasks/101" in str(captured_requests[1].url)


# --- 4. Web Search Capability ---


class MockSearchProvider(WebSearchProvider):
    provider_name = "mock_tavily"

    def __init__(self, results: list[WebSearchResult] | None = None):
        self._results = results or []

    async def search(self, query: str, **kwargs) -> list[WebSearchResult]:
        return self._results


@pytest.mark.asyncio
async def test_web_search_handler_empty_and_normal_query():
    """web.search fast-paths on empty query and consumes budget on valid search."""
    budget_store = InMemoryWebSearchBudgetStore()
    provider = MockSearchProvider(
        results=[
            WebSearchResult(
                url="https://example.com/item",
                title="Example Item",
                snippet="Snippet text",
            )
        ]
    )
    handler = create_web_search_handler(provider=provider, budget_store=budget_store)

    # 1. Empty query -> fast path without error
    empty_res = await handler({"query": ""}, {"workspace_id": "ws_search"})
    assert empty_res["results"] == []
    assert empty_res["query"] == ""

    # 2. Valid query -> executes search & tracks cost
    res = await handler(
        {"query": "AI SaaS trends 2026", "max_results": 3}, {"workspace_id": "ws_search"}
    )
    assert len(res["results"]) == 1
    assert res["results"][0]["title"] == "Example Item"
    assert res["query"] == "AI SaaS trends 2026"

    from datetime import UTC, datetime

    today_str = datetime.now(UTC).date().isoformat()
    record = budget_store._usage.get(("ws_search", today_str))
    assert record is not None
    assert record["query_count"] == 1
    assert record["cost_accumulated"] == 1.0
