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


def test_central_vps_scopes_central_api_to_control_plane_role():
    compose = yaml.safe_load((REPO_ROOT / "deploy/central_vps/docker-compose.yaml").read_text())
    central_api = compose["services"]["central_api"]

    assert "APP_ROLE=central_control_plane" in central_api["environment"]
    assert "COSA_RUNTIME_PLANE=control" in central_api["environment"]
    assert central_api["command"] == "uvicorn app.central_main:app --host 0.0.0.0 --port 8000"


def test_central_vps_does_not_run_local_alembic_migrations():
    compose = yaml.safe_load((REPO_ROOT / "deploy/central_vps/docker-compose.yaml").read_text())
    central_api = compose["services"]["central_api"]

    assert "alembic" not in central_api.get("command", "")


SELF_HOST_COMPOSE = "deploy/self_host/docker-compose.yaml"


def test_self_host_compose_defines_expected_services():
    compose = yaml.safe_load((REPO_ROOT / SELF_HOST_COMPOSE).read_text())
    assert set(compose["services"].keys()) == {
        "caddy", "postgres", "minio", "migrate", "brain-api", "agent-worker", "realtime-agent",
    }


def test_self_host_compose_never_publishes_postgres_minio_or_worker_ports():
    compose = yaml.safe_load((REPO_ROOT / SELF_HOST_COMPOSE).read_text())
    services = compose["services"]

    assert "ports" not in services["postgres"]
    assert "ports" not in services["minio"]
    assert "ports" not in services["agent-worker"]


def test_self_host_compose_only_exposes_caddy_publicly():
    compose = yaml.safe_load((REPO_ROOT / SELF_HOST_COMPOSE).read_text())
    caddy_ports = compose["services"]["caddy"]["ports"]

    assert "80:80" in caddy_ports
    assert "443:443" in caddy_ports
    assert "ports" not in compose["services"]["brain-api"]


def test_self_host_compose_runs_brain_api_as_full_role():
    compose = yaml.safe_load((REPO_ROOT / SELF_HOST_COMPOSE).read_text())
    brain_api = compose["services"]["brain-api"]

    assert "APP_ROLE=full" in brain_api["environment"]
    assert brain_api["command"] == "uvicorn app.full_main:app --host 0.0.0.0 --port 8000"


def test_self_host_compose_never_includes_desktop_worker():
    raw_text = (REPO_ROOT / SELF_HOST_COMPOSE).read_text()
    assert "desktop_worker" not in raw_text

    compose = yaml.safe_load(raw_text)
    assert "desktop_worker" not in compose["services"]


def test_self_host_caddyfile_proxies_only_brain_api():
    caddyfile = (REPO_ROOT / "deploy/self_host/Caddyfile").read_text()

    assert "reverse_proxy brain-api:8000" in caddyfile
    assert "SELF_HOST_DOMAIN" in caddyfile
    assert "central_api" not in caddyfile
    assert "central_postgres" not in caddyfile
