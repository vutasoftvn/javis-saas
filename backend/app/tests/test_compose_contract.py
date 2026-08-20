from pathlib import Path

import yaml

# Repo root, resolved from this file's location rather than the process cwd - the rest of
# the suite requires cwd=backend/ for `app.*` imports, but these contract checks read files
# that only exist at the repo root (docker-compose.yml, Makefile, frontend/), so a bare
# relative Path() silently passed or failed depending on which directory pytest was invoked
# from.
REPO_ROOT = Path(__file__).resolve().parents[3]


def _environment_values(service: dict) -> list[str]:
    return service["environment"]


def test_compose_migrates_before_api_and_worker_start():
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    services = compose["services"]

    assert services["migrate"]["command"] == "alembic upgrade head"
    assert services["brain-api"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert services["agent-worker"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"


def test_compose_keeps_openrouter_secret_in_worker_only():
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    api_environment = _environment_values(compose["services"]["brain-api"])
    worker_environment = _environment_values(compose["services"]["agent-worker"])

    assert "PROVIDER_CONFIGURED_OPENROUTER=${OPENROUTER_API_KEY:+1}" in api_environment
    assert not any(value.startswith("OPENROUTER_API_KEY=") for value in api_environment)
    assert "OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}" in worker_environment


def test_deployment_documents_migrate_service_and_cors():
    deployment = (REPO_ROOT / "DEPLOYMENT.md").read_text()

    assert "docker compose up --build -d migrate" in deployment
    assert "COSA_ALLOWED_ORIGINS" in deployment
    assert "Base.metadata.create_all(bind=engine)" not in deployment


def test_compose_keeps_opensandbox_config_in_worker_only():
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    api_environment = _environment_values(compose["services"]["brain-api"])
    worker_environment = _environment_values(compose["services"]["agent-worker"])

    assert not any("OPEN_SANDBOX" in value for value in api_environment)
    assert any("OPEN_SANDBOX_DOMAIN=" in value for value in worker_environment)
    assert any("OPEN_SANDBOX_API_KEY=" in value for value in worker_environment)


def test_compose_brain_api_does_not_mount_docker_sock():
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    api_volumes = compose["services"]["brain-api"].get("volumes", [])
    worker_volumes = compose["services"]["agent-worker"].get("volumes", [])

    assert not any("docker.sock" in vol for vol in api_volumes)
    assert not any("docker.sock" in vol for vol in worker_volumes)


def test_flutter_runtime_does_not_include_unused_sqlite_cache():
    assert not (REPO_ROOT / "frontend/lib/core/database/database_helper.dart").exists()
    assert "sqflite:" not in (REPO_ROOT / "frontend/pubspec.yaml").read_text()
