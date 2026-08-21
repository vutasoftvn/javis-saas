from typing import Dict, Any, Optional
import httpx
from workforce.identity.context import ExecutionContext
from workforce.tools.base import BaseToolAdapter


class MCPToolAdapter(BaseToolAdapter):
    """Adapter kết nối với Model Context Protocol (MCP) Server để gọi các công cụ ngoại vi."""

    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout

    async def execute(
        self,
        context: ExecutionContext,
        tool_key: str,
        args: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        config = config or {}
        server_url = config.get("server_url") or "http://localhost:8000/mcp"
        mcp_tool_name = config.get("tool_name") or tool_key

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": mcp_tool_name,
                "arguments": args,
            },
            "id": context.trace_id,
        }

        try:
            async with httpx.AsyncClient(timeout=self.default_timeout) as client:
                headers = {
                    "X-Workspace-Id": str(context.workspace_id),
                    "X-Agent-Id": str(context.agent_id),
                }
                # Tạm thời gọi JSON-RPC hoặc giả lập nếu endpoint chưa sẵn sàng
                response = await client.post(server_url, json=payload, headers=headers)
                if response.status_code == 200:
                    resp_json = response.json()
                    
                    if "error" in resp_json:
                        from workforce.extensions.contracts import ProviderProtocolError
                        raise ProviderProtocolError(f"MCP server error: {resp_json['error']}")
                        
                    return {
                        "status": "success",
                        "transport": "mcp",
                        "tool": tool_key,
                        "data": resp_json.get("result", resp_json)
                    }
                else:
                    from workforce.extensions.contracts import ProviderUnavailableError
                    raise ProviderUnavailableError(f"MCP server returned HTTP {response.status_code}")
        except httpx.RequestError as exc:
            from workforce.extensions.contracts import ProviderUnavailableError
            raise ProviderUnavailableError(f"MCP request failed: {exc}")
