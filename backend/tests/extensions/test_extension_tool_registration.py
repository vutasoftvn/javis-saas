import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core import tool_registry
from core.toolset_resolver import resolve_toolset
from workforce.agents.governance.kernel import GovernanceDecision
from workforce.agents.governance.kernel import GovernanceKernel
from workforce.agents.governance.policy_engine import PolicyAction
from workforce.agents.runtime.execution_scope import ExecutionScope
from workforce.extensions.models import ExtensionRegistration
from workforce.extensions.contracts import ProviderProtocolError
from workforce.extensions.registry import ExtensionRegistry
from workforce.extensions.seams import DiscoveredCapability, ProviderResult
from workforce.extensions.tool_registration import register_extension_tools
from workforce.chat import company_tools
from workforce.tools.invocation.contracts import ToolInvocationRequest
from workforce.tools.invocation.service import ToolInvocationService


EXTENSION_ID = "com.cosa.mcp.tenant-safe"
CAPABILITY_ID = f"{EXTENSION_ID}:search"
COLLISION_EXTENSION_IDS = ("foo.bar", "foo.bar.baz")


def _scope(workspace_id: int) -> ExecutionScope:
    return ExecutionScope(
        workspace_id=workspace_id,
        company_id=workspace_id,
        principal_user_id=1,
        principal_member_id=1,
        principal_role="owner",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=(),
    )


def _manifest(endpoint: str) -> dict:
    return {
        "extension_id": EXTENSION_ID,
        "version": "1.0.0",
        "compatibility": ">=1.0.0",
        "trust_level": "first_party",
        "owner": "system",
        "capabilities": [{
            "id": CAPABILITY_ID,
            "name": "search",
            "risk_level": "low",
            "permission_level": "read_only",
            "requires_approval": False,
            "mutating": False,
            "external": False,
        }],
        "required_permissions": [],
        "required_secret_refs": [],
        "supported_scope_levels": ["company"],
        "health_check": {"type": "ping"},
        "disable_behavior": "block_new_calls_preserve_history",
        "provider_type": "mcp",
        "provider_config": {"endpoint": endpoint},
    }


