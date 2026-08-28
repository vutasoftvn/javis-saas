"""Contract and smoke tests for MCP adapter (mcp_tool_to_capability_spec & register_mcp_tools).

Asserts:
- mcp_tool_to_capability_spec maps MCP wire format tools to valid CapabilitySpec.
- Default risk is MEDIUM (safe default for external MCP tools).
- register_mcp_tools registers tools to CapabilityRegistry and delegates execution to caller.
"""

from __future__ import annotations

import pytest
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.governance.contracts import CapabilityRisk
from agent_integrations.mcp.capability_adapter import (
    mcp_tool_to_capability_spec,
    register_mcp_tools,
)


def test_mcp_tool_to_capability_spec_contract():
    """Maps wire format tool definition into CapabilitySpec."""
    raw_tool = {
        "name": "fetch_sales_report",
        "description": "Fetch sales report from CRM",
        "inputSchema": {
            "type": "object",
            "properties": {"quarter": {"type": "string"}},
            "required": ["quarter"],
        },
    }

    spec = mcp_tool_to_capability_spec(
        raw_tool,
        connector_key="salesforce_mcp",
        catalog_version="1.2.0",
        capability_id_prefix="crm",
    )

    assert spec.id == "crm.fetch_sales_report"
    assert spec.description == "Fetch sales report from CRM"
    assert spec.risk == CapabilityRisk.MEDIUM
    assert spec.connector_requirements == {"connector_id": "salesforce_mcp"}
    assert spec.implementation_identity is not None
    assert spec.implementation_identity.schema_version == "1.2.0"
    assert spec.metadata["mcp_tool_name"] == "fetch_sales_report"


@pytest.mark.asyncio
async def test_register_mcp_tools_and_execute_through_registry():
    """register_mcp_tools attaches async caller handler correctly in registry."""
    registry = CapabilityRegistry()
    raw_tools = [
        {"name": "echo_tool", "description": "Echoes input", "inputSchema": {"type": "object"}},
    ]

    called_payloads: list[dict] = []

    async def mock_caller(tool_name: str, payload: dict) -> dict:
        called_payloads.append({"tool": tool_name, "payload": payload})
        return {"echo": payload}

    registered = register_mcp_tools(
        registry,
        raw_tools,
        mock_caller,
        connector_key="test_server",
        catalog_version="1.0.0",
    )

    assert registered == ["mcp.echo_tool"]

    registered_item = registry.get("mcp.echo_tool")
    assert registered_item is not None

    res = await registered_item.handler({"msg": "ping"}, {"workspace_id": "ws_1"})
    assert res == {"echo": {"msg": "ping"}}
    assert len(called_payloads) == 1
    assert called_payloads[0]["tool"] == "echo_tool"
