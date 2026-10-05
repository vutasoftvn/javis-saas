"""Connector MCP khai báo bằng manifest đã review (review 2026-09-27, G-6).

Mở rộng pilot `sandbox-read` thành khung chung cho email/lịch, kế toán/ngân hàng,
kênh khách hàng… mà KHÔNG mở cửa tự discover tool từ server ngoài:

- Manifest JSON (`COSA_MCP_CONNECTORS_FILE`) liệt kê TĨNH từng connector và từng
  tool đã review, mỗi tool khai báo `access` = `read` | `write`.
- Tool `read`: risk MEDIUM, approval POLICY_DRIVEN (CosaPolicyEngine quyết định).
- Tool `write` (gửi mail, tạo sự kiện, ghi sổ…): risk HIGH + approval ALWAYS →
  floor REQUIRE_APPROVAL, không policy nào nới được (quy tắc 8).
- Mọi lời gọi vẫn qua CapabilityGateway: grant connector được kiểm lại ở MỌI lần
  execute (`connector_requirements.connector_id`), nên workspace chưa
  install/authorize/grant connector thì tool bị DENY.
- Credential máy chủ MCP lấy từ biến môi trường tên trong `auth_env` (secret phía
  server). Secret theo từng workspace qua `secret_ref` của grant là bước sau.

Capability id: `mcp.<connector_key>.<tool_name>`.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from agent.capabilities.registry import CapabilityRegistry
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk
from agent_integrations.mcp.capability_adapter import mcp_tool_to_capability_spec
from pydantic import BaseModel, Field, field_validator

__all__ = [
    "McpConnectorManifest",
    "McpToolDecl",
    "load_mcp_connector_manifests",
    "register_mcp_connectors",
]

logger = logging.getLogger(__name__)

_KEY_RE = re.compile(r"^[a-z][a-z0-9-]{1,40}$")
_TOOL_RE = re.compile(r"^[a-z][a-z0-9_]{1,60}$")

# (connector, tool_name, payload) -> kết quả
McpCallerFactory = Callable[
    ["McpConnectorManifest"], Callable[[str, dict[str, Any]], Awaitable[Any]]
]


class McpToolDecl(BaseModel):
    name: str
    description: str = Field(min_length=5, max_length=1000)
    access: Literal["read", "write"]
    input_schema: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not _TOOL_RE.match(v):
            raise ValueError(f"invalid MCP tool name {v!r}")
        return v


class McpConnectorManifest(BaseModel):
    connector_key: str
    url: str
    catalog_version: str = "1.0.0"
    auth_env: str | None = None
    tools: list[McpToolDecl] = Field(min_length=1)

    @field_validator("connector_key")
    @classmethod
    def _key(cls, v: str) -> str:
        if not _KEY_RE.match(v):
            raise ValueError(f"invalid connector_key {v!r}")
        return v

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        # Chỉ HTTPS; HTTP chỉ cho localhost (dev/test).
        local = v.startswith(("http://localhost", "http://127.0.0.1"))
        if not (v.startswith("https://") or local):
            raise ValueError("MCP connector url must be https:// (http only for localhost)")
        return v


def load_mcp_connector_manifests(path: str | None = None) -> list[McpConnectorManifest]:
    """Đọc manifest; không cấu hình thì trả rỗng. Manifest sai thì raise — cấu hình
    connector hỏng không được âm thầm bỏ qua."""
    raw_path = path if path is not None else os.environ.get("COSA_MCP_CONNECTORS_FILE", "")
    if not raw_path.strip():
        return []
    data = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    items = data.get("connectors") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("MCP connector manifest must be a list or {'connectors': [...]}")
    manifests = [McpConnectorManifest.model_validate(item) for item in items]
    keys = [m.connector_key for m in manifests]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate connector_key in MCP connector manifest")
    return manifests


def _streamable_http_caller(
    manifest: McpConnectorManifest,
) -> Callable[[str, dict[str, Any]], Awaitable[Any]]:
    async def caller(tool_name: str, payload: dict[str, Any]) -> Any:
        import httpx2
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        headers: dict[str, str] = {}
        if manifest.auth_env:
            token = os.environ.get(manifest.auth_env, "")
            if not token:
                raise RuntimeError(
                    f"MCP connector {manifest.connector_key}: {manifest.auth_env} is not set"
                )
            headers["Authorization"] = f"Bearer {token}"

        async with (
            httpx2.AsyncClient(headers=headers, timeout=30.0) as http_client,
            streamable_http_client(manifest.url, http_client=http_client) as (
                read,
                write,
                _get_session_id,
            ),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.call_tool(tool_name, payload)
            return result.model_dump()

    return caller


def register_mcp_connectors(
    registry: CapabilityRegistry,
    manifests: list[McpConnectorManifest],
    caller_factory: McpCallerFactory | None = None,
) -> list[str]:
    factory = caller_factory or _streamable_http_caller
    registered: list[str] = []
    for manifest in manifests:
        caller = factory(manifest)
        for tool in manifest.tools:
            is_write = tool.access == "write"
            spec = mcp_tool_to_capability_spec(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                },
                connector_key=manifest.connector_key,
                catalog_version=manifest.catalog_version,
                capability_id_prefix=f"mcp.{manifest.connector_key}",
                risk=CapabilityRisk.HIGH if is_write else CapabilityRisk.MEDIUM,
                approval_policy=ApprovalPolicy.ALWAYS if is_write else ApprovalPolicy.POLICY_DRIVEN,
                extra_metadata={
                    "mcp_access": tool.access,
                    "action_class": "C" if is_write else "A",
                },
            )

            async def handler(
                payload: dict[str, Any],
                ctx: Any = None,
                *,
                _tool: str = tool.name,
                _caller: Callable[[str, dict[str, Any]], Awaitable[Any]] = caller,
            ) -> Any:
                return await _caller(_tool, payload)

            registry.register(spec, handler)
            registered.append(spec.id)
        logger.info(
            "mcp connector %s registered tools=%d", manifest.connector_key, len(manifest.tools)
        )
    return registered
