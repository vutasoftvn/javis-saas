import uuid
import httpx
from core.tool_registry import FLAT_NAME_PATTERN
from workforce.extensions.seams import ConnectorProvider, DiscoveredCapability, ProviderHealth, ProviderResult
from workforce.extensions.contracts import ProviderProtocolError, ProviderUnavailableError
from workforce.agents.runtime.execution_scope import ExecutionScope


def _parse_envelope(response: httpx.Response, request_id: str) -> dict:
    """Decode and validate a JSON-RPC 2.0 response envelope. Never re-raises the
    underlying parser/transport exception text - it may contain the endpoint URL or
    embedded credentials."""
    try:
        data = response.json()
    except ValueError:
        raise ProviderProtocolError("Invalid MCP response")

    if not isinstance(data, dict) or data.get("jsonrpc") != "2.0" or data.get("id") != request_id:
        raise ProviderProtocolError("Invalid MCP response")

    if "error" in data:
        raise ProviderProtocolError("MCP provider returned an error")

    return data


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
                    raise ProviderUnavailableError("MCP provider unavailable")

                init_data = _parse_envelope(init_resp, init_id)
                init_result = init_data.get("result")
                if not isinstance(init_result, dict) or init_result.get("protocolVersion") != "2025-03-26":
                    raise ProviderProtocolError("Invalid MCP response")

                # 2. Initialized notification (no response body to validate)
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
                    raise ProviderUnavailableError("MCP provider unavailable")

                list_data = _parse_envelope(list_resp, list_id)
                list_result = list_data.get("result")
                if not isinstance(list_result, dict) or not isinstance(list_result.get("tools"), list):
                    raise ProviderProtocolError("Invalid MCP response")

                # Validate every tool before registering any of them - a manifest that
                # would half-register is worse than one that registers nothing.
                discovered = []
                for tool in list_result["tools"]:
                    if not isinstance(tool, dict):
                        raise ProviderProtocolError("Invalid MCP response")
                    name = tool.get("name")
                    if not name or not FLAT_NAME_PATTERN.match(name):
                        raise ProviderProtocolError("Invalid MCP response")
                    discovered.append(DiscoveredCapability(
                        capability_id=f"{extension_id}:{name}",
                        name=name,
                        description=tool.get("description"),
                        input_schema=tool.get("inputSchema"),
                        output_schema=None,
                        endpoint_config={"endpoint": endpoint},
                    ))

                return tuple(discovered)
        except httpx.RequestError:
            raise ProviderUnavailableError("MCP provider unavailable")

    async def invoke(
        self,
        scope: ExecutionScope,
        capability: DiscoveredCapability,
        arguments: dict,
    ) -> ProviderResult:
        endpoint = capability.endpoint_config.get("endpoint")
        if not endpoint:
            raise ProviderUnavailableError("Missing MCP endpoint configuration")

        request_id = str(uuid.uuid4())
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "tools/call",
                    "params": {"name": capability.name, "arguments": arguments},
                })
        except httpx.RequestError:
            raise ProviderUnavailableError("MCP provider unavailable")

        if response.status_code != 200:
            raise ProviderUnavailableError("MCP provider unavailable")

        response_data = _parse_envelope(response, request_id)

        result = response_data.get("result")
        if not isinstance(result, dict):
            raise ProviderProtocolError("Invalid MCP response")

        content = result.get("content")
        if not isinstance(content, list):
            raise ProviderProtocolError("Invalid MCP response")
        for item in content:
            if not isinstance(item, dict) or "type" not in item:
                raise ProviderProtocolError("Invalid MCP response")
            if item["type"] == "text" and "text" not in item:
                raise ProviderProtocolError("Invalid MCP response")

        output = result["structuredContent"] if "structuredContent" in result else content
        return ProviderResult(status="success", result=output)
