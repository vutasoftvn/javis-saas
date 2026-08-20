import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from app.workforce.tools.transports.mcp_adapter import MCPToolAdapter
from app.workforce.extensions.contracts import ProviderProtocolError
from app.workforce.identity.context import ExecutionContext


@pytest.mark.asyncio
async def test_mcp_adapter_raises_provider_protocol_error_on_rpc_error(monkeypatch):
    """
    Regression test: mcp_adapter.py imports ProviderProtocolError from
    extensions.contracts, but until this fix that class was only defined in
    extensions.mcp_provider — the import raised ImportError the first time
    an MCP server actually returned a JSON-RPC error.
    """
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "error": {"code": -32000, "message": "boom"},
    }
    mock_client.post.return_value = mock_response

    mock_client_ctx = MagicMock()
    mock_client_ctx.__aenter__.return_value = mock_client
    mock_client_ctx.__aexit__.return_value = False
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: mock_client_ctx)

    adapter = MCPToolAdapter()
    context = ExecutionContext(
        workspace_id=1, user_id=None, session_id=None, agent_id=1, agent_key="agent-1"
    )

    with pytest.raises(ProviderProtocolError):
        await adapter.execute(context, "some_tool", {})
