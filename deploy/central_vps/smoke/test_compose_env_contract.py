import pathlib

import yaml

COMPOSE = pathlib.Path(__file__).parents[1] / "docker-compose.prod.yaml"


def _env(service: str) -> dict:
    doc = yaml.safe_load(COMPOSE.read_text())
    return dict(doc["services"][service]["environment"])


def test_company_has_cosa_internal_wiring():
    e = _env("services-company")
    assert e["COSA_INTERNAL_URL"] == "http://cosa-api:8000"
    assert e["COSA_AGENTOS_INTAKE_URL"] == "http://cosa-api:8000"
    assert "${COSA_LOCAL_SERVICE_SECRET:?" in e["COSA_LOCAL_SERVICE_SECRET"]
    assert "${COSA_SERVICE_TOKEN:?" in e["COSA_SERVICE_TOKEN"]
    assert "${COSA_WORKER_SERVICE_TOKEN:?" in e["COSA_WORKER_SERVICE_TOKEN"]


def test_cosa_api_has_secret_and_tokens():
    e = _env("cosa-api")
    assert "${COSA_LOCAL_SERVICE_SECRET:?" in e["COSA_LOCAL_SERVICE_SECRET"]
    assert "${COSA_SERVICE_TOKEN:?" in e["COSA_SERVICE_TOKEN"]
    assert "${COSA_WORKER_SERVICE_TOKEN:?" in e["COSA_WORKER_SERVICE_TOKEN"]


def test_worker_has_company_url_and_token():
    e = _env("cosa-worker")
    assert e["COMPANY_SERVICE_URL"] == "http://services-company:4000"
    assert "${COSA_SERVICE_TOKEN:?" in e["COSA_SERVICE_TOKEN"]
