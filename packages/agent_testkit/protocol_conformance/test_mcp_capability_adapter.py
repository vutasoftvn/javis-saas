"""Wave 9 — MCP capability adapter conformance: MCP tool registered qua
register_mcp_tools() phải đi qua ĐÚNG CapabilityGateway pipeline (governance,
idempotency, tool_call ledger) như capability nội bộ — không có execution path
riêng cho MCP (Blueprint V2 §10.1)."""
from __future__ import annotations

import pytest

from agent_core.capabilities.gateway import CapabilityGateway, GatewayExecutionRequest
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.runs.repository import InMemoryRunRepository
from agent_integrations.mcp.capability_adapter import mcp_tool_to_capability_spec, register_mcp_tools


def test_mcp_tool_to_capability_spec_maps_wire_format_correctly():
    tool = {
        "name": "search_web",
        "description": "Tìm kiếm thông tin công khai trên web",
        "inputSchema": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}},
    }
    spec = mcp_tool_to_capability_spec(
        tool, capability_id_prefix="mcp.acme_server", connector_key="acme_server", catalog_version="1.0.0"
    )

    assert spec.id == "mcp.acme_server.search_web"
    assert spec.description == "Tìm kiếm thông tin công khai trên web"
    assert spec.input_schema["required"] == ["query"]
    assert spec.metadata["mcp_tool_name"] == "search_web"


@pytest.mark.asyncio
async def test_registered_mcp_tool_executes_through_real_gateway_pipeline():
    call_log = []

    async def fake_mcp_caller(tool_name: str, args: dict) -> dict:
        call_log.append((tool_name, args))
        return {"results": ["Kết quả A", "Kết quả B"]}

    registry = CapabilityRegistry()
    tools = [
        {
            "name": "search_web",
            "description": "Web search",
            "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
        }
    ]
    registered_ids = register_mcp_tools(
        registry, tools, fake_mcp_caller, connector_key="search-web", catalog_version="1.0.0"
    )
    assert registered_ids == ["mcp.search_web"]

    repo = InMemoryRunRepository()
    gateway = CapabilityGateway(registry=registry, repository=repo)

    req = GatewayExecutionRequest(
        run_id="run_mcp_1",
        capability_id="mcp.search_web",
        input_payload={"query": "COSA agent platform"},
    )
    result = await gateway.execute(req)

    assert result.status == "completed"
    assert result.output_payload == {"results": ["Kết quả A", "Kết quả B"]}
    assert call_log == [("search_web", {"query": "COSA agent platform"})]

    # Đúng pipeline gateway — có tool_call ledger entry như capability nội bộ.
    tool_calls = await repo.list_tool_calls("run_mcp_1")
    assert len(tool_calls) == 1
    assert tool_calls[0].capability_id == "mcp.search_web"
    assert tool_calls[0].status == "completed"
