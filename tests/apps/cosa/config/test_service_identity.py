import pytest

from apps.cosa.config.service_identity import (
    ServiceIdentityError,
    is_strict_env,
    require_internal_url,
    require_local_service_secret,
    require_service_token,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("ENVIRONMENT", "APP_ENV", "COSA_LOCAL_SERVICE_SECRET",
              "COSA_SERVICE_TOKEN", "COSA_WORKER_SERVICE_TOKEN", "COMPANY_SERVICE_URL"):
        monkeypatch.delenv(k, raising=False)


def test_dev_env_is_not_strict_and_allows_defaults(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert is_strict_env() is False
    assert require_internal_url(
        "COMPANY_SERVICE_URL", purpose="callback", default_dev="http://127.0.0.1:4000"
    ) == "http://127.0.0.1:4000"


def test_production_rejects_missing_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ServiceIdentityError):
        require_local_service_secret()


def test_production_rejects_dev_sentinel_token(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_SERVICE_TOKEN", "local-dev-service-token")
    with pytest.raises(ServiceIdentityError):
        require_service_token("COSA_SERVICE_TOKEN", purpose="company callback")


def test_production_rejects_short_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_LOCAL_SERVICE_SECRET", "tooshort")
    with pytest.raises(ServiceIdentityError):
        require_local_service_secret()


def test_production_accepts_strong_values(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_LOCAL_SERVICE_SECRET", "s" * 40)
    monkeypatch.setenv("COMPANY_SERVICE_URL", "http://services-company:4000")
    assert require_local_service_secret() == "s" * 40
    assert require_internal_url(
        "COMPANY_SERVICE_URL", purpose="callback", default_dev="http://127.0.0.1:4000"
    ) == "http://services-company:4000"


def test_production_rejects_loopback_internal_url(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COMPANY_SERVICE_URL", "http://127.0.0.1:4000")
    with pytest.raises(ServiceIdentityError):
        require_internal_url("COMPANY_SERVICE_URL", purpose="callback", default_dev="x")
