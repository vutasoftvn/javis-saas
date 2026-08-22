"""G3 §9.6b: the capabilities router is mounted directly into `app.main`
(read-only fast win ahead of Phase 1B's full Capability Registry
consolidation). These tests lock in: the router is actually reachable
(distinguishing "mounted but needs auth" from "not mounted at all"), and
`/execute` stays off unless COSA_ENABLE_CAPABILITY_EXECUTE is explicitly set.
"""
import importlib

from fastapi.testclient import TestClient


def test_capabilities_catalog_route_is_mounted_and_requires_auth():
    from main import app

    client = TestClient(app)
    response = client.get("/api/v1/capabilities/catalog")
    # 401 (needs auth), not 404 (route doesn't exist) — proves the router is mounted.
    assert response.status_code == 401


def test_capability_execute_route_absent_by_default(monkeypatch):
    monkeypatch.delenv("COSA_ENABLE_CAPABILITY_EXECUTE", raising=False)
    import workforce.agents.capabilities.router as capabilities_router_module
    importlib.reload(capabilities_router_module)
    assert not any(getattr(r, "path", "") == "/execute" for r in capabilities_router_module.router.routes)


def test_capability_execute_route_present_when_flag_enabled(monkeypatch):
    monkeypatch.setenv("COSA_ENABLE_CAPABILITY_EXECUTE", "true")
    import workforce.agents.capabilities.router as capabilities_router_module
    importlib.reload(capabilities_router_module)
    assert any(getattr(r, "path", "") == "/execute" for r in capabilities_router_module.router.routes)

    # Leave the module in its default (flag-off) state for any other test
    # importing it later in the same process.
    monkeypatch.delenv("COSA_ENABLE_CAPABILITY_EXECUTE", raising=False)
    importlib.reload(capabilities_router_module)
