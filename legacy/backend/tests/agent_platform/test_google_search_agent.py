import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from workforce.identity.context import ExecutionContext
from workforce.models import ToolDefinition
from workforce.gateway.gateway import AgentGateway
from workforce.registry.tool_registry import ToolRegistryService
from workforce.registry.defaults import DEFAULT_AGENT_MANIFESTS, DEFAULT_TOOL_MANIFESTS, DEFAULT_PROMPT_TEMPLATES
from workforce.routing.router import IntentRouter
from workforce.routing.deterministic import Intent
from workforce.tools.search.tools import (
    google_search_handler,
    web_extract_handler,
    _search_google_custom_search,
    _search_serpapi,
    _search_tavily,
    _search_duckduckgo_fallback,
)
from workforce.tools.auto_register import register_all_domain_tools


class TestGoogleSearchAgentAndTools:
    """Test suite cho Google Search Agent và các Search Tools."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def context(self):
        return ExecutionContext(
            workspace_id=1001,
            user_id=2001,
            session_id=3001,
            agent_id=5001,
            agent_key="google_search",
        )

    def test_agent_manifest_registered(self):
        """Kiểm tra manifest của google_search agent tồn tại."""
        agent_keys = [a["key"] for a in DEFAULT_AGENT_MANIFESTS]
        assert "google_search" in agent_keys

        manifest = next(a for a in DEFAULT_AGENT_MANIFESTS if a["key"] == "google_search")
        assert "google.search" in manifest["tools"]
        assert "web.extract" in manifest["tools"]
        assert manifest["risk_level"] == 0
        assert "google_search.system" in DEFAULT_PROMPT_TEMPLATES

    def test_tool_manifests_registered(self):
        """Kiểm tra manifest của google.search và web.extract tools."""
        tool_keys = [t["key"] for t in DEFAULT_TOOL_MANIFESTS]
        assert "google.search" in tool_keys
        assert "web.extract" in tool_keys

    @pytest.mark.parametrize("query,expected_agent", [
        ("Tìm kiếm google thông tin về AI Agent 2026", "google_search"),
        ("Google search xu hướng công nghệ mới", "google_search"),
        ("Tìm kiếm internet thị trường SaaS Việt Nam", "google_search"),
        ("Tra cứu trên mạng tin tức mới nhất về DeepSeek", "google_search"),
        ("Tìm thông tin trên mạng về đối thủ cạnh tranh", "google_search"),
    ])
    @pytest.mark.asyncio
    async def test_intent_router_routes_to_google_search(self, query: str, expected_agent: str):
        decision = await IntentRouter.route_message(query)
        assert decision.intent == Intent.RESEARCH
        assert decision.target_agent_key == expected_agent

    @pytest.mark.asyncio
    async def test_google_search_handler_missing_query(self, context, mock_db):
        res = await google_search_handler(context, {}, mock_db)
        assert res["status"] == "error"
        assert "Thiếu tham số 'query'" in res["message"]

    @pytest.mark.asyncio
    async def test_google_search_handler_mocked_custom_search(self, context, mock_db):
        mock_results = [
            {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1", "source": "example.com"},
            {"title": "Result 2", "url": "https://example.com/2", "snippet": "Snippet 2", "source": "example.com"},
        ]
        with patch.dict("os.environ", {"GOOGLE_SEARCH_API_KEY": "test_key", "GOOGLE_CSE_ID": "test_cx"}):
            with patch("workforce.tools.search.tools._search_google_custom_search", new=AsyncMock(return_value=mock_results)):
                res = await google_search_handler(context, {"query": "AI SaaS"}, mock_db)
                assert res["status"] == "success"
                assert res["provider"] == "google_custom_search"
                assert res["total_results"] == 2
                assert len(res["results"]) == 2

    @pytest.mark.asyncio
    async def test_google_search_handler_fallback_duckduckgo(self, context, mock_db):
        with patch.dict("os.environ", {}, clear=True):
            with patch("workforce.tools.search.tools._search_duckduckgo_fallback", new=AsyncMock(return_value=[
                {"title": "DDG Result", "url": "https://ddg.example.com", "snippet": "Text", "source": "ddg.example.com"}
            ])):
                res = await google_search_handler(context, {"query": "test query"}, mock_db)
                assert res["status"] == "success"
                assert res["provider"] == "web_crawler_fallback"
                assert len(res["results"]) == 1

    @pytest.mark.asyncio
    async def test_web_extract_handler_success(self, context, mock_db):
        fake_html = """
        <html>
            <head><title>Test Article Title</title></head>
            <body>
                <header><p>Header to ignore</p></header>
                <main>
                    <h1>Main Heading</h1>
                    <p>This is the important content of the website that needs to be extracted.</p>
                </main>
                <footer>Footer to ignore</footer>
            </body>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = fake_html

        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
            res = await web_extract_handler(context, {"url": "https://example.com/article"}, mock_db)
            assert res["status"] == "success"
            assert res["title"] == "Test Article Title"
            assert "Main Heading" in res["content"]
            assert "This is the important content" in res["content"]
            assert "Header to ignore" not in res["content"]
            assert "Footer to ignore" not in res["content"]

    @pytest.mark.asyncio
    async def test_gateway_executes_search_tools(self, context, mock_db):
        tool_reg = AsyncMock(spec=ToolRegistryService)
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=10, key="google.search", name="Google Search", transport="local", risk_level=0, requires_approval=False
        )

        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_res

        gateway = AgentGateway(db=mock_db, tool_registry=tool_reg)
        register_all_domain_tools(gateway, mock_db)

        with patch("workforce.tools.search.tools._search_duckduckgo_fallback", new=AsyncMock(return_value=[
            {"title": "Result", "url": "https://example.com", "snippet": "Snip", "source": "example.com"}
        ])):
            res = await gateway.execute(context, "google.search", {"query": "COSA OS"})
            assert res["status"] == "success"
            assert len(res["results"]) == 1
