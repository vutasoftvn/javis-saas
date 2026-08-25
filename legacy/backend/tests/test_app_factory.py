"""Tests cho COSA app factory (Quyết định 3 - self-host + central control-plane
role split). Xem docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md,
Quyết định 3.
"""
import importlib
import subprocess
import sys
from pathlib import Path
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]  # tests -> backend


def test_resolve_app_role_defaults_to_full_when_unset():
    from bootstrap.create_app import resolve_app_role, FULL_ROLE

    assert resolve_app_role({}) == FULL_ROLE


def test_resolve_app_role_defaults_to_full_when_blank():
    from bootstrap.create_app import resolve_app_role, FULL_ROLE

    assert resolve_app_role({"APP_ROLE": "   "}) == FULL_ROLE


def test_resolve_app_role_accepts_central_control_plane():
    from bootstrap.create_app import resolve_app_role, CENTRAL_CONTROL_PLANE_ROLE

    assert resolve_app_role({"APP_ROLE": "central_control_plane"}) == CENTRAL_CONTROL_PLANE_ROLE
    assert resolve_app_role({"APP_ROLE": " Central_Control_Plane "}) == CENTRAL_CONTROL_PLANE_ROLE


def test_resolve_app_role_rejects_unknown_value():
    from bootstrap.create_app import resolve_app_role

    with pytest.raises(ValueError, match="Unknown APP_ROLE"):
        resolve_app_role({"APP_ROLE": "central"})