def _capability(
    endpoint: str,
    input_schema: dict | None = None,
) -> DiscoveredCapability:
    return DiscoveredCapability(
        capability_id=CAPABILITY_ID,
        name="search",
        description="Search tenant records",
        input_schema=input_schema or {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        output_schema={"type": "object"},
        endpoint_config={"endpoint": endpoint},
    )


@pytest.fixture
def session():
    from db.session import SessionLocal

    db = SessionLocal()
    db.query(ExtensionRegistration).filter(
        ExtensionRegistration.workspace_id.in_((501, 502)),
        ExtensionRegistration.extension_id.in_(
            (EXTENSION_ID, *COLLISION_EXTENSION_IDS)
        ),
    ).delete(synchronize_session=False)
    db.commit()
    # Extension tools now register into tool_registry's per-context overlay (see
    # register_overlay_tool), not the global _registry dict - a sync test function
    # has no Task boundary to isolate it from the next one, so reset explicitly.
    tool_registry.reset_overlay()
    original_names = set(tool_registry._registry)
    yield db
    tool_registry.reset_overlay()
    db.query(ExtensionRegistration).filter(
        ExtensionRegistration.workspace_id.in_((501, 502)),
        ExtensionRegistration.extension_id.in_(
            (EXTENSION_ID, *COLLISION_EXTENSION_IDS)
        ),
    ).delete(synchronize_session=False)
    db.commit()
    for qualified_name in set(tool_registry._registry) - original_names:
        tool_registry._registry.pop(qualified_name, None)
    db.close()


def _install_snapshot(
    session,
    workspace_id: int,
    endpoint: str,
    input_schema: dict | None = None,
) -> None:
    registry = ExtensionRegistry()
    registry.install(session, workspace_id, _manifest(endpoint))
    registry.record_discovery(
        session,
        workspace_id,
        EXTENSION_ID,
        [_capability(endpoint, input_schema=input_schema)],
    )


def _install_named_capability(
    session,
    workspace_id: int,
    extension_id: str,
    capability_name: str,
) -> None:
    capability_id = f"{extension_id}:{capability_name}"
    manifest = _manifest("https://collision.test/rpc")
    manifest["extension_id"] = extension_id
    manifest["capabilities"] = [{
        "id": capability_id,
        "name": capability_name,
        "risk_level": "low",
        "permission_level": "read_only",
        "requires_approval": False,
        "mutating": False,
        "external": False,
    }]
    registry = ExtensionRegistry()
    registry.install(session, workspace_id, manifest)
    registry.record_discovery(
        session,
        workspace_id,
        extension_id,
        [
            DiscoveredCapability(
                capability_id=capability_id,
                name=capability_name,
                input_schema={"type": "object"},
                endpoint_config={"endpoint": "https://collision.test/rpc"},
            )
        ],
    )


def test_registration_is_idempotent_and_maps_snapshot_and_manifest_metadata(session):
    scope = _scope(501)
    _install_snapshot(session, scope.workspace_id, "https://workspace-a.test/rpc")

    first = register_extension_tools(session, scope)
    second = register_extension_tools(session, scope)

    assert [spec.qualified_name for spec in first] == [
        "com_cosa_mcp_tenant_safe.search"
    ]
    assert [spec.qualified_name for spec in second] == [
        "com_cosa_mcp_tenant_safe.search"
    ]
    assert len(
        [
            name
            for name in tool_registry.get_registered_tools()
            if name == "com_cosa_mcp_tenant_safe.search"
        ]
    ) == 1
    spec = first[0]
    assert spec.execution_backend == "connector"
    assert spec.backend_id == EXTENSION_ID
    assert spec.input_schema == _capability("unused").input_schema
    assert spec.output_schema == {"type": "object"}
    assert spec.required_scope_level == "company"
    assert spec.required_secret_refs == []
    assert spec.risk_level == "low"
    assert spec.permission_level == "read_only"
    assert spec.requires_approval is False
    assert spec.mutating is False
    assert spec.external is False
    assert spec.qualified_name not in tool_registry._registry


def test_request_toolset_construction_registers_eligible_extension(session):
    scope = _scope(501)
    _install_snapshot(session, scope.workspace_id, "https://workspace-a.test/rpc")

    names = {
        spec.qualified_name
        for spec in resolve_toolset(
            session,
            scope.workspace_id,
            execution_scope=scope,
        )
    }

    assert "com_cosa_mcp_tenant_safe.search" in names


def test_request_toolset_excludes_connector_from_another_workspace(session):
    scope_a = _scope(501)
    scope_b = _scope(502)
    _install_snapshot(session, scope_b.workspace_id, "https://workspace-b.test/rpc")

    workspace_b_names = {
        spec.qualified_name
        for spec in resolve_toolset(
            session,
            scope_b.workspace_id,
            execution_scope=scope_b,
        )
    }
    workspace_a_names = {
        spec.qualified_name
        for spec in resolve_toolset(
            session,
            scope_a.workspace_id,
            execution_scope=scope_a,
        )
    }

    assert "com_cosa_mcp_tenant_safe.search" in workspace_b_names
    assert "com_cosa_mcp_tenant_safe.search" not in workspace_a_names


def test_registration_rejects_distinct_qualified_name_with_flat_name_collision(
    session,
):
    scope = _scope(501)
    _install_named_capability(
        session,
        scope.workspace_id,
        extension_id="foo.bar",
        capability_name="baz_qux",
    )
    first = register_extension_tools(session, scope)
    assert {spec.qualified_name for spec in first} == {"foo_bar.baz_qux"}

    _install_named_capability(
        session,
        scope.workspace_id,
        extension_id="foo.bar.baz",
        capability_name="qux",
    )
    second = register_extension_tools(session, scope)

    assert {spec.qualified_name for spec in second} == {"foo_bar.baz_qux"}
    assert "foo_bar_baz.qux" not in tool_registry.get_registered_tools()


@pytest.mark.asyncio
async def test_connector_dispatch_reuses_decision_and_resolves_workspace_at_call_time(
    session,
):
    scope_a = _scope(501)
    scope_b = _scope(502)
    _install_snapshot(session, scope_a.workspace_id, "https://workspace-a.test/rpc")
    _install_snapshot(session, scope_b.workspace_id, "https://workspace-b.test/rpc")
    spec = register_extension_tools(session, scope_a)[0]
    register_extension_tools(session, scope_b)
    decision = GovernanceDecision(
        allowed=True,
        action=PolicyAction.ALLOW,
        reason="already governed",
        tool_spec=spec,
        sanitized_args={"query": "Ada"},
    )
    request = ToolInvocationRequest(
        scope=scope_b,
        tool_flat_name=spec.flat_name,
        arguments={"query": "Ada"},
        source="test",
        governance_decision=decision,
    )
    service = ToolInvocationService()
    service.policy_gate.execute_if_allowed = MagicMock()

    with patch(
        "workforce.tools.invocation.service.MCPProvider.invoke",
        new_callable=AsyncMock,
        return_value=ProviderResult(status="success", result={"matches": ["Ada"]}),
    ) as invoke:
        result = await service.invoke(session, request)

    assert request.governance_decision is decision
    assert result.status == "success"
    assert result.output == {"matches": ["Ada"]}
    service.policy_gate.execute_if_allowed.assert_not_called()
    invoked_capability = invoke.await_args.args[1]
    assert invoked_capability.endpoint_config == {
        "endpoint": "https://workspace-b.test/rpc"
    }


@pytest.mark.asyncio
async def test_pre_evaluated_connector_decision_renormalizes_reserved_context(
    session,
):
    scope = _scope(501)
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "workspace_id": {"type": "integer"},
            "endpoint": {"type": "string"},
            "approval": {"type": "string"},
        },
        "required": ["query"],
    }
    _install_snapshot(
        session,
        scope.workspace_id,
        "https://workspace-a.test/rpc",
        input_schema=schema,
    )
    spec = register_extension_tools(session, scope)[0]
    injected = {
        "query": "Ada",
        "workspace_id": 502,
        "endpoint": "https://attacker.test/rpc",
        "approval": "approved",
    }
    decision = GovernanceDecision(
        allowed=True,
        action=PolicyAction.ALLOW,
        reason="already governed",
        tool_spec=spec,
        sanitized_args=injected,
    )
    request = ToolInvocationRequest(
        scope=scope,
        tool_flat_name=spec.flat_name,
        arguments=injected,
        source="test",
        governance_decision=decision,
    )

    with patch(
        "workforce.tools.invocation.service.MCPProvider.invoke",
        new_callable=AsyncMock,
        return_value=ProviderResult(status="success", result={"matches": ["Ada"]}),
    ) as invoke:
        result = await ToolInvocationService().invoke(session, request)

    assert result.status == "success"
    assert invoke.await_args.args[2] == {"query": "Ada"}
    assert set(spec.chat_schema["parameters"]["properties"]) == {"query"}


