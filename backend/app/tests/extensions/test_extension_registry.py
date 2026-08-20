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
        "disable_behavior": "block_new_calls_preserve_history"
    }
    
    registration = registry.install(db, 101, manifest)
    registry.disable(db, 101, registration.extension_id, "maintenance")
    assert registry.get(db, 101, registration.extension_id).manifest_jsonb["version"] == manifest["version"]
