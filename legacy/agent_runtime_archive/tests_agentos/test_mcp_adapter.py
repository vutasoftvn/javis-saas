from __future__ import annotations

import httpx
import pytest

from agentos.tools.mcp_adapter import (
    MCPServerError,
    MCPServerUnavailableError,
    MCPToolAdapter,
    make_mcp_tool_spec,
)
from agentos.tools.registry import ToolRegistry

_RealAsyncClient = httpx.AsyncClient


def _mock_client(handler):
    return lambda *a, **kw: _RealAsyncClient(*a, transport=httpx.MockTransport(handler), **kw)


@pytest.mark.asyncio
async def test_call_tool_returns_the_result_field(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content)
        assert body["method"] == "tools/call"
        assert body["params"]["name"] == "web_search"
        assert body["params"]["arguments"] == {"query": "widgets"}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": "1", "result": {"hits": ["a", "b"]}})

    monkeypatch.setattr(httpx, "AsyncClient", _mock_client(handler))
    adapter = MCPToolAdapter("https://mcp.example.test/mcp")

    result = await adapter.call_tool("web_search", {"query": "widgets"})

    assert result == {"hits": ["a", "b"]}


@pytest.mark.asyncio
async def test_call_tool_raises_on_json_rpc_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": "1", "error": {"code": -1, "message": "boom"}})

    monkeypatch.setattr(httpx, "AsyncClient", _mock_client(handler))
    adapter = MCPToolAdapter("https://mcp.example.test/mcp")

    with pytest.raises(MCPServerError, match="boom"):
        await adapter.call_tool("web_search", {})


@pytest.mark.asyncio
async def test_call_tool_raises_on_non_200_status(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    monkeypatch.setattr(httpx, "AsyncClient", _mock_client(handler))
    adapter = MCPToolAdapter("https://mcp.example.test/mcp")

    with pytest.raises(MCPServerUnavailableError, match="500"):
        await adapter.call_tool("web_search", {})


@pytest.mark.asyncio
async def test_call_tool_raises_on_connection_failure(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    monkeypatch.setattr(httpx, "AsyncClient", _mock_client(handler))
    adapter = MCPToolAdapter("https://mcp.example.test/mcp")

    with pytest.raises(MCPServerUnavailableError):
        await adapter.call_tool("web_search", {})


@pytest.mark.asyncio
async def test_make_mcp_tool_spec_registers_and_invokes_through_tool_registry(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": "1", "result": {"ok": True}})

    monkeypatch.setattr(httpx, "AsyncClient", _mock_client(handler))
    adapter = MCPToolAdapter("https://mcp.example.test/mcp")
    spec = make_mcp_tool_spec("web_search", "Search the web", adapter, permission_class="READ_NETWORK")

    registry = ToolRegistry()
    registry.register(spec)

    result = await registry.invoke("web_search", {"query": "widgets"})

    assert result == {"ok": True}
    assert registry.get("web_search").permission_class == "READ_NETWORK"


@pytest.mark.asyncio
async def test_make_mcp_tool_spec_uses_mcp_tool_name_override(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": "1", "result": {}})

    monkeypatch.setattr(httpx, "AsyncClient", _mock_client(handler))
    adapter = MCPToolAdapter("https://mcp.example.test/mcp")
    spec = make_mcp_tool_spec("search", "Search", adapter, mcp_tool_name="web.search")

    registry = ToolRegistry()
    registry.register(spec)
    await registry.invoke("search", {})

    assert captured["body"]["params"]["name"] == "web.search"
