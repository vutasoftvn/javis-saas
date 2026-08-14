from pathlib import Path


def test_dev_bootstrap_script_requires_password_and_is_idempotent():
    source = Path("backend/app/scripts/bootstrap_dev_user.py").read_text()

    assert "DEV_ADMIN_PASSWORD" in source
    assert "first()" in source
    assert "WorkspaceMember" in source
    assert "Brain" in source


def test_dev_smoke_target_checks_readiness_and_authenticated_identity():
    makefile = Path("Makefile").read_text()

    assert "dev-smoke:" in makefile
    assert "/ready" in makefile
    assert "/api/v1/auth/sessions" in makefile
    assert "/api/v1/auth/me" in makefile
    assert "DEV_ADMIN_PASSWORD" in makefile
