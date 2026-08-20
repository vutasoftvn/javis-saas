import pytest

from app.core.runtime_config import ConfigurationError, validate_runtime_configuration, resolve_cors_origins


def test_production_requires_strong_jwt_and_master_secrets():
    environment = {
        "APP_ENV": "production",
        "JWT_SECRET": "supersecret-dev-key",
        "MASTER_SECRET_KEY": "default-insecure-master-key-for-dev",
    }

    with pytest.raises(ConfigurationError, match="JWT_SECRET"):
        validate_runtime_configuration(environment)


def test_development_allows_local_defaults():
    validate_runtime_configuration({"APP_ENV": "development"})


def test_production_rejects_default_minio_credentials():
    environment = {
        "APP_ENV": "production",
        "JWT_SECRET": "j" * 32,
        "MASTER_SECRET_KEY": "m" * 32,
        "MINIO_ACCESS_KEY": "minioadmin",
        "MINIO_SECRET_KEY": "minioadmin",
    }

    with pytest.raises(ConfigurationError, match="MINIO_ACCESS_KEY"):
        validate_runtime_configuration(environment)


def test_production_rejects_wildcard_cors_origins():
    with pytest.raises(ConfigurationError, match="COSA_ALLOWED_ORIGINS"):
        resolve_cors_origins({"APP_ENV": "production", "COSA_ALLOWED_ORIGINS": "*"})


def test_production_requires_explicit_cors_origins():
    with pytest.raises(ConfigurationError, match="COSA_ALLOWED_ORIGINS"):
        resolve_cors_origins({"APP_ENV": "production"})


def test_production_accepts_explicit_cors_allowlist():
    origins = resolve_cors_origins({
        "APP_ENV": "production",
        "COSA_ALLOWED_ORIGINS": "https://app.example.com, https://admin.example.com",
    })
    assert origins == ["https://app.example.com", "https://admin.example.com"]


def test_development_defaults_to_localhost_cors_origins():
    origins = resolve_cors_origins({"APP_ENV": "development"})
    assert "http://localhost:3000" in origins
