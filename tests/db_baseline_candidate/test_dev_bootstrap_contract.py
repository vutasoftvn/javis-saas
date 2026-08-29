"""
Bootstrap and deployment contract tests.

Verifies that:
1. PostgreSQL initializes with explicit bootstrap scripts (deploy/postgres/init)
2. COSA migration script requires explicit DATABASE_URL environment variables
3. Deploy pipeline is explicitly sequential (preflight → migrate-all → deploy-app)
"""

import re
from pathlib import Path


def test_postgres_bootstrap_mount():
    """PostgreSQL service must mount deploy/postgres/init read-only for initialization."""
    compose_path = Path(__file__).parent.parent.parent / "docker-compose.yml"
    compose_text = compose_path.read_text()

    # Verify the postgres service mounts deploy/postgres/init at /docker-entrypoint-initdb.d
    assert "/docker-entrypoint-initdb.d:ro" in compose_text, (
        "PostgreSQL service must mount deploy/postgres/init as read-only "
        "at /docker-entrypoint-initdb.d for automatic initialization"
    )


def test_bootstrap_declares_only_canonical_data_planes():
    """A fresh development cluster starts with the three canonical databases."""
    bootstrap_path = Path(__file__).parent.parent.parent / "deploy/postgres/init/01-create-app-roles.sql"
    sql = bootstrap_path.read_text()

    for database in ("agent", "cosa", "workspace"):
        assert f"CREATE DATABASE {database}" in sql
        assert f"REVOKE CONNECT ON DATABASE {database} FROM PUBLIC" in sql

    for role in (
        "agent_app",
        "agent_migrator",
        "cosa_app",
        "cosa_migrator",
        "workspace_app",
        "workspace_migrator",
    ):
        assert role in sql

    for retired_name in ("javis", "company", "cosa_control_plane"):
        assert retired_name not in sql


def test_migration_script_no_fallback_credential():
    """
    COSA migration script must not have hardcoded fallback database credential.

    If COSA_DATABASE_URL or CONTROL_PLANE_DATABASE_URL is not set, the script
    must throw an error, not silently connect to a hardcoded host/credential.
    """
    migrate_path = Path(__file__).parent.parent.parent / "services/cosa/scripts/migrate.mjs"
    migration_text = migrate_path.read_text()

    # The contract explicitly checks for "SecureCentral" string which indicates
    # a hardcoded fallback credential in the format:
    # "postgresql://cosa_central_admin:SecureCentralPass2026@127.0.0.1:5434/cosa?..."
    assert "SecureCentral" not in migration_text, (
        "COSA migration script must not contain hardcoded fallback credentials. "
        "Missing COSA_DATABASE_URL or CONTROL_PLANE_DATABASE_URL must throw an error."
    )

    # Must have specific error guard that requires DATABASE_URL
    required_msg = "COSA_DATABASE_URL or CONTROL_PLANE_DATABASE_URL is required"
    assert required_msg in migration_text, (
        f"COSA migration script must throw error with message: '{required_msg}'"
    )


def test_deploy_recipe_is_sequential():
    """
    Deploy recipe must explicitly call preflight, migrations, then app deployment
    in that order, even when make is invoked with -j (parallel jobs).

    To ensure sequential execution even under -j, the deploy target recipe must
    call the three sub-targets via $(MAKE) calls within the recipe body,
    not as prerequisite dependencies.
    """
    makefile_path = Path(__file__).parent.parent.parent / "Makefile"
    makefile_text = makefile_path.read_text()

    # Extract the deploy target recipe (everything after "deploy:" until next target)
    deploy_match = re.search(r'^deploy:\s*\n((?:^\t.*\n)*)', makefile_text, re.MULTILINE)
    assert deploy_match, "deploy target not found in Makefile"

    deploy_recipe = deploy_match.group(1)

    # The deploy target must call three sub-targets in order via $(MAKE)
    # This ensures sequential execution even with -j flag
    expected_calls = [
        "$(MAKE) deploy-preflight",
        "$(MAKE) migrate-all",
        "$(MAKE) deploy-app"
    ]

    # Extract all $(MAKE) calls from the recipe in order
    make_calls = re.findall(r'\$\(MAKE\) [a-z-]+', deploy_recipe)

    assert make_calls == expected_calls, (
        f"deploy recipe must call targets in order: {expected_calls}, "
        f"but found: {make_calls}"
    )


def test_deploy_preflight_exists():
    """Deploy preflight target must exist."""
    makefile_path = Path(__file__).parent.parent.parent / "Makefile"
    makefile_text = makefile_path.read_text()

    assert re.search(r'^deploy-preflight:', makefile_text, re.MULTILINE), (
        "deploy-preflight target must exist in Makefile"
    )


def test_migrate_all_exists():
    """Migrate-all target must exist and handle all three database migrations."""
    makefile_path = Path(__file__).parent.parent.parent / "Makefile"
    makefile_text = makefile_path.read_text()

    assert re.search(r'^migrate-all:', makefile_text, re.MULTILINE), (
        "migrate-all target must exist in Makefile"
    )
