import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger
from workforce.extensions.manifest import ManifestValidationError
from workforce.extensions.registry import ExtensionRegistry
from workforce.extensions.models import ExtensionRegistration
from workforce.extensions.seams import DiscoveredCapability
from workforce.extensions.contracts import ProviderProtocolError
from workforce.extensions.router import router as extension_router
from workforce.extensions.router import MCPProvider
from db.session import get_db
from core.auth import get_current_workspace_member

registry = ExtensionRegistry()


def governed_capability(capability_id="com.cosa.crm:search", name="search"):
    return {
        "id": capability_id,
        "name": name,
        "risk_level": "low",
        "permission_level": "read_only",
        "requires_approval": False,
        "mutating": False,
        "external": False,
    }


def test_extension_registration_workspace_id_uses_snowflake_width():
    assert isinstance(
        ExtensionRegistration.__table__.c.workspace_id.type, BigInteger
    )

@pytest.fixture
def db():
    from db.session import SessionLocal
    session = SessionLocal()
    # This suite runs against a real, shared Postgres DB (no per-test transaction
    # rollback) - a registration left by another test/file leaks into
    # unfiltered listing queries and makes result ordering nondeterministic.
    session.query(ExtensionRegistration).delete()
    session.commit()
    yield session
    session.rollback()
    session.query(ExtensionRegistration).delete()
    session.commit()
    session.close()


@pytest.fixture
def installed_registration(db):
    registration = ExtensionRegistry().install(db, 1, {
        "extension_id": "com.cosa.crm", "version": "1.0.0", "compatibility": ">=1",
        "trust_level": "first_party", "owner": "cosa",
        "capabilities": (governed_capability(),),
        "required_permissions": (), "required_secret_refs": (),
        "supported_scope_levels": ("company",), "health_check": {"type": "mcp"},
        "disable_behavior": "block_new_calls_preserve_history",
        "provider_type": "mcp", "provider_config": {"endpoint": "https://mcp.test/rpc"},
    })
    registration.status = "installed"
    registration.disabled_reason = None
    registration.capabilities_jsonb = None
    db.commit()
    yield registration
    registration.status = "installed"
    registration.disabled_reason = None
    registration.capabilities_jsonb = None
    db.commit()

def test_registry_rejects_non_first_party_manifest(db):
    with pytest.raises(ManifestValidationError, match="first_party"):
        registry.install(db, workspace_id=101, manifest={"extension_id": "org.x", "trust_level": "community"})

def test_registry_preserves_manifest_version_when_disabled(db):
    manifest = {
        "extension_id": "com.cosa.mcp.github",
        "version": "1.0.0",
        "compatibility": ">=1.0.0",
        "trust_level": "first_party",
        "owner": "system",
        "capabilities": [],
        "required_permissions": [],
        "required_secret_refs": [],
        "supported_scope_levels": ["company"],
        "health_check": {"type": "ping"},
        "disable_behavior": "block_new_calls_preserve_history",
        "provider_type": "mcp",
        "provider_config": {"endpoint": "https://mcp.test/rpc"},
    }
    
    registration = registry.install(db, 101, manifest)
    registry.disable(db, 101, registration.extension_id, "maintenance")
    assert registry.get(db, 101, registration.extension_id).manifest_jsonb["version"] == manifest["version"]


def test_install_accepts_first_party_mcp_provider_config(db):
    registration = ExtensionRegistry().install(db, 1, {
        "extension_id": "com.cosa.crm", "version": "1.0.0", "compatibility": ">=1",
        "trust_level": "first_party", "owner": "cosa", "capabilities": (),
        "required_permissions": (), "required_secret_refs": (),
        "supported_scope_levels": ("company",), "health_check": {"type": "mcp"},
        "disable_behavior": "block_new_calls_preserve_history",
        "provider_type": "mcp", "provider_config": {"endpoint": "https://mcp.test/rpc"},
    })
    assert registration.capabilities_jsonb is None
    assert registration.manifest_jsonb["provider_config"]["endpoint"] == "https://mcp.test/rpc"


def test_manifest_capability_governance_metadata_is_required(db):
    with pytest.raises(ManifestValidationError) as exc_info:
        ExtensionRegistry().install(db, 1, {
            "extension_id": "com.cosa.unsafe",
            "version": "1.0.0",
            "compatibility": ">=1",
            "trust_level": "first_party",
            "owner": "cosa",
            "capabilities": [{"id": "com.cosa.unsafe:send", "name": "send"}],
            "required_permissions": (),
            "required_secret_refs": (),
            "supported_scope_levels": ("company",),
            "health_check": {"type": "mcp"},
            "disable_behavior": "block_new_calls_preserve_history",
            "provider_type": "mcp",
            "provider_config": {"endpoint": "https://mcp.test/rpc"},
        })

    message = str(exc_info.value)
    assert "risk_level" in message
    assert "permission_level" in message
    assert "requires_approval" in message
    assert "mutating" in message
    assert "external" in message


