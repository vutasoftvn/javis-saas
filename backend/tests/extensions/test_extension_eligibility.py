import pytest
from workforce.extensions.eligibility import resolve_eligible_capabilities
from workforce.extensions.registry import ExtensionRegistry
from workforce.agents.runtime.execution_scope import ExecutionScope


def governed_capability(capability_id, name):
    return {
        "id": capability_id,
        "name": name,
        "risk_level": "low",
        "permission_level": "read_only",
        "requires_approval": False,
        "mutating": False,
        "external": False,
    }

@pytest.fixture
def db():
    from db.session import SessionLocal
    from workforce.extensions.models import ExtensionRegistration
    session = SessionLocal()
    session.query(ExtensionRegistration).delete()
    session.commit()
    yield session
    session.query(ExtensionRegistration).delete()
    session.commit()
    session.close()

@pytest.fixture
def registry():
    return ExtensionRegistry()

@pytest.fixture
def enabled_scope():
    return ExecutionScope(
        workspace_id=101,
        company_id=101,
        principal_user_id=1,
        principal_member_id=1,
        principal_role="owner",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=()
    )

@pytest.fixture
def installed_extension(db, registry):
    manifest = {
        "extension_id": "com.cosa.mcp.github",
        "version": "1.0.0",
        "compatibility": ">=1.0.0",
        "trust_level": "first_party",
        "owner": "system",
        "capabilities": [governed_capability(
            "com.cosa.mcp.github:search", "Search"
        )],
        "required_permissions": [],
        "required_secret_refs": [],
        "supported_scope_levels": ["company", "operating_unit"],
        "health_check": {"type": "ping"},
        "disable_behavior": "block_new_calls_preserve_history",
        "provider_type": "mcp",
        "provider_config": {"endpoint": "https://mcp.test/rpc"},
    }
    return registry.install(db, 101, manifest)

@pytest.fixture
def extension_requiring_secret(db, registry):
    manifest = {
        "extension_id": "com.cosa.mcp.jira",
        "version": "1.0.0",
        "compatibility": ">=1.0.0",
        "trust_level": "first_party",
        "owner": "system",
        "capabilities": [governed_capability(
            "com.cosa.mcp.jira:create_issue", "Create Issue"
        )],
        "required_permissions": [],
        "required_secret_refs": ["jira_api_token"],
        "supported_scope_levels": ["company"],
        "health_check": {"type": "ping"},
        "disable_behavior": "block_new_calls_preserve_history",
        "provider_type": "mcp",
        "provider_config": {"endpoint": "https://mcp.test/rpc"},
    }
    return registry.install(db, 101, manifest)


def save_snapshot(db, registration, capabilities):
    registration.status = "enabled"
    registration.health_jsonb = {"status": "ok"}
    registration.capabilities_jsonb = {
        "provider": "mcp",
        "endpoint_config": {"endpoint": "https://mcp.test/rpc"},
        "capabilities": capabilities,
    }
    db.commit()


def test_eligibility_uses_discovered_snapshot_not_manifest(db, enabled_scope, installed_extension):
    save_snapshot(db, installed_extension, [{
        "capability_id": "com.cosa.mcp.github:search",
        "name": "search",
        "endpoint_config": {"endpoint": "https://mcp.test/rpc"},
        "input_schema": {"type": "object"},
        "output_schema": {"type": "string"},
    }])

    result = resolve_eligible_capabilities(db, enabled_scope)

    assert [capability.capability_id for capability in result] == [
        "com.cosa.mcp.github:search"
    ]
    assert result[0].extension_id == "com.cosa.mcp.github"
    assert result[0].input_schema == {"type": "object"}
    assert result[0].output_schema == {"type": "string"}
    assert result[0].required_secret_refs == ()
    assert result[0].risk_level == "low"
    assert result[0].permission_level == "read_only"
    assert result[0].requires_approval is False
    assert result[0].mutating is False
    assert result[0].external is False


