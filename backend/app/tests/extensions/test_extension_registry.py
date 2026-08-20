import pytest
from app.workforce.extensions.manifest import ManifestValidationError
from app.workforce.extensions.registry import ExtensionRegistry
from app.workforce.extensions.models import ExtensionRegistration

registry = ExtensionRegistry()

@pytest.fixture
def db():
    from app.db.session import SessionLocal
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()

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
