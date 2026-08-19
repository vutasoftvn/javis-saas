"""Runtime configuration validation for environment-dependent secrets."""

import os
from collections.abc import Mapping


class ConfigurationError(RuntimeError):
    """Raised when a non-development runtime is unsafe to start."""


_DEVELOPMENT_SECRETS = frozenset({
    "supersecret-dev-key",
    "default-insecure-master-key-for-dev",
})
_REQUIRED_PRODUCTION_SECRETS = ("JWT_SECRET", "MASTER_SECRET_KEY")
_INSECURE_STORAGE_DEFAULTS = {"minioadmin"}


def validate_runtime_configuration(environment: Mapping[str, str] | None = None) -> None:
    environment = environment if environment is not None else os.environ
    app_env = environment.get("APP_ENV", "development").strip().lower()
    if app_env in {"development", "dev", "test"}:
        return

    signing_secret = (environment.get("COSA_PLATFORM_SIGNING_SECRET") or "").strip()
    if signing_secret and len(signing_secret) >= 32:
        if not environment.get("JWT_SECRET"):
            os.environ["JWT_SECRET"] = signing_secret
        if not environment.get("MASTER_SECRET_KEY"):
            os.environ["MASTER_SECRET_KEY"] = signing_secret

    for name in _REQUIRED_PRODUCTION_SECRETS:
        value = (os.environ.get(name) or environment.get(name) or "").strip()
        if len(value) < 32 or value in _DEVELOPMENT_SECRETS:
            raise ConfigurationError(
                f"{name} must be a unique value of at least 32 characters when APP_ENV={app_env}."
            )

    for name in ("MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"):
        if (environment.get(name) or "").strip() in _INSECURE_STORAGE_DEFAULTS:
            raise ConfigurationError(f"{name} must not use the development default when APP_ENV={app_env}.")