def test_install_invalidates_capability_snapshot_when_provider_config_changes(db):
    manifest = {
        "extension_id": "com.cosa.snapshot-test", "version": "1.0.0", "compatibility": ">=1",
        "trust_level": "first_party", "owner": "cosa", "capabilities": (),
        "required_permissions": (), "required_secret_refs": (),
        "supported_scope_levels": ("company",), "health_check": {"type": "mcp"},
        "disable_behavior": "block_new_calls_preserve_history",
        "provider_type": "mcp", "provider_config": {"endpoint": "https://mcp.test/rpc"},
    }
    registration = ExtensionRegistry().install(db, 1, manifest)
    registration.capabilities_jsonb = {"tools": ["create_contact"]}
    db.commit()

    manifest["provider_config"] = {"endpoint": "https://mcp.test/v2/rpc"}
    registration = ExtensionRegistry().install(db, 1, manifest)

    assert registration.capabilities_jsonb is None


def test_enable_clears_disabled_reason(db, installed_registration):
    installed_registration.status = "disabled"
    installed_registration.disabled_reason = "operator disabled"
    db.commit()

    enabled = ExtensionRegistry().enable(db, installed_registration.workspace_id, installed_registration.extension_id)

    assert enabled.status == "enabled"
    assert enabled.disabled_reason is None


def test_record_discovery_keeps_manifest_and_stores_snapshot(db, installed_registration):
    manifest_before = dict(installed_registration.manifest_jsonb)

    saved = ExtensionRegistry().record_discovery(db, 1, "com.cosa.crm", [
        DiscoveredCapability(
            capability_id="com.cosa.crm:search",
            name="search",
            endpoint_config={"endpoint": "https://mcp.test/rpc"},
        )
    ])

    assert saved.manifest_jsonb == manifest_before
    assert saved.capabilities_jsonb["capabilities"][0]["name"] == "search"
    assert saved.capabilities_jsonb["provider"] == "mcp"
    assert saved.capabilities_jsonb["endpoint_config"] == {
        "endpoint": "https://mcp.test/rpc"
    }


def test_get_capability_returns_discovered_snapshot_capability(db, installed_registration):
    ExtensionRegistry().record_discovery(db, 1, "com.cosa.crm", [
        DiscoveredCapability(
            capability_id="com.cosa.crm:search",
            name="search",
            endpoint_config={"endpoint": "https://mcp.test/rpc"},
        )
    ])

    capability = ExtensionRegistry().get_capability(db, 1, "com.cosa.crm:search")

    assert capability == DiscoveredCapability(
        capability_id="com.cosa.crm:search",
        name="search",
        endpoint_config={"endpoint": "https://mcp.test/rpc"},
    )


def test_enable_raises_lookup_error_for_an_absent_registration(db):
    with pytest.raises(LookupError):
        ExtensionRegistry().enable(db, 1, "com.cosa.missing")


def test_get_capability_ignores_malformed_snapshot_data(db, installed_registration):
    installed_registration.status = "enabled"
    installed_registration.capabilities_jsonb = {"capabilities": None}
    db.commit()

    assert ExtensionRegistry().get_capability(db, 1, "com.cosa.crm:search") is None


def test_record_discovery_rejects_invalid_records_atomically(db, installed_registration):
    ExtensionRegistry().record_discovery(db, 1, "com.cosa.crm", [
        DiscoveredCapability(
            capability_id="com.cosa.crm:search",
            name="search",
            endpoint_config={"endpoint": "https://mcp.test/rpc"},
        )
    ])
    snapshot_before = dict(installed_registration.capabilities_jsonb)

    with pytest.raises(ProviderProtocolError, match="Invalid MCP discovery payload"):
        ExtensionRegistry().record_discovery(db, 1, "com.cosa.crm", [
            {
                "capability_id": "com.cosa.crm:bad name",
                "name": "bad name",
                "endpoint_config": {},
            }
        ])

    db.refresh(installed_registration)
    assert installed_registration.capabilities_jsonb == snapshot_before


