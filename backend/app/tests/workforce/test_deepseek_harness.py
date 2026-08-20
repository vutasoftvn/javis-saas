import pytest
from app.workforce.adapters.deepseek_harness import DeepSeekHarnessAdapter

@pytest.mark.asyncio
async def test_dsh_cosa_governed_mode_rejects_unregistered_tools():
    """Harness in cosa_governed mode must reject any tool not explicitly provided via scope."""
    adapter = DeepSeekHarnessAdapter(mode="cosa_governed")
    
    # Giả lập payload từ DSH yêu cầu gọi tool "unknown_native_tool"
    payload = {
        "jsonrpc": "2.0",
        "method": "call_tool",
        "params": {"name": "unknown_native_tool", "args": {}},
        "id": 1
    }
    
    # scope trống, không chứa tool nào
    scope = {"allowed_tools": ["ext.cosa.registered_tool"]}
    
    response = await adapter.handle_rpc_request(scope, payload)
    assert response["error"]["code"] == -32601 # Method not found / Unauthorized
    assert "not registered" in response["error"]["message"]

@pytest.mark.asyncio
async def test_dsh_cosa_governed_mode_routes_to_invocation_service():
    """Harness must route authorized tool calls to ToolInvocationService."""
    adapter = DeepSeekHarnessAdapter(mode="cosa_governed")
    
    payload = {
        "jsonrpc": "2.0",
        "method": "call_tool",
        "params": {"name": "ext.cosa.registered_tool", "args": {"foo": "bar"}},
        "id": 2
    }
    
    scope = {"allowed_tools": ["ext.cosa.registered_tool"]}
    
    response = await adapter.handle_rpc_request(scope, payload)
    assert "result" in response
    assert response["result"] == "mock_invocation_success"

@pytest.mark.asyncio
async def test_dsh_isolated_coding_mode_rejects_production_tools():
    """Harness in isolated_coding mode must reject production tools."""
    adapter = DeepSeekHarnessAdapter(mode="isolated_coding")
    
    payload = {
        "jsonrpc": "2.0",
        "method": "call_tool",
        "params": {"name": "ext.cosa.production_tool", "args": {}},
        "id": 3
    }
    
    scope = {"allowed_tools": ["ext.cosa.production_tool"]}
    
    response = await adapter.handle_rpc_request(scope, payload)
    assert response["error"]["code"] == -32603
    assert "forbidden" in response["error"]["message"]

@pytest.mark.asyncio
async def test_dsh_isolated_coding_mode_allows_sandbox_tools():
    """Harness in isolated_coding mode allows native sandbox tools."""
    adapter = DeepSeekHarnessAdapter(mode="isolated_coding")
    
    payload = {
        "jsonrpc": "2.0",
        "method": "call_tool",
        "params": {"name": "bash", "args": {"cmd": "ls"}},
        "id": 4
    }
    
    scope = {}
    
    response = await adapter.handle_rpc_request(scope, payload)
    assert response["result"] == "mock_sandbox_execution"
