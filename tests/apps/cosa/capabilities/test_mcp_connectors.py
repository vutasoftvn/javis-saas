"""Connector MCP theo manifest: tool ghi luôn bắt buộc duyệt, grant do gateway kiểm (G-6)."""

from __future__ import annotations

import json

import pytest
from agent.capabilities.registry import CapabilityRegistry
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk, PolicyOutcome
from agent.governance.floor import capability_floor
from pydantic import ValidationError

from apps.cosa.capabilities.mcp_connectors import (
    McpConnectorManifest,
    load_mcp_connector_manifests,
    register_mcp_connectors,
)

_MANIFEST = {
    "connectors": [
        {
            "connector_key": "email-read",
            "url": "https://mcp.example.com/email",
            "auth_env": "EMAIL_MCP_TOKEN",
            "tools": [
                {
                    "name": "list_threads",
                    "description": "List recent email threads",
                    "access": "read",
                },
                {"name": "send_reply", "description": "Send an email reply", "access": "write"},
            ],
        }
    ]
}


def _write(tmp_path, data) -> str:
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def test_no_manifest_configured_registers_nothing(monkeypatch):
    monkeypatch.delenv("COSA_MCP_CONNECTORS_FILE", raising=False)
    assert load_mcp_connector_manifests() == []


def test_write_tool_is_high_risk_and_always_requires_approval(tmp_path):
    manifests = load_mcp_connector_manifests(_write(tmp_path, _MANIFEST))
    registry = CapabilityRegistry()

    async def _never(tool, payload):  # pragma: no cover - không gọi tới
        raise AssertionError

    ids = register_mcp_connectors(registry, manifests, caller_factory=lambda m: _never)
    assert ids == ["mcp.email-read.list_threads", "mcp.email-read.send_reply"]

    read = registry.get("mcp.email-read.list_threads").spec
    write = registry.get("mcp.email-read.send_reply").spec
    assert read.connector_requirements == {"connector_id": "email-read"}
    assert write.connector_requirements == {"connector_id": "email-read"}
    assert CapabilityRisk(write.risk) is CapabilityRisk.HIGH
    assert ApprovalPolicy(write.approval_policy) is ApprovalPolicy.ALWAYS
    assert capability_floor(write.risk, write.approval_policy) == PolicyOutcome.REQUIRE_APPROVAL
    assert ApprovalPolicy(read.approval_policy) is ApprovalPolicy.POLICY_DRIVEN


@pytest.mark.asyncio
async def test_handler_calls_the_reviewed_tool_name(tmp_path):
    manifests = load_mcp_connector_manifests(_write(tmp_path, _MANIFEST))
    calls: list[tuple[str, dict]] = []

    def factory(manifest):
        async def caller(tool, payload):
            calls.append((tool, payload))
            return {"ok": True}

        return caller

    registry = CapabilityRegistry()
    register_mcp_connectors(registry, manifests, caller_factory=factory)
    handler = registry.get_handler("mcp.email-read.list_threads")
    assert await handler({"limit": 5}, None) == {"ok": True}
    assert calls == [("list_threads", {"limit": 5})]


@pytest.mark.parametrize(
    "patch",
    [
        {"url": "http://evil.example.com"},
        {"connector_key": "Bad Key"},
        {"tools": []},
        {"tools": [{"name": "x-y", "description": "bad name", "access": "read"}]},
        {"tools": [{"name": "do_it", "description": "unknown access", "access": "admin"}]},
    ],
)
def test_invalid_manifest_is_rejected(patch):
    base = dict(_MANIFEST["connectors"][0])
    base.update(patch)
    with pytest.raises(ValidationError):
        McpConnectorManifest.model_validate(base)


def test_duplicate_connector_keys_rejected(tmp_path):
    data = {"connectors": _MANIFEST["connectors"] * 2}
    with pytest.raises(ValueError):
        load_mcp_connector_manifests(_write(tmp_path, data))
