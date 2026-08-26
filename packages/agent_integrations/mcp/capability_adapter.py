from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from agent_core.contracts.capability import CapabilityImplementationIdentity, CapabilitySpec
from agent_core.capabilities.registry import CapabilityHandler, CapabilityRegistry
from agent_core.capabilities.canonicalization import compute_payload_hash
from agent_core.governance.contracts import CapabilityRisk

__all__ = ["McpToolCaller", "mcp_tool_to_capability_spec", "register_mcp_tools"]

# (tool_name, arguments) -> kết quả — do caller (MCP client thật) tiêm vào, không
# import trực tiếp 1 SDK MCP cụ thể ở tầng adapter này (môi trường phát triển
# hiện tại không cài được package `mcp` — cần Python 3.10+, xem ghi chú trong
# COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md Wave 9). Nhận
# tool definition dạng dict JSON thô (name/description/inputSchema) đúng wire
# format MCP `tools/list`, không phụ thuộc API cụ thể của 1 SDK version.
McpToolCaller = Callable[[str, dict[str, Any]], Awaitable[Any]]


def mcp_tool_to_capability_spec(
    tool: dict[str, Any],
    *,
    connector_key: str,
    catalog_version: str,
    capability_id_prefix: str = "mcp",
    risk: CapabilityRisk = CapabilityRisk.MEDIUM,
) -> CapabilitySpec:
    """Convert 1 MCP tool definition (`{"name", "description", "inputSchema"}`,
    đúng response shape của MCP `tools/list`) thành `CapabilitySpec`. MCP chỉ là
    transport/discovery (Blueprint V2 §10.1) — CapabilitySpec sinh ra từ đây vẫn
    phải qua đúng pipeline CapabilityGateway khi thực thi, không có execution
    path riêng.

    Risk mặc định MEDIUM (không phải LOW) vì tool MCP đến từ server bên ngoài,
    chưa có evidence để coi là an toàn low-risk như capability nội bộ COSA."""
    name = tool["name"]
    input_schema = tool.get("inputSchema") or {"type": "object", "properties": {}}
    schema_hash = compute_payload_hash(input_schema)
    capability_id = f"{capability_id_prefix}.{name}"

    return CapabilitySpec(
        id=capability_id,
        description=tool.get("description", ""),
        input_schema=input_schema,
        risk=risk,
        connector_requirements={"connector_id": connector_key},
        implementation_identity=CapabilityImplementationIdentity(
            capability_id=capability_id,
            schema_version=catalog_version,
        ),
        metadata={
            "mcp_tool_name": name,
            "mcp_source": "tools/list",
            "mcp_server_name": connector_key,
            "mcp_tool_schema_hash": schema_hash,
        },
    )


def register_mcp_tools(
    registry: CapabilityRegistry,
    tools: list[dict[str, Any]],
    caller: McpToolCaller,
    *,
    connector_key: str,
    catalog_version: str,
    capability_id_prefix: str = "mcp",
    risk: CapabilityRisk = CapabilityRisk.MEDIUM,
) -> list[str]:
    """Đăng ký hàng loạt MCP tool vào `CapabilityRegistry`. Handler sinh ra chỉ
    gọi `caller(tool_name, payload)` — không tự thực thi side effect ở đây,
    không tự quyết governance/approval. Mọi lời gọi VẪN đi qua
    `CapabilityGateway.execute()` như bất kỳ capability nội bộ nào khác (đăng
    ký vào registry không phải là execution path riêng)."""
    registered_ids: list[str] = []
    for tool in tools:
        spec = mcp_tool_to_capability_spec(
            tool,
            connector_key=connector_key,
            catalog_version=catalog_version,
            capability_id_prefix=capability_id_prefix,
            risk=risk,
        )
        tool_name = tool["name"]

        async def handler(
            payload: dict[str, Any], ctx: dict[str, Any], *, _tool_name: str = tool_name
        ) -> Any:
            return await caller(_tool_name, payload)

        registry.register(spec, handler)
        registered_ids.append(spec.id)
    return registered_ids
