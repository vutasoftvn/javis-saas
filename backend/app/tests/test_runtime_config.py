import pytest

from app.core.runtime_config import ConfigurationError, validate_runtime_configuration


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
