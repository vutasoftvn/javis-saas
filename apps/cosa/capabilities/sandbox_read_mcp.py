from __future__ import annotations

import os
from typing import Any

from agent_core.capabilities.registry import CapabilityRegistry
from agent_integrations.mcp.capability_adapter import register_mcp_tools

__all__ = ["register_sandbox_read_mcp_tools"]

SANDBOX_READ_MCP_URL = os.environ.get("COSA_SANDBOX_READ_MCP_URL", "")


def register_sandbox_read_mcp_tools(registry: CapabilityRegistry) -> list[str]:
    """Đăng ký MCP tool đọc-only đầu tiên cho pilot (Wave B/C). Chỉ hỗ trợ
    `streamable-http`, chỉ đọc — theo đúng giới hạn pilot đã chốt. Không tự
    thực thi side effect ở đây — handler CHỈ gọi MCP server thật, mọi
    governance/approval/audit vẫn do CapabilityGateway.execute() quyết định."""
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession

    async def caller(tool_name: str, payload: dict[str, Any]) -> Any:
        async with streamablehttp_client(SANDBOX_READ_MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, payload)
                return result.model_dump()

    # tools/list tĩnh cho pilot — 1 tool duy nhất, đã review thủ công
    # (đúng nguyên tắc "first-party, reviewed" — không tự động discover
    # runtime từ server bên ngoài trong pilot).
    tools = [
        {
            "name": "list_sandbox_items",
            "description": "List read-only sandbox items for operations reporting.",
            "inputSchema": {"type": "object", "properties": {}},
        }
    ]

    return register_mcp_tools(
        registry,
        tools=tools,
        caller=caller,
        connector_key="sandbox-read",
        catalog_version="1.0.0",
    )