def test_request_overlay_replaces_rediscovered_schema_and_governance_metadata(session):
    scope = _scope(501)
    _install_snapshot(session, scope.workspace_id, "https://workspace-a.test/rpc")
    first = register_extension_tools(session, scope)[0]
    assert set(first.input_schema["properties"]) == {"query"}

    updated_manifest = _manifest("https://workspace-a.test/rpc")
    updated_manifest["version"] = "1.1.0"
    updated_manifest["capabilities"][0].update({
        "risk_level": "critical",
        "permission_level": "admin_write",
        "requires_approval": True,
        "mutating": True,
        "external": True,
    })
    registry = ExtensionRegistry()
    registry.install(session, scope.workspace_id, updated_manifest)
    registry.record_discovery(
        session,
        scope.workspace_id,
        EXTENSION_ID,
        [_capability(
            "https://workspace-a.test/rpc",
            input_schema={
                "type": "object",
                "properties": {"term": {"type": "string"}},
                "required": ["term"],
            },
        )],
    )

    refreshed = register_extension_tools(session, scope)[0]

    assert set(refreshed.input_schema["properties"]) == {"term"}
    assert refreshed.risk_level == "critical"
    assert refreshed.permission_level == "admin_write"
    assert refreshed.requires_approval is True
    assert refreshed.mutating is True
    assert refreshed.external is True
    assert tool_registry.get_tool_by_flat_name(refreshed.flat_name) == refreshed
    assert refreshed.qualified_name not in tool_registry._registry


