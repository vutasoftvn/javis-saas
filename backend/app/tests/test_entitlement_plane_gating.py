"""G2 P0.2 / G3 §9.2: the entitlement-signing endpoint must never be
reachable on a company/local runtime — only on COSA_RUNTIME_PLANE=control.
Locks in the conditional route registration in platform/sync/router.py.
"""
import importlib

import pytest


@pytest.fixture
def fresh_sync_router_module():
    """Reimports platform.sync.router fresh so it picks up the current
    COSA_RUNTIME_PLANE env var (the module reads it once at import time)."""
    import app.platform.sync.router as sync_router_module
    importlib.reload(sync_router_module)
    yield sync_router_module
    # Restore default (company plane) state for any later test/import.
    import os
    os.environ.pop("COSA_RUNTIME_PLANE", None)
    importlib.reload(sync_router_module)


def test_entitlement_sign_absent_on_company_plane(monkeypatch, fresh_sync_router_module):
    monkeypatch.delenv("COSA_RUNTIME_PLANE", raising=False)
    import importlib as _importlib
    _importlib.reload(fresh_sync_router_module)
    paths = [r.path for r in fresh_sync_router_module.router.routes]
    assert "/sync/entitlement/sign" not in paths
    # Local-facing endpoints must still be present.
    assert "/sync/entitlement/refresh" in paths
    assert "/sync/entitlement/current" in paths


def test_entitlement_sign_present_on_control_plane(monkeypatch, fresh_sync_router_module):
    monkeypatch.setenv("COSA_RUNTIME_PLANE", "control")
    import importlib as _importlib
    _importlib.reload(fresh_sync_router_module)
    paths = [r.path for r in fresh_sync_router_module.router.routes]
    assert "/sync/entitlement/sign" in paths
