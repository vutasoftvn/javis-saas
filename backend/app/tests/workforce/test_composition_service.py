import pytest
from app.workforce.composition.service import ProfileCompositionService
from app.workforce.agents.profiles.schemas import AgentProfile
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.db.session import SessionLocal
from app.workforce.extensions.models import ExtensionRegistration
from app.workforce.extensions.registry import ExtensionRegistry


@pytest.fixture
def session():
    db = SessionLocal()
    db.query(ExtensionRegistration).delete()
    db.commit()
    yield db
    db.query(ExtensionRegistration).delete()
    db.commit()
    db.close()

@pytest.fixture
def base_profile():
    return AgentProfile(
        id="sales",
        name="Sales",
        role="Sales",
        description="Sales agent",
        tools=["crm.read", "core.search", "ext.notion.create"],
        skills=["skill_sales_pitch"],
        permissions=["sales.read", "crm.read"],
        model_policy={"default": "reasoning"}
    )

@pytest.fixture
def mock_execution_scope():
    return ExecutionScope(
        workspace_id=1,
        company_id=1,
        principal_user_id=1,
        principal_member_id=1,
        principal_role="member",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=("sales.read", "core.basic")  # Lacks crm.read
    )


def save_eligible_capability(session, extension_id, capability_id, name, *, required_secret_refs=()):
    registration = ExtensionRegistry().install(session, 1, {
        "extension_id": extension_id,
        "version": "1.0.0",
        "compatibility": ">=1.0.0",
        "trust_level": "first_party",
        "owner": "system",
        "capabilities": [{
            "id": capability_id,
            "name": name,
            "risk_level": "low",
            "permission_level": "read_only",
            "requires_approval": False,
            "mutating": False,
            "external": False,
        }],
        "required_permissions": [],
        "required_secret_refs": list(required_secret_refs),
        "supported_scope_levels": ["company"],
        "health_check": {"type": "ping"},
        "disable_behavior": "block_new_calls_preserve_history",
        "provider_type": "mcp",
        "provider_config": {"endpoint": "https://mcp.test/rpc"},
    })
    registration.status = "enabled"
    registration.health_jsonb = {"status": "ok"}
    registration.capabilities_jsonb = {
        "provider": "mcp",
        "endpoint_config": {"endpoint": "https://mcp.test/rpc"},
        "capabilities": [{
            "capability_id": capability_id,
            "name": name,
            "endpoint_config": {"endpoint": "https://mcp.test/rpc"},
        }],
    }
    session.commit()


def test_profile_exposes_only_eligible_extension_tool(
    session, base_profile, mock_execution_scope
):
    save_eligible_capability(
        session, "com.cosa.crm", "com.cosa.crm:search", "search"
    )
    base_profile.tools = ["ext.com_cosa_crm_search"]

    resolved = ProfileCompositionService().resolve(
        base_profile, mock_execution_scope, session
    )

    assert resolved.visible_tool_ids == ["ext.com_cosa_crm_search"]


def test_profile_explains_secret_unavailable_extension(
    session, base_profile, mock_execution_scope
):
    save_eligible_capability(
        session,
        "com.cosa.jira",
        "com.cosa.jira:create_issue",
        "create_issue",
        required_secret_refs=("jira_api_token",),
    )
    base_profile.tools = ["ext.com_cosa_jira_create_issue"]

    resolved = ProfileCompositionService().resolve(
        base_profile, mock_execution_scope, session
    )

    explanation = next(
        item
        for item in resolved.explanations
        if item.item_id == "ext.com_cosa_jira_create_issue"
    )
    assert explanation.reason_code == "SECRET_UNAVAILABLE"


def test_resolve_profile_requires_grant_for_native_permission(
    session, base_profile, mock_execution_scope
):
    """
    Test crm.read bị loại bỏ vì scope không có crm.read grant.
    """
    service = ProfileCompositionService()
    resolved = service.resolve(base_profile, mock_execution_scope, session)
    
    assert "crm.read" not in resolved.visible_tool_ids
    
    # Tìm explanation
    expl = next((e for e in resolved.explanations if e.item_id == "crm.read"), None)
    assert expl is not None
    assert expl.reason_code == "SCOPE"

def test_resolve_profile_keeps_native_tool_without_profile_permission(
    session, base_profile, mock_execution_scope
):
    """
    Native tools not declared as profile permissions remain visible.
    """
    base_profile.tools = ["core.search"]
    service = ProfileCompositionService()
    resolved = service.resolve(base_profile, mock_execution_scope, session)
    
    assert resolved.visible_tool_ids == ["core.search"]
