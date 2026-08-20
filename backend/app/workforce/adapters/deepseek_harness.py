from typing import Any, Dict
from app.workforce.extensions.seams import ProviderHealth, ProviderResult

class DeepSeekHarnessAdapter:
    def __init__(self, mode: str = "cosa_governed"):
        self.mode = mode

    async def health(self, scope: Any) -> ProviderHealth:
        return ProviderHealth(status="ok")

    async def start(self, scope: Any, config: dict, input_data: dict) -> ProviderResult:
        return ProviderResult(status="started", result="dsh_run_1")

    async def stream(self, scope: Any, run_id: str):
        yield {"event": "started"}

    async def cancel(self, scope: Any, run_id: str) -> bool:
        return True

    async def ingest_artifacts(self, scope: Any, run_id: str) -> list:
        return []

    async def handle_rpc_request(self, scope: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Xử lý JSON-RPC request từ DeepSeek Harness.
        """
        if payload.get("method") == "call_tool":
            tool_name = payload["params"]["name"]
            
            if self.mode == "isolated_coding":
                # Chế độ cô lập: từ chối các công cụ production của COSA
                if tool_name.startswith("ext.cosa"):
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": "Production tools are forbidden in isolated_coding mode."
                        },
                        "id": payload.get("id")
                    }
                # Cho phép native sandbox tools
                return {
                    "jsonrpc": "2.0",
                    "result": "mock_sandbox_execution",
                    "id": payload.get("id")
                }

            # Chế độ cosa_governed
            allowed_tools = scope.get("allowed_tools", [])
            
            if tool_name not in allowed_tools:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Tool {tool_name} is not registered or authorized in current scope."
                    },
                    "id": payload.get("id")
                }
                
            # Giả lập gọi qua ToolInvocationService
            return {
                "jsonrpc": "2.0",
                "result": "mock_invocation_success",
                "id": payload.get("id")
            }
            
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Invalid Request"},
            "id": payload.get("id")
        }
