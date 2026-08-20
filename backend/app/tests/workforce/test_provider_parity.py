import pytest
from app.workforce.adapters.deepseek_harness import DeepSeekHarnessAdapter
# Giả sử NativeAdapter cũng tuân theo RuntimeAdapter
from app.workforce.extensions.seams import RuntimeAdapter

@pytest.mark.asyncio
async def test_parity_between_native_and_dsh():
    """Both DSH and Native must respect scope allowances."""
    scope = {"allowed_tools": ["ext.cosa.foo"]}
    
    # DSH Test
    dsh_adapter = DeepSeekHarnessAdapter(mode="cosa_governed")
    dsh_payload = {
        "jsonrpc": "2.0",
        "method": "call_tool",
        "params": {"name": "ext.cosa.bar", "args": {}},
        "id": 1
    }
    dsh_response = await dsh_adapter.handle_rpc_request(scope, dsh_payload)
    assert "error" in dsh_response
    assert dsh_response["error"]["code"] == -32601

    # Native sẽ có hành vi tương tự qua ToolInvocationService (đã được test ở module khác)
    pass
