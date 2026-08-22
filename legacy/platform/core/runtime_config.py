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
_DEFAULT_DEV_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
)


def validate_runtime_configuration(environment: Mapping[str, str] | None = None) -> None:
    environment = environment if environment is not None else os.environ
    app_env = environment.get("APP_ENV", "development").strip().lower()
    if app_env in {"development", "dev", "test"}:
        return

    # G2 P0.1 / G3 §9.1: COSA_PLATFORM_SIGNING_SECRET (legacy entitlement HMAC
    # secret) used to silently backfill JWT_SECRET/MASTER_SECRET_KEY when
    # those were unset — three unrelated secrets sharing one value. Severed:
    # each secret must now be configured independently and explicitly.
    for name in _REQUIRED_PRODUCTION_SECRETS:
        value = (os.environ.get(name) or environment.get(name) or "").strip()
        if len(value) < 32 or value in _DEVELOPMENT_SECRETS:
            raise ConfigurationError(
                f"{name} must be a unique value of at least 32 characters when APP_ENV={app_env}."
            )

    for name in ("MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"):
        if (environment.get(name) or "").strip() in _INSECURE_STORAGE_DEFAULTS:
            raise ConfigurationError(f"{name} must not use the development default when APP_ENV={app_env}.")


def resolve_cors_origins(environment: Mapping[str, str] | None = None) -> list[str]:
    """Resolve the CORS allowlist from COSA_ALLOWED_ORIGINS (G2 P0.10 / G3 §9.5).

    Development/test keeps a small localhost allowlist when unset. Any other
    APP_ENV must set COSA_ALLOWED_ORIGINS explicitly to a comma-separated list
    with no wildcard entry — wildcard origins combined with allow_credentials
    is unsafe and must never reach a non-development runtime.
    """
    environment = environment if environment is not None else os.environ
    app_env = environment.get("APP_ENV", "development").strip().lower()
    is_dev = app_env in {"development", "dev", "test"}

    raw = (environment.get("COSA_ALLOWED_ORIGINS") or "").strip()
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]

    if not origins:
        if is_dev:
            return list(_DEFAULT_DEV_CORS_ORIGINS)
        raise ConfigurationError(
            f"COSA_ALLOWED_ORIGINS must be set to a comma-separated origin allowlist when APP_ENV={app_env}; "
            "wildcard/unset CORS origins are not permitted outside development."
        )

    if "*" in origins and not is_dev:
        raise ConfigurationError(
            f"COSA_ALLOWED_ORIGINS must not include '*' when APP_ENV={app_env} (wildcard origins + credentials is unsafe)."
        )

    return origins

