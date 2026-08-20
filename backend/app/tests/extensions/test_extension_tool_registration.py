from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import tool_registry
from app.core.toolset_resolver import resolve_toolset
from app.workforce.agents.governance.kernel import GovernanceDecision
from app.workforce.agents.governance.policy_engine import PolicyAction
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.extensions.models import ExtensionRegistration
from app.workforce.extensions.registry import ExtensionRegistry
from app.workforce.extensions.seams import DiscoveredCapability, ProviderResult
from app.workforce.extensions.tool_registration import register_extension_tools
from app.workforce.tools.invocation.contracts import ToolInvocationRequest
from app.workforce.tools.invocation.service import ToolInvocationService


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
        "capabilities": [{"id": CAPABILITY_ID, "name": "search"}],
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
    from app.db.session import SessionLocal

    db = SessionLocal()
    db.query(ExtensionRegistration).filter(
        ExtensionRegistration.workspace_id.in_((501, 502)),
        ExtensionRegistration.extension_id.in_(
            (EXTENSION_ID, *COLLISION_EXTENSION_IDS)
        ),
    ).delete(synchronize_session=False)
    db.commit()
    original_names = set(tool_registry._registry)
    yield db
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
    manifest["capabilities"] = [{"id": capability_id, "name": capability_name}]
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
        "app.workforce.tools.invocation.service.MCPProvider.invoke",
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
    assert register_extension_tools(session, scope_b) == []
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
        "app.workforce.tools.invocation.service.MCPProvider.invoke",
        new_callable=AsyncMock,
    ) as invoke:
        result = await service.invoke(session, request)

    assert result.status == "error"
    invoke.assert_not_awaited()
    service.policy_gate.execute_if_allowed.assert_not_called()