def _run_role_probe(role: str, forbidden_prefixes: tuple, required_modules: tuple) -> None:
    """Spawn 1 process `python` mới, build create_app(role), rồi kiểm tra
    những module `app.*` nào đã lọt vào sys.modules. Bắt buộc chạy ở process
    riêng - 1 module đã bị import ở bất kỳ đâu trong cùng phiên pytest sẽ ở
    lại sys.modules cho tới hết process đó, khiến check "X có bị import
    không" trong cùng process pass/fail tuỳ thứ tự chạy test chứ không phải
    tuỳ hành vi thật của create_app().
    """
    script = (
        "import sys\n"
        "from bootstrap.create_app import create_app\n"
        f"create_app({role!r})\n"
        f"required = {list(required_modules)!r}\n"
        f"forbidden_prefixes = {list(forbidden_prefixes)!r}\n"
        "missing = [m for m in required if m not in sys.modules]\n"
        "leaked = [m for m in sys.modules if any(m.startswith(p) for p in forbidden_prefixes)]\n"
        "assert not missing, f'expected imported, missing: {missing}'\n"
        "assert not leaked, f'unexpectedly imported: {leaked}'\n"
        "print('PROBE_OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "PROBE_OK" in result.stdout


def test_full_role_imports_every_domain_router_module():
    _run_role_probe(
        role="full",
        forbidden_prefixes=(),
        required_modules=(
            "founder_os.router",
            "business.router",
            "workforce.router",
            "integrations.router",
            "platform_core.router",
            "workforce.agents.capabilities.router",
            "workforce.agents.delegation.router",
        ),
    )


def test_central_control_plane_role_only_imports_platform_sync_router():
    _run_role_probe(
        role="central_control_plane",
        forbidden_prefixes=(
            "founder_os",
            "business",
            "workforce",
            "integrations",
            "platform_core.router",
        ),
        required_modules=("platform_core.sync.router",),
    )


def _route_paths(app) -> list:
    paths = []
    def _collect(router, prefix=""):
        for r in getattr(router, "routes", []):
            if hasattr(r, "path") and r.path is not None:
                paths.append(prefix + r.path)
            elif hasattr(r, "original_router"):
                inc_prefix = getattr(getattr(r, "include_context", None), "prefix", "")
                _collect(r.original_router, prefix + inc_prefix)
            elif hasattr(r, "routes"):
                _collect(r, prefix)
    _collect(app)
    return paths


def test_full_role_mounts_all_five_domain_prefixes():
    from bootstrap.create_app import create_app

    app = create_app("full")
    paths = _route_paths(app)

    assert any(p.startswith("/api/v1/auth") for p in paths)
    assert any(p.startswith("/api/v1/vault") for p in paths)
    assert any(p.startswith("/api/v1/company-runtime") for p in paths)
    assert any(p.startswith("/api/v1/organization") for p in paths)
    assert any(p.startswith("/api/v1/capabilities") for p in paths)
    assert any(p.startswith("/api/v1/agents/delegations") for p in paths)
    assert any(p.startswith("/api/v1/platform/sync") for p in paths)


def test_central_control_plane_role_mounts_only_platform_sync():
    from bootstrap.create_app import create_app

    app = create_app("central_control_plane")
    paths = _route_paths(app)

    assert any(p.startswith("/api/v1/platform/sync") for p in paths)
    assert not any(p.startswith("/api/v1/auth") for p in paths)
    assert not any(p.startswith("/api/v1/vault") for p in paths)
    assert not any(p.startswith("/api/v1/company-runtime") for p in paths)
    assert not any(p.startswith("/api/v1/organization") for p in paths)
    assert not any(p.startswith("/api/v1/capabilities") for p in paths)
    assert not any(p.startswith("/api/v1/agents/delegations") for p in paths)


def test_full_role_lifespan_runs_all_four_startup_hooks(monkeypatch):
    from unittest.mock import MagicMock
    from fastapi.testclient import TestClient

    mcb_module = importlib.import_module("workforce.agents.orchestration.mission_control_bus")

    ensure_bucket = MagicMock()
    load_snapshots = MagicMock()
    seed_registry = MagicMock()
    register_listeners = MagicMock()

    monkeypatch.setattr("integrations.storage.s3_client.ensure_bucket_exists", ensure_bucket)
    monkeypatch.setattr(
        "platform_core.sync.entitlement_manager.load_all_current_snapshots_into_cache", load_snapshots
    )
    monkeypatch.setattr(
        "founder_os.strategy.services.capability_registry_seed_service."
        "seed_canonical_capability_registry",
        seed_registry,
    )
    monkeypatch.setattr(mcb_module, "register_default_listeners", register_listeners)

    from bootstrap.create_app import create_app

    app = create_app("full")
    with TestClient(app):
        pass

    ensure_bucket.assert_called_once()
    load_snapshots.assert_called_once()
    seed_registry.assert_called_once()
    register_listeners.assert_called_once()


def test_central_control_plane_lifespan_is_a_noop(monkeypatch):
    from unittest.mock import MagicMock
    from fastapi.testclient import TestClient

    ensure_bucket = MagicMock()
    monkeypatch.setattr("integrations.storage.s3_client.ensure_bucket_exists", ensure_bucket)

    from bootstrap.create_app import create_app

    app = create_app("central_control_plane")
    with TestClient(app):
        pass

    ensure_bucket.assert_not_called()


def test_full_role_ready_probe_reports_four_checks():
    from fastapi.testclient import TestClient
    from bootstrap.create_app import create_app

    app = create_app("full")
    response = TestClient(app).get("/ready")

    assert set(response.json()["checks"].keys()) == {"database", "storage", "migrations", "worker"}


def test_central_control_plane_ready_probe_only_checks_database():
    from fastapi.testclient import TestClient
    from bootstrap.create_app import create_app

    app = create_app("central_control_plane")
    response = TestClient(app).get("/ready")

    assert set(response.json()["checks"].keys()) == {"database"}


_FULL_MAIN_DELETED_REASON = (
    "full_main.py/central_main.py đã bị xoá ở commit 448c1981 (2026-08-24); "
    "legacy/backend frozen-in-place theo ADR-012, xem "
    "docs/architecture/legacy_backend_capability_audit_2026-08-25.md"
)


@pytest.mark.skip(reason=_FULL_MAIN_DELETED_REASON)
def test_full_main_app_has_full_role_route_surface():
    from full_main import app as full_app

    paths = _route_paths(full_app)
    assert any(p.startswith("/api/v1/auth") for p in paths)
    assert any(p.startswith("/api/v1/capabilities") for p in paths)


@pytest.mark.skip(reason=_FULL_MAIN_DELETED_REASON)
def test_central_main_app_has_central_role_route_surface():
    from central_main import app as central_app

    paths = _route_paths(central_app)
    assert any(p.startswith("/api/v1/platform/sync") for p in paths)
    assert not any(p.startswith("/api/v1/auth") for p in paths)


@pytest.mark.skip(reason=_FULL_MAIN_DELETED_REASON)
def test_main_module_is_a_backward_compatible_alias_for_full_main():
    from main import app as main_app
    from full_main import app as full_app

    assert main_app is full_app


def test_main_module_client_fixture_still_serves_live_probe(client):
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