@pytest.mark.asyncio
async def test_request_overlay_isolates_workspace_specific_schemas(session):
    scope_a = _scope(501)
    scope_b = _scope(502)
    _install_snapshot(session, 501, "https://workspace-a.test/rpc")
    _install_snapshot(
        session,
        502,
        "https://workspace-b.test/rpc",
        input_schema={
            "type": "object",
            "properties": {"term": {"type": "string"}},
            "required": ["term"],
        },
    )
    ready = asyncio.Event()
    registrations = 0

    async def resolve_in_context(scope):
        nonlocal registrations
        offered = register_extension_tools(session, scope)[0]
        registrations += 1
        if registrations == 2:
            ready.set()
        await ready.wait()
        resolved = tool_registry.get_tool_by_flat_name(offered.flat_name)
        return set(resolved.input_schema["properties"])

    props_a, props_b = await asyncio.gather(
        resolve_in_context(scope_a),
        resolve_in_context(scope_b),
    )

    assert props_a == {"query"}
    assert props_b == {"term"}


@pytest.mark.asyncio
async def test_company_chat_reuses_connector_governance_decision_exactly_once(session):
    scope = _scope(501)
    _install_snapshot(session, scope.workspace_id, "https://workspace-a.test/rpc")
    register_extension_tools(session, scope)

    with patch.object(
        GovernanceKernel,
        "evaluate_and_audit_tool_call",
        wraps=GovernanceKernel.evaluate_and_audit_tool_call,
    ) as evaluate, patch(
        "workforce.tools.invocation.service.MCPProvider.invoke",
        new_callable=AsyncMock,
        return_value=ProviderResult(status="success", result={"matches": ["Ada"]}),
    ):
        result = json.loads(await company_tools.execute_tool(
            session,
            scope.workspace_id,
            77,
            scope.principal_user_id,
            "com_cosa_mcp_tenant_safe_search",
            '{"query": "Ada"}',
        ))

    assert result == {"matches": ["Ada"]}
    assert evaluate.call_count == 1


@pytest.mark.asyncio
async def test_connector_protocol_failure_returns_generic_safe_error(session):
    scope = _scope(501)
    _install_snapshot(session, scope.workspace_id, "https://workspace-a.test/rpc")
    spec = register_extension_tools(session, scope)[0]
    decision = GovernanceDecision(
        allowed=True,
        action=PolicyAction.ALLOW,
        reason="already governed",
        tool_spec=spec,
        sanitized_args={"query": "Ada"},
    )
    request = ToolInvocationRequest(
        scope=scope,
        tool_flat_name=spec.flat_name,
        arguments={"query": "Ada"},
        source="test",
        governance_decision=decision,
    )

    with patch(
        "workforce.tools.invocation.service.MCPProvider.invoke",
        new_callable=AsyncMock,
        side_effect=ProviderProtocolError(
            "upstream https://user:secret@private-mcp.test/rpc"
        ),
    ):
        result = await ToolInvocationService().invoke(session, request)

    assert result.status == "error"
    assert result.error_message == "Connector provider request failed"
    assert "secret" not in result.error_message


@pytest.mark.asyncio
async def test_connector_dispatch_rejects_workspace_snapshot_semantic_mismatch(
    session,
):
    scope_a = _scope(501)
    scope_b = _scope(502)
    _install_snapshot(session, scope_a.workspace_id, "https://workspace-a.test/rpc")
    _install_snapshot(
        session,
        scope_b.workspace_id,
        "https://workspace-b.test/rpc",
        input_schema={
            "type": "object",
            "properties": {"term": {"type": "string"}},
            "required": ["term"],
        },
    )
    governed_spec = register_extension_tools(session, scope_a)[0]
    workspace_b_spec = register_extension_tools(session, scope_b)[0]
    assert set(workspace_b_spec.input_schema["properties"]) == {"term"}
    decision = GovernanceDecision(
        allowed=True,
        action=PolicyAction.ALLOW,
        reason="already governed",
        tool_spec=governed_spec,
        sanitized_args={"query": "Ada"},
    )
    request = ToolInvocationRequest(
        scope=scope_b,
        tool_flat_name=governed_spec.flat_name,
        arguments={"query": "Ada"},
        source="test",
        governance_decision=decision,
    )
    service = ToolInvocationService()
    service.policy_gate.execute_if_allowed = MagicMock()

    with patch(
        "workforce.tools.invocation.service.MCPProvider.invoke",
        new_callable=AsyncMock,
    ) as invoke:
        result = await service.invoke(session, request)

    assert result.status == "error"
    invoke.assert_not_awaited()
    service.policy_gate.execute_if_allowed.assert_not_called()
