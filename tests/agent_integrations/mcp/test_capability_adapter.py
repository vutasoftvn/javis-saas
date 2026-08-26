from agent_core.capabilities.registry import CapabilityRegistry
from agent_integrations.mcp.capability_adapter import register_mcp_tools


def test_register_mcp_tools_sets_connector_requirements_and_schema_hash():
    registry = CapabilityRegistry()

    async def fake_caller(tool_name, payload):
        return {"ok": True}

    ids = register_mcp_tools(
        registry,
        tools=[{"name": "list_items", "description": "List items", "inputSchema": {"type": "object", "properties": {}}}],
        caller=fake_caller,
        connector_key="sandbox-read",
        catalog_version="1.0.0",
    )

    assert ids == ["mcp.list_items"]
    reg = registry.get("mcp.list_items")
    assert reg.spec.connector_requirements == {"connector_id": "sandbox-read"}
    assert reg.spec.metadata["mcp_server_name"] == "sandbox-read"
    assert "mcp_tool_schema_hash" in reg.spec.metadata
    assert reg.spec.implementation_identity is not None
    assert reg.spec.implementation_identity.schema_version == "1.0.0"
