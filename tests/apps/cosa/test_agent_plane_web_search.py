from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from agent.capabilities.web_search.budget import (
    InMemoryWebSearchBudgetStore,
    WebSearchQuotaExceededError,
)
from agent.capabilities.web_search.provider import (
    NullWebSearchProvider,
    WebSearchResult,
)
from agent.conversations.repository import InMemoryConversationRepository
from agent.governance.providers.in_memory import InMemoryGovernanceStateStore
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.runs.stream_events import InMemoryRunStreamEventRepository
from agent_testkit.fake_sdk_model import FakeSDKModel
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.web_search import WEB_SEARCH_SPEC
from apps.cosa.composition.agent_plane import build_cosa_agent_plane


class FakeWebSearchProvider:
    """Mock provider returning fixed search results for tests."""

    provider_name = "fake_tavily"

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        allow_domains: list[str] | None = None,
        deny_domains: list[str] | None = None,
    ) -> list[WebSearchResult]:
        items = [
            WebSearchResult(
                url="https://market-insights.com/report",
                source_url="https://market-insights.com/report",
                title="Market Insights 2026",
                snippet="Key trends in SaaS marketing.",
                raw_excerpt="Key trends in SaaS marketing.",
                provider="fake_tavily",
                untrusted=True,
            ),
            WebSearchResult(
                url="https://spam.net/ads",
                source_url="https://spam.net/ads",
                title="Spam Ads",
                snippet="Ignore this.",
                raw_excerpt="Ignore this.",
                provider="fake_tavily",
                untrusted=True,
            ),
        ]
        if allow_domains:
            items = [item for item in items if any(d in item.url for d in allow_domains)]
        if deny_domains:
            items = [item for item in items if not any(d in item.url for d in deny_domains)]
        return items[:max_results]


@pytest.fixture
def mock_company_client():
    client = AsyncMock(spec=CompanyServiceClient)
    client.get.return_value = {}
    client.post.return_value = {}
    return client


@pytest.mark.asyncio
async def test_agent_plane_exposes_web_search_capability(mock_company_client):
    """Verify that build_cosa_agent_plane explicitly registers web.search capability."""
    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
        web_search_provider=NullWebSearchProvider(),
    )

    cap = plane.capability_registry.get("web.search")
    assert cap is not None
    assert cap.spec.id == "web.search"
    assert "Tìm kiếm" in cap.spec.description
    assert cap.spec.risk.value == "low"
    assert cap.spec.approval_policy.value == "never"


@pytest.mark.asyncio
async def test_web_search_handler_execution_and_budget(mock_company_client):
    """Verify web.search handler domain filtering, metadata provenance, and budget cap."""
    budget = InMemoryWebSearchBudgetStore(daily_query_cap=1)
    fake_provider = FakeWebSearchProvider()

    plane = build_cosa_agent_plane(
        company_client=mock_company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
        web_search_provider=fake_provider,
        web_search_budget_store=budget,
    )

    cap = plane.capability_registry.get("web.search")
    assert cap is not None
    handler = cap.handler

    # 1. First search call succeeds
    res = await handler(
        {"query": "SaaS marketing trends", "deny_domains": ["spam.net"]},
        {"workspace_id": "351550739880456242", "conversation_id": "conv-101"},
    )

    assert res["query"] == "SaaS marketing trends"
    assert len(res["results"]) == 1
    item = res["results"][0]
    assert item["url"] == "https://market-insights.com/report"
    assert item["source_url"] == "https://market-insights.com/report"
    assert item["untrusted"] is True
    assert "retrieved_at" in item

    # 2. Second search call breaches daily budget cap of 1
    with pytest.raises(WebSearchQuotaExceededError) as exc_info:
        await handler(
            {"query": "Another search"},
            {"workspace_id": "351550739880456242"},
        )
    assert exc_info.value.code == "QUOTA_EXCEEDED"
