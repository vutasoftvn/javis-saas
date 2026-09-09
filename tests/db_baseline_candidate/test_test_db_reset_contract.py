"""Static guard: the Founder Trial test reset validates before any destructive SQL.

The reset library must run every precondition check *before* it emits a
``DROP OWNED BY`` statement, and it must never contain the truly irreversible
forms (``DROP DATABASE`` / ``DROP SCHEMA public`` / ``DROP OWNED BY PUBLIC``).
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def test_reset_validates_before_destructive_sql():
    source = (ROOT / "scripts/test-db-reset-lib.mjs").read_text()
    assert "CONFIRM_FOUNDER_TRIAL_MVP_RESET" in source
    assert source.index("assertResetPreconditions") < source.index("DROP OWNED BY")
    assert "DROP DATABASE" not in source
    assert "DROP SCHEMA public" not in source
    assert "DROP OWNED BY PUBLIC" not in source


def test_reset_wrapper_delegates_to_guarded_lib():
    wrapper = (ROOT / "scripts/test-db-reset.mjs").read_text()
    assert "runTestDatabaseReset" in wrapper
    # Wrapper phải mỏng: không tự dựng SQL phá huỷ.
    assert "DROP" not in wrapper


def test_reset_absent_from_deploy_and_dev_targets():
    makefile = (ROOT / "Makefile").read_text()
    # Không target nào ngoài `test-db-reset` được gọi script reset.
    for line in makefile.splitlines():
        if "test-db-reset.mjs" in line:
            assert line.lstrip().startswith("APP_ENV=test") or "test-db-reset:" in line


def test_env_example_documents_test_only_urls_without_credentials():
    env_example = (ROOT / ".env.example").read_text()
    for key in (
        "AGENT_TEST_MIGRATOR_DATABASE_URL",
        "COSA_TEST_MIGRATOR_DATABASE_URL",
        "WORKSPACE_TEST_MIGRATOR_DATABASE_URL",
    ):
        assert key in env_example
    # Các biến test phải để trống (không kèm credential mẫu).
    assert "AGENT_TEST_MIGRATOR_DATABASE_URL=\n" in env_example + "\n"