def test_eligibility_is_empty_without_discovery_snapshot(db, enabled_scope, installed_extension):
    installed_extension.status = "enabled"
    installed_extension.health_jsonb = {"status": "ok"}
    installed_extension.capabilities_jsonb = None
    db.commit()

    assert resolve_eligible_capabilities(db, enabled_scope) == ()


def test_disabled_extension_is_not_eligible(db, registry, enabled_scope, installed_extension):
    registry.disable(db, enabled_scope.workspace_id, installed_extension.extension_id, "operator disabled")
    assert resolve_eligible_capabilities(db, enabled_scope) == ()

def test_missing_secret_returns_reason_and_required_secret_refs(db, enabled_scope, extension_requiring_secret):
    save_snapshot(db, extension_requiring_secret, [{
        "capability_id": "com.cosa.mcp.jira:create_issue",
        "name": "create_issue",
        "endpoint_config": {"endpoint": "https://mcp.test/rpc"},
    }])
    result = resolve_eligible_capabilities(db, enabled_scope)
    assert len(result) == 1
    assert result[0].eligible is False
    assert result[0].reason_code == "SECRET_UNAVAILABLE"
    assert result[0].required_secret_refs == ("jira_api_token",)

def test_scope_mismatch_returns_ineligible(db, installed_extension):
    # Extension only supports company and operating_unit
    initiative_scope = ExecutionScope(
        workspace_id=101,
        company_id=101,
        principal_user_id=1,
        principal_member_id=1,
        principal_role="owner",
        operating_unit_id=1,
        offering_id=1,
        initiative_id=1,
        profile_id=None,
        session_id=None,
        grants=()
    )
    save_snapshot(db, installed_extension, [{
        "capability_id": "com.cosa.mcp.github:search",
        "name": "search",
        "endpoint_config": {"endpoint": "https://mcp.test/rpc"},
    }])

    result = resolve_eligible_capabilities(db, initiative_scope)
    assert len(result) == 1
    assert result[0].eligible is False
    assert result[0].reason_code == "SCOPE_MISMATCH"


def test_missing_capability_governance_metadata_fails_closed(
    db, enabled_scope, installed_extension
):
    installed_extension.manifest_jsonb = {
        **installed_extension.manifest_jsonb,
        "capabilities": [{
            "id": "com.cosa.mcp.github:search",
            "name": "Search",
        }],
    }
    save_snapshot(db, installed_extension, [{
        "capability_id": "com.cosa.mcp.github:search",
        "name": "search",
        "endpoint_config": {"endpoint": "https://mcp.test/rpc"},
        "input_schema": {"type": "object"},
    }])

    result = resolve_eligible_capabilities(db, enabled_scope)

    assert len(result) == 1
    assert result[0].eligible is False
    assert result[0].reason_code == "GOVERNANCE_METADATA_UNAVAILABLE"


def test_malformed_snapshot_record_invalidates_entire_snapshot(
    db, enabled_scope, installed_extension
):
    save_snapshot(db, installed_extension, [
        {
            "capability_id": "com.cosa.mcp.github:search",
            "name": "search",
            "endpoint_config": {"endpoint": "https://mcp.test/rpc"},
            "input_schema": {"type": "object"},
        },
        {
            "capability_id": "com.cosa.mcp.github:bad name",
            "name": "bad name",
            "endpoint_config": {},
        },
    ])

    assert resolve_eligible_capabilities(db, enabled_scope) == ()


def test_snapshot_without_trusted_endpoint_fails_closed(
    db, enabled_scope, installed_extension
):
    save_snapshot(db, installed_extension, [{
        "capability_id": "com.cosa.mcp.github:search",
        "name": "search",
        "endpoint_config": {},
    }])
    installed_extension.capabilities_jsonb["endpoint_config"] = {}
    db.commit()

    assert resolve_eligible_capabilities(db, enabled_scope) == ()
