from __future__ import annotations

import json
from datetime import datetime, timezone
import httpx
import pytest
from agent_core.capabilities.web_search.budget import (
    InMemoryWebSearchBudgetStore,
    WebSearchQuotaExceededError,
)
from agent_core.capabilities.web_search.provider import (
    NullWebSearchProvider,
    build_web_search_provider,
    sanitize_excerpt,
)
from agent_core.capabilities.web_search.tavily import TavilyWebSearchProvider

MOCK_TAVILY_RESPONSE = {
    "query": "B2B SaaS pricing benchmarks 2026",
    "results": [
        {
            "title": "B2B SaaS Pricing Trends 2026",
            "url": "https://saas-metrics.com/pricing-2026",
            "content": "Comprehensive guide to SaaS pricing models and ACV benchmarks in 2026.",
            "raw_content": "<script>alert('malicious')</script><p>Comprehensive guide to SaaS pricing models and ACV benchmarks in 2026.</p><style>.hidden{display:none}</style>",
            "published_date": "2026-01-15T10:00:00Z",
            "score": 0.95,
        },
        {
            "title": "Spam Competitor Ads",
            "url": "https://spammy-ads.com/ad",
            "content": "Buy cheap software.",
            "raw_content": "Buy cheap software.",
            "published_date": "2026-02-01T12:00:00Z",
            "score": 0.3,
        },
        {
            "title": "Forbes Tech Trends",
            "url": "https://www.forbes.com/tech/enterprise-ai",
            "content": "Enterprise AI adoption is accelerating.",
            "raw_content": "Enterprise AI adoption is accelerating.",
            "published_date": "2026-02-10T14:00:00Z",
            "score": 0.88,
        },
    ],
}


@pytest.mark.asyncio
async def test_null_web_search_provider():
    provider = NullWebSearchProvider()
    results = await provider.search("any query", max_results=10)
    assert results == []


def test_sanitize_excerpt():
    raw_html = "<script>bad()</script><div>Hello <b>World</b></div><style>css{}</style>"
    cleaned = sanitize_excerpt(raw_html)
    assert "bad()" not in cleaned
    assert "css{}" not in cleaned
    assert "Hello World" in cleaned


@pytest.mark.asyncio
async def test_tavily_provider_mock_search():
    def custom_transport(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/search" in str(request.url)
        body = json.loads(request.read())
        assert body["query"] == "B2B SaaS pricing benchmarks 2026"
        assert body["api_key"] == "test-key"
        return httpx.Response(200, json=MOCK_TAVILY_RESPONSE)

    client = httpx.AsyncClient(transport=httpx.MockTransport(custom_transport))
    provider = TavilyWebSearchProvider(api_key="test-key", client=client)

    results = await provider.search("B2B SaaS pricing benchmarks 2026", max_results=5)
    assert len(results) == 3
    first = results[0]
    assert first.title == "B2B SaaS Pricing Trends 2026"
    assert first.url == "https://saas-metrics.com/pricing-2026"
    assert first.source_url == "https://saas-metrics.com/pricing-2026"
    assert first.untrusted is True
    assert first.provider == "tavily"
    assert "alert('malicious')" not in first.raw_excerpt
    assert "Comprehensive guide" in first.raw_excerpt
    assert first.published_at == datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_tavily_provider_domain_filtering():
    def custom_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=MOCK_TAVILY_RESPONSE)

    client = httpx.AsyncClient(transport=httpx.MockTransport(custom_transport))
    provider = TavilyWebSearchProvider(api_key="test-key", client=client)

    # Allow only saas-metrics.com
    results_allowed = await provider.search(
        "query",
        allow_domains=["saas-metrics.com"],
        max_results=5,
    )
    assert len(results_allowed) == 1
    assert results_allowed[0].url == "https://saas-metrics.com/pricing-2026"

    # Deny spammy-ads.com
    results_denied = await provider.search(
        "query",
        deny_domains=["spammy-ads.com"],
        max_results=5,
    )
    assert len(results_denied) == 2
    assert all("spammy-ads.com" not in r.url for r in results_denied)


@pytest.mark.asyncio
async def test_tavily_provider_retry_on_429():
    call_count = 0

    def custom_transport(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"})
        return httpx.Response(200, json=MOCK_TAVILY_RESPONSE)

    client = httpx.AsyncClient(transport=httpx.MockTransport(custom_transport))
    provider = TavilyWebSearchProvider(api_key="test-key", client=client, max_retries=3)

    results = await provider.search("query", max_results=5)
    assert call_count == 2
    assert len(results) == 3


@pytest.mark.asyncio
async def test_tavily_provider_timeout():
    def custom_transport(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out")

    client = httpx.AsyncClient(transport=httpx.MockTransport(custom_transport))
    provider = TavilyWebSearchProvider(api_key="test-key", client=client, timeout=0.1, max_retries=1)

    with pytest.raises(RuntimeError) as exc_info:
        await provider.search("query")
    assert "timed out" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_budget_store_quota_exceeded():
    store = InMemoryWebSearchBudgetStore(daily_query_cap=2, daily_cost_cap=5.0)

    # 1st query OK
    ok1 = await store.check_and_consume("ws-1", cost=1.0)
    assert ok1 is True

    # 2nd query OK
    ok2 = await store.check_and_consume("ws-1", cost=1.0)
    assert ok2 is True

    # 3rd query exceeds limit
    with pytest.raises(WebSearchQuotaExceededError) as exc_info:
        await store.check_and_consume("ws-1", cost=1.0)
    assert exc_info.value.code == "QUOTA_EXCEEDED"
    assert exc_info.value.workspace_id == "ws-1"


def test_build_web_search_provider_env_dispatch(monkeypatch):
    # Null provider
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "null")
    prov_null = build_web_search_provider()
    assert isinstance(prov_null, NullWebSearchProvider)

    # Tavily provider in dev without key falls back to null with warning
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "tavily")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    prov_dev_fallback = build_web_search_provider()
    assert isinstance(prov_dev_fallback, NullWebSearchProvider)

    # Tavily provider in prod without key raises RuntimeError
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        build_web_search_provider()

    # Tavily provider with key
    monkeypatch.setenv("TAVILY_API_KEY", "real-mock-key")
    prov_tavily = build_web_search_provider()
    assert isinstance(prov_tavily, TavilyWebSearchProvider)
