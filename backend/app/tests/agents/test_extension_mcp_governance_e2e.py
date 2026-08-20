"""Opt-in end-to-end coverage for governed extension MCP execution."""

from __future__ import annotations

from dataclasses import dataclass, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from threading import Thread
from typing import Any

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.core import tool_registry
from app.platform.auth.models import User, Workspace
from app.workforce.agents.governance.models import (
    AgentApproval,
    AgentRun,
    AgentToolCall,
)
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.agents.runtime.tool_bridge import dispatch_tool_call
from app.workforce.agents.runtime.types import AgentRunRequest
from app.workforce.extensions.registry import ExtensionRegistry
from app.workforce.extensions.seams import DiscoveredCapability
from app.workforce.extensions.tool_registration import register_extension_tools
from app.workforce.tools.invocation.contracts import ToolInvocationError


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DB_INTEGRATION") != "1",
    reason="requires migrated Postgres",
)

EXTENSION_ID = "com.cosa.crm"
CAPABILITY_ID = f"{EXTENSION_ID}:search"
TOOL_FLAT_NAME = "com_cosa_crm_search"
TOOL_QUALIFIED_NAME = "com_cosa_crm.search"


@dataclass(frozen=True)
class _DatabaseContext:
    user_id: int
    workspace_a_id: int
    workspace_b_id: int
    run_id: int


@dataclass
class _FakeMCPServer:
    server: ThreadingHTTPServer
    thread: Thread
    calls: list[dict[str, Any]]

    @property
    def url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}/rpc"


@pytest.fixture
def fake_mcp_server():
    calls: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            body_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(body_length))
            calls.append(
                {"method": payload.get("method"), "params": payload.get("params")}
            )
            response = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {"matches": ["Ada"]},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    fake = _FakeMCPServer(server=server, thread=thread, calls=calls)
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def db_ctx():
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        columns = {
            column["name"]: str(column["type"]).upper()
            for column in inspect(db.get_bind()).get_columns(
                "extension_registrations"
            )
        }
    except SQLAlchemyError as exc:
        db.close()
        pytest.skip(
            "requires migrated Postgres; extension schema inspection failed: "
            f"{type(exc).__name__}"
        )
    if "capabilities_jsonb" not in columns:
        db.close()
        pytest.skip(
            "requires migrated Postgres; extension_registrations is missing "
            "capabilities_jsonb"
        )
    if columns.get("workspace_id") != "BIGINT":
        db.close()
        pytest.skip(
            "requires compatible migrated Postgres; "
            "extension_registrations.workspace_id is "
            f"{columns.get('workspace_id', 'missing')}, but real workspace "
            "Snowflake IDs require BIGINT"
        )

    original_registry = dict(tool_registry._registry)
    user = User(
        email=f"extension-e2e-{id(db)}@example.test",
        password_hash="test",
        display_name="Extension Governance E2E",
    )
    workspace_a = Workspace(name="Extension Governance E2E A")
    workspace_b = Workspace(name="Extension Governance E2E B")
    try:
        db.add_all([user, workspace_a, workspace_b])
        db.flush()
        run = AgentRun(
            workspace_id=workspace_a.id,
            company_id=workspace_a.id,
            user_id=user.id,
            agent_key="extension_e2e_agent",
            runtime="test",
            status="running",
            permission_profile="L0_READ",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        db.info["extension_e2e"] = _DatabaseContext(
            user_id=user.id,
            workspace_a_id=workspace_a.id,
            workspace_b_id=workspace_b.id,
            run_id=run.id,
        )
        yield db
    finally:
        db.rollback()
        context = db.info.get("extension_e2e")
        if context is not None:
            db.execute(
                text("DELETE FROM agent_tool_calls WHERE run_id = :run_id"),
                {"run_id": context.run_id},
            )
            db.execute(
                text("DELETE FROM agent_approvals WHERE workspace_id IN (:a, :b)"),
                {"a": context.workspace_a_id, "b": context.workspace_b_id},
            )
            db.execute(
                text("DELETE FROM agent_runs WHERE id = :run_id"),
                {"run_id": context.run_id},
            )
            db.execute(
                text(
                    "DELETE FROM extension_registrations "
                    "WHERE workspace_id IN (:a, :b)"
                ),
                {"a": context.workspace_a_id, "b": context.workspace_b_id},
            )
            db.execute(
                text("DELETE FROM workspaces WHERE id IN (:a, :b)"),
                {"a": context.workspace_a_id, "b": context.workspace_b_id},
            )
            db.execute(
                text("DELETE FROM users WHERE id = :user_id"),
                {"user_id": context.user_id},
            )
            db.commit()
        tool_registry._registry.clear()
        tool_registry._registry.update(original_registry)
        db.close()


def _scope(context: _DatabaseContext, workspace_id: int) -> ExecutionScope:
    return ExecutionScope(
        workspace_id=workspace_id,
        company_id=workspace_id,
        principal_user_id=context.user_id,
        principal_member_id=context.user_id,
        principal_role="owner",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=(),
    )


def _request(context: _DatabaseContext, workspace_id: int) -> AgentRunRequest:
    return AgentRunRequest(
        workspace_id=str(workspace_id),
        company_id=str(workspace_id),
        user_id=str(context.user_id),
        agent_key="extension_e2e_agent",
        task="Search CRM through governed MCP",
        permission_profile="L0_READ",
        parent_run_id=str(context.run_id),
    )


def _manifest(endpoint: str) -> dict[str, Any]:
    return {
        "extension_id": EXTENSION_ID,
        "version": "1.0.0",
        "compatibility": ">=1.0.0",
        "trust_level": "first_party",
        "owner": "cosa",
        "capabilities": [{"id": CAPABILITY_ID, "name": "search"}],
        "required_permissions": [],
        "required_secret_refs": [],
        "supported_scope_levels": ["company"],
        "health_check": {"type": "mcp"},
        "disable_behavior": "block_new_calls_preserve_history",
        "provider_type": "mcp",
        "provider_config": {"endpoint": endpoint},
    }


def _capability(endpoint: str) -> DiscoveredCapability:
    return DiscoveredCapability(
        capability_id=CAPABILITY_ID,
        name="search",
        description="Search CRM contacts",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        output_schema={"type": "object"},
        endpoint_config={"endpoint": endpoint},
    )


def install_discovered_extension(
    db,
    endpoint: str,
    *,
    registration_workspace: str = "a",
    request_workspace: str = "a",
):
    context: _DatabaseContext = db.info["extension_e2e"]
    registration_workspace_id = (
        context.workspace_a_id
        if registration_workspace == "a"
        else context.workspace_b_id
    )
    request_workspace_id = (
        context.workspace_a_id if request_workspace == "a" else context.workspace_b_id
    )
    registry = ExtensionRegistry()
    registration = registry.install(
        db, registration_workspace_id, _manifest(endpoint)
    )
    registry.record_discovery(
        db,
        registration_workspace_id,
        EXTENSION_ID,
        [_capability(endpoint)],
    )
    return (
        _scope(context, request_workspace_id),
        _request(context, request_workspace_id),
        registration,
    )


@pytest.mark.asyncio
async def test_allowed_extension_call_is_audited_and_calls_mcp_once(
    db_ctx, fake_mcp_server
):
    scope, request, _registration = install_discovered_extension(
        db_ctx, fake_mcp_server.url
    )
    register_extension_tools(db_ctx, scope)

    result = await dispatch_tool_call(
        db_ctx,
        request,
        TOOL_FLAT_NAME,
        {"query": "Ada"},
        run_id=request.parent_run_id,
    )

    assert result == {"matches": ["Ada"]}
    assert fake_mcp_server.calls == [
        {
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "Ada"}},
        }
    ]
    assert (
        db_ctx.query(AgentToolCall)
        .filter_by(run_id=int(request.parent_run_id), tool_name=TOOL_QUALIFIED_NAME)
        .count()
        == 1
    )


