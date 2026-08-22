from __future__ import annotations

from typing import Any

import httpx

from agentos.tools.registry import ToolSpec


class MCPServerError(Exception):
    """MCP server trả lỗi trong response JSON-RPC (field "error")."""


class MCPServerUnavailableError(Exception):
    """Không kết nối được MCP server, hoặc server trả về HTTP lỗi."""


class MCPToolAdapter:
    """Gọi 1 tool qua Model Context Protocol server bằng JSON-RPC
    (blueprint §17 — MCP là interface capability, không thay thế business
    service). Port từ
    `legacy/agent_runtime/workforce/tools/transports/mcp_adapter.py`, bỏ
    phần phụ thuộc `ExecutionContext`/`BaseToolAdapter`/
    `workforce.extensions.contracts` (không có khái niệm tương đương trong
    `agentos/`) — chỉ giữ lại phần gọi JSON-RPC "tools/call" thuần túy, tự
    chủ qua httpx giống các adapter khác trong `agentos/core/adapters/`
    (ADR-012 pattern: không import ngược `legacy/`).
    """

    def __init__(self, server_url: str, *, timeout: float = 30.0) -> None:
        self._server_url = server_url
        self._timeout = timeout

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], *, request_id: str | None = None
    ) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": request_id,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(self._server_url, json=payload)
            except httpx.RequestError as exc:
                raise MCPServerUnavailableError(f"MCP request failed: {exc}") from exc

        if response.status_code != 200:
            raise MCPServerUnavailableError(f"MCP server returned HTTP {response.status_code}")

        data = response.json()
        if "error" in data:
            raise MCPServerError(f"MCP server error: {data['error']}")
        return data.get("result", data)


def make_mcp_tool_spec(
    name: str,
    description: str,
    adapter: MCPToolAdapter,
    *,
    mcp_tool_name: str | None = None,
    permission_class: str | None = None,
) -> ToolSpec:
    """Bọc 1 MCP tool thành `ToolSpec` để đăng ký vào `ToolRegistry` — cùng
    convention với tool binding của `services/` (`agentos/tools/clusters/`):
    gọi qua handler async, gắn `permission_class` để đi qua PolicyEngine
    như mọi tool khác, không có đường tắt riêng cho MCP.
    """

    async def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        return await adapter.call_tool(mcp_tool_name or name, arguments)

    return ToolSpec(name=name, description=description, handler=handler, permission_class=permission_class)
