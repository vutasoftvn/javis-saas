from pathlib import Path


def test_dev_bootstrap_script_requires_password_and_is_idempotent():
    source = Path("backend/app/scripts/bootstrap_dev_user.py").read_text()

    assert "DEV_ADMIN_PASSWORD" in source
    assert "first()" in source
    assert "WorkspaceMember" in source
    assert "Brain" in source