def test_record_discovery_rejects_capability_that_cannot_form_flat_name(
    db, installed_registration
):
    long_name = "x" * 60

    with pytest.raises(ProviderProtocolError, match="Invalid MCP discovery payload"):
        ExtensionRegistry().record_discovery(db, 1, "com.cosa.crm", [
            DiscoveredCapability(
                capability_id=f"com.cosa.crm:{long_name}",
                name=long_name,
                endpoint_config={"endpoint": "https://mcp.test/rpc"},
            )
        ])

    assert installed_registration.capabilities_jsonb is None


def extension_client(db, member=None):
    app = FastAPI()
    app.include_router(extension_router)
    app.dependency_overrides[get_db] = lambda: db
    member = member or type(
        "Member",
        (),
        {"id": 17, "user_id": 7, "workspace_id": 1, "role": "admin"},
    )()
    app.dependency_overrides[get_current_workspace_member] = lambda: member
    return TestClient(app, raise_server_exceptions=False)


def test_discovery_route_returns_no_provider_configuration(db, installed_registration, monkeypatch):
    async def discover(self, scope, config):
        assert scope.workspace_id == 1
        assert scope.principal_user_id == 7
        assert scope.principal_member_id == 17
        assert scope.principal_role == "admin"
        return (DiscoveredCapability(
            capability_id="com.cosa.crm:search",
            name="search",
            endpoint_config={"endpoint": "https://private-mcp.test/rpc", "extension_id": "com.cosa.crm"},
        ),)

    monkeypatch.setattr(MCPProvider, "discover", discover)

    response = extension_client(db).post("/api/v1/workspaces/1/extensions/com.cosa.crm/discover")

    assert response.status_code == 200
    assert response.json() == {
        "extension_id": "com.cosa.crm",
        "status": "enabled",
        "capability_count": 1,
    }
    assert "endpoint_config" not in response.text
    assert "private-mcp.test" not in response.text


def test_discovery_route_hides_provider_failure_detail(db, installed_registration, monkeypatch):
    async def discover(self, scope, config):
        raise ProviderProtocolError("upstream payload: https://private-mcp.test/rpc")

    monkeypatch.setattr(MCPProvider, "discover", discover)

    response = extension_client(db).post("/api/v1/workspaces/1/extensions/com.cosa.crm/discover")

    assert response.status_code == 502
    assert response.json() == {"detail": "Extension discovery failed"}
    assert "private-mcp.test" not in response.text
    assert installed_registration.capabilities_jsonb is None
    assert installed_registration.health_jsonb == {"status": "unavailable"}


def test_listing_uses_sanitized_snapshot_capabilities_not_manifest(
    db, installed_registration
):
    installed_registration.manifest_jsonb["capabilities"][0]["name"] = "Manifest label"
    db.commit()
    ExtensionRegistry().record_discovery(db, 1, "com.cosa.crm", [
        DiscoveredCapability(
            capability_id="com.cosa.crm:search",
            name="search",
            description="Discovered search",
            endpoint_config={"endpoint": "https://mcp.test/rpc"},
        )
    ])

    response = extension_client(db).get("/api/v1/workspaces/1/extensions")

    assert response.status_code == 200
    assert response.json()["extensions"][0]["capabilities"] == [{
        "id": "com.cosa.crm:search",
        "name": "search",
        "eligible": True,
        "reason_code": None,
    }]
    assert "Manifest label" not in response.text
    assert "mcp.test" not in response.text


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/api/v1/workspaces/1/extensions", None),
        (
            "post",
            "/api/v1/workspaces/1/extensions/com.cosa.crm/status",
            {"status": "disabled"},
        ),
        (
            "post",
            "/api/v1/workspaces/1/extensions/com.cosa.crm/discover",
            None,
        ),
    ],
)
def test_extension_routes_reject_cross_workspace_member(
    db, installed_registration, method, path, body
):
    other_workspace_member = type(
        "Member",
        (),
        {"id": 27, "user_id": 7, "workspace_id": 2, "role": "owner"},
    )()

    response = extension_client(db, other_workspace_member).request(
        method, path, json=body
    )

    assert response.status_code == 403


def test_extension_routes_require_owner_or_admin_role(db, installed_registration):
    regular_member = type(
        "Member",
        (),
        {"id": 17, "user_id": 7, "workspace_id": 1, "role": "member"},
    )()

    response = extension_client(db, regular_member).get(
        "/api/v1/workspaces/1/extensions"
    )

    assert response.status_code == 403


def test_status_route_accepts_only_enabled_or_disabled(db, installed_registration):
    response = extension_client(db).post(
        "/api/v1/workspaces/1/extensions/com.cosa.crm/status",
        json={"status": "installed"},
    )

    assert response.status_code == 422
