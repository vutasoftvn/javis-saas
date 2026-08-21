from pathlib import Path

# Resolved from this file's location, not the process cwd - see test_compose_contract.py.
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dev_bootstrap_script_requires_password_and_is_idempotent():
    source = (REPO_ROOT / "backend/scripts/bootstrap_dev_user.py").read_text()

    assert "DEV_ADMIN_PASSWORD" in source
    assert "first()" in source
    assert "WorkspaceMember" in source
    assert "Brain" in source


def test_dev_smoke_target_checks_readiness_and_authenticated_identity():
    makefile = (REPO_ROOT / "Makefile").read_text()

    assert "dev-smoke:" in makefile
    assert "/ready" in makefile
    assert "/api/v1/auth/sessions" in makefile
    assert "/api/v1/auth/me" in makefile
    assert "DEV_ADMIN_PASSWORD" in makefile


def test_dev_setup_target_runs_bootstrap_then_authenticated_smoke_check():
    makefile = (REPO_ROOT / "Makefile").read_text()

    assert "dev-setup:" in makefile
    assert "$(MAKE) dev" in makefile
    assert "$(MAKE) dev-user" in makefile
    assert "$(MAKE) dev-smoke" in makefile
