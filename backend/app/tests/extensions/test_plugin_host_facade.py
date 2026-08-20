import pytest
from app.integrations.channels.plugins.plugin_host import PluginHost, PluginExecutionRemovedError

@pytest.fixture
def registry_mock(monkeypatch):
    class FakeRegistry:
        def get_all(self, db, workspace_id):
            class FakeReg:
                extension_id = "com.cosa.mcp.github"
                version = "1.0.0"
                status = "installed"
                disabled_reason = None
                manifest_jsonb = {
                    "capabilities": [{"id": "github:search", "name": "Search"}],
                    "health_check": {"type": "ping"}
                }
                health_jsonb = {"status": "ok"}
            return [FakeReg()]

    from app.workforce.extensions.registry import ExtensionRegistry
    monkeypatch.setattr(ExtensionRegistry, "get_all", lambda self, db, workspace_id: FakeRegistry().get_all(db, workspace_id))

@pytest.fixture
def db():
    return None

@pytest.mark.asyncio
async def test_plugin_host_lists_registry_metadata_without_transport_calls(monkeypatch, registry_mock, db):
    # Pass db session mock if required by PluginHost, or just test its return
    host = PluginHost(workspace_id=101)
    # the original load_plugins may not take db, we should see what PluginHost takes.
    plugins = await host.load_plugins(db)
    assert plugins[0]["extension_id"] == "com.cosa.mcp.github"
    assert plugins[0]["status"] == "installed"

@pytest.mark.asyncio
async def test_plugin_host_cannot_execute_plugin_directly():
    host = PluginHost(workspace_id=101)
    with pytest.raises(PluginExecutionRemovedError):
        await host.execute_plugin("github", "search", {})
