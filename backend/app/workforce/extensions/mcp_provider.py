import uuid
import httpx
from app.workforce.extensions.seams import ConnectorProvider, DiscoveredCapability, ProviderHealth, ProviderResult
from app.workforce.extensions.contracts import ProviderProtocolError, ProviderUnavailableError
from app.workforce.agents.runtime.execution_scope import ExecutionScope

class MCPProvider(ConnectorProvider):
    async def health(self, scope: ExecutionScope) -> ProviderHealth:
        return ProviderHealth(status="ok")

    async def discover(self, scope: ExecutionScope, config: dict) -> tuple[DiscoveredCapability, ...]:
        endpoint = config.get("endpoint")
        extension_id = config.get("extension_id")
        if not endpoint or not extension_id:
            raise ProviderUnavailableError("Missing endpoint or extension_id in config")

        try:
            async with httpx.AsyncClient() as client:
                # 1. Initialize
                init_id = str(uuid.uuid4())
                init_resp = await client.post(endpoint, json={
                    "jsonrpc": "2.0",
                    "id": init_id,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "cosa-harness", "version": "1.0.0"}
                    }
                })
                
                if init_resp.status_code != 200:
                    raise ProviderUnavailableError(f"Initialize failed: {init_resp.status_code}")
                
                init_data = init_resp.json()
                if "error" in init_data:
                    raise ProviderProtocolError(f"Initialize error: {init_data['error']}")
                
                if init_data.get("result", {}).get("protocolVersion") != "2025-03-26":
                    raise ProviderProtocolError("Unsupported protocol version")

                # 2. Initialized notification
                await client.post(endpoint, json={
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                })

                # 3. tools/list
                list_id = str(uuid.uuid4())
                list_resp = await client.post(endpoint, json={
                    "jsonrpc": "2.0",
                    "id": list_id,
                    "method": "tools/list",
                    "params": {}
                })
                
                if list_resp.status_code != 200:
                    raise ProviderUnavailableError(f"tools/list failed: {list_resp.status_code}")
                    
                list_data = list_resp.json()
                if "error" in list_data:
                    raise ProviderProtocolError(f"tools/list error: {list_data['error']}")
                    
                tools = list_data.get("result", {}).get("tools", [])
                
                discovered = []
                for tool in tools:
                    name = tool.get("name")
                    if not name:
                        continue
                    discovered.append(DiscoveredCapability(
                        capability_id=f"{extension_id}:{name}",
                        name=name,
                        description=tool.get("description"),
                        input_schema=tool.get("inputSchema"),
                        output_schema=None
                    ))
                
                return tuple(discovered)
        except httpx.RequestError as e:
            raise ProviderUnavailableError(f"Request failed: {str(e)}")

    async def invoke(self, scope: ExecutionScope, capability_id: str, arguments: dict) -> ProviderResult:
        # capability_id is extension_id:tool_name
        # config is expected to be fetched or passed. Wait, the interface is invoke(scope, capability_id, arguments)
        # We need config! Wait, the contract has no config parameter in invoke? 
        # Ah, the spec says: ConnectorProvider.invoke(scope, capability_id, arguments) -> ProviderResult
        # Then how does MCPProvider know the endpoint? It must be retrieved from the extension registration or we assume the bridge passes it via some context, or we fetch it from the registry.
        raise NotImplementedError("invoke is handled by bridge or requires config")