@pytest.mark.asyncio
async def test_approval_required_extension_returns_awaiting_approval_without_mcp(
    db_ctx, fake_mcp_server
):
    scope, request, _registration = install_discovered_extension(
        db_ctx, fake_mcp_server.url
    )
    spec = register_extension_tools(db_ctx, scope)[0]
    tool_registry._registry[spec.qualified_name] = replace(
        spec,
        risk_level="critical",
        permission_level="admin_write",
        requires_approval=True,
    )

    result = await dispatch_tool_call(
        db_ctx,
        request,
        TOOL_FLAT_NAME,
        {"query": "Ada"},
        run_id=request.parent_run_id,
    )

    assert result["status"] == "awaiting_approval"
    assert result["tool_name"] == TOOL_QUALIFIED_NAME
    assert result["approval_id"] is not None
    assert fake_mcp_server.calls == []
    assert (
        db_ctx.query(AgentApproval)
        .filter_by(id=int(result["approval_id"]), workspace_id=scope.workspace_id)
        .count()
        == 1
    )


@pytest.mark.asyncio
async def test_workspace_b_capability_cannot_execute_for_workspace_a(
    db_ctx, fake_mcp_server
):
    context: _DatabaseContext = db_ctx.info["extension_e2e"]
    scope_b, request_a, _registration = install_discovered_extension(
        db_ctx,
        fake_mcp_server.url,
        registration_workspace="b",
        request_workspace="a",
    )
    register_extension_tools(db_ctx, scope_b)

    with pytest.raises(
        ToolInvocationError, match="Connector capability is not eligible"
    ):
        await dispatch_tool_call(
            db_ctx,
            request_a,
            TOOL_FLAT_NAME,
            {"query": "Ada", "workspace_id": context.workspace_b_id},
            run_id=request_a.parent_run_id,
        )

    assert fake_mcp_server.calls == []
