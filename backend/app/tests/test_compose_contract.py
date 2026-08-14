from pathlib import Path

import yaml


def _environment_values(service: dict) -> list[str]:
    return service["environment"]


def test_compose_migrates_before_api_and_worker_start():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    services = compose["services"]

    assert services["migrate"]["command"] == "alembic upgrade head"
    assert services["brain-api"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert services["agent-worker"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"


def test_compose_keeps_openrouter_secret_in_worker_only():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    api_environment = _environment_values(compose["services"]["brain-api"])
    worker_environment = _environment_values(compose["services"]["agent-worker"])

    assert "PROVIDER_CONFIGURED_OPENROUTER=${OPENROUTER_API_KEY:+1}" in api_environment
    assert not any(value.startswith("OPENROUTER_API_KEY=") for value in api_environment)
    assert "OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}" in worker_environment
