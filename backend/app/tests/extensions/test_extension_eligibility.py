import pytest
from app.workforce.extensions.eligibility import resolve_eligible_capabilities
from app.workforce.extensions.registry import ExtensionRegistry
from app.workforce.agents.runtime.execution_scope import ExecutionScope

@pytest.fixture
def db():
    from app.db.session import SessionLocal
    from app.workforce.extensions.models import ExtensionRegistration
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
        "capabilities": [{"id": "github:search", "name": "Search"}],
        "required_permissions": [],
        "required_secret_refs": [],
        "supported_scope_levels": ["company", "operating_unit"],
        "health_check": {"type": "ping"},
        "disable_behavior": "block_new_calls_preserve_history"
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
        "capabilities": [{"id": "jira:create", "name": "Create Issue"}],
        "required_permissions": [],
        "required_secret_refs": ["jira_api_token"],
        "supported_scope_levels": ["company"],
        "health_check": {"type": "ping"},
        "disable_behavior": "block_new_calls_preserve_history"
    }
    return registry.install(db, 101, manifest)


def test_disabled_extension_is_not_eligible(db, registry, enabled_scope, installed_extension):
    registry.disable(db, enabled_scope.workspace_id, installed_extension.extension_id, "operator disabled")
    assert resolve_eligible_capabilities(db, enabled_scope) == ()

def test_missing_secret_returns_reason_without_secret_value(db, enabled_scope, extension_requiring_secret):
    result = resolve_eligible_capabilities(db, enabled_scope)
    assert len(result) == 1
    assert result[0].eligible is False
    assert result[0].reason_code == "SECRET_UNAVAILABLE"
    assert "jira_api_token" not in result[0].model_dump_json().lower()

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
    result = resolve_eligible_capabilities(db, initiative_scope)
    assert len(result) == 1
    assert result[0].eligible is False
    assert result[0].reason_code == "SCOPE_MISMATCH"
