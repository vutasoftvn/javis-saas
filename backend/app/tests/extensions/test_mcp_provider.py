import pytest
from app.workforce.extensions.mcp_provider import MCPProvider
from app.workforce.extensions.contracts import ProviderUnavailableError
from app.workforce.agents.runtime.execution_scope import ExecutionScope
import httpx

@pytest.fixture
def scope():
    return ExecutionScope(
        workspace_id=101,
        company_id=101,
        principal_user_id=1,
        principal_member_id=1,
        principal_role="owner",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=()
    )

@pytest.fixture
def config():
    return {"endpoint": "https://mcp.test/rpc", "extension_id": "com.cosa.mcp.github"}

@pytest.mark.asyncio
async def test_mcp_provider_discovers_tools_after_initialize(monkeypatch, scope, config):
    from unittest.mock import AsyncMock, MagicMock
    
    mock_client = AsyncMock()
    
    async def mock_post(url, json=None, **kwargs):
        body = json or {}
        method = body.get("method")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        if method == "initialize":
            mock_response.json.return_value = {"jsonrpc":"2.0","id":body["id"],"result":{"protocolVersion":"2025-03-26"}}
        elif method == "notifications/initialized":
            mock_response.json.return_value = {"jsonrpc":"2.0"}
        elif method == "tools/list":
            mock_response.json.return_value = {"jsonrpc":"2.0","id":body.get("id"),"result":{"tools":[{"name":"search","inputSchema":{"type":"object"}}]}}
        else:
            mock_response.status_code = 400
            
        return mock_response
        
    mock_client.post.side_effect = mock_post
    
    mock_client_ctx = MagicMock()
    mock_client_ctx.__aenter__.return_value = mock_client
    mock_client_ctx.__aexit__.return_value = False
    
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: mock_client_ctx)
    
    provider = MCPProvider()
    tools = await provider.discover(scope, config)
    
    assert len(tools) == 1
    assert tools[0].capability_id == "com.cosa.mcp.github:search"
    assert tools[0].name == "search"
    assert tools[0].input_schema == {"type":"object"}

@pytest.mark.asyncio
async def test_mcp_error_is_provider_failure_not_fake_success(monkeypatch, scope, config):
    from unittest.mock import AsyncMock, MagicMock
    
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_client.post.return_value = mock_response
    
    mock_client_ctx = MagicMock()
    mock_client_ctx.__aenter__.return_value = mock_client
    mock_client_ctx.__aexit__.return_value = False
    
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: mock_client_ctx)
    
    provider = MCPProvider()
    with pytest.raises(ProviderUnavailableError):
        await provider.discover(scope, config)
