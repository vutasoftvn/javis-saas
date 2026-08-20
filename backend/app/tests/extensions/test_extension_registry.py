import pytest
from app.workforce.extensions.manifest import ManifestValidationError
from app.workforce.extensions.registry import ExtensionRegistry
from app.workforce.extensions.models import ExtensionRegistration
from app.workforce.extensions.seams import DiscoveredCapability

registry = ExtensionRegistry()

@pytest.fixture
def db():
    from app.db.session import SessionLocal
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def installed_registration(db):
    registration = ExtensionRegistry().install(db, 1, {
        "extension_id": "com.cosa.crm", "version": "1.0.0", "compatibility": ">=1",
        "trust_level": "first_party", "owner": "cosa", "capabilities": (),
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
