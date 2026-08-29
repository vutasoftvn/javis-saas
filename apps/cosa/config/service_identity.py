"""Fail-closed đọc credential/URL nội bộ giữa các plane.

`development` / `test` cho phép giá trị mặc định để không phá DX local. Mọi
giá trị ENVIRONMENT khác (staging, production, …) là strict: thiếu / quá
ngắn / bằng giá trị dev-sentinel ⇒ raise ngay ở startup, không đợi request."""

from __future__ import annotations

import os

__all__ = [
    "ServiceIdentityError",
    "is_strict_env",
    "require_internal_url",
    "require_local_service_secret",
    "require_service_token",
    "validate_service_identity",
]

_DEV_SENTINELS = frozenset(
    {"", "dev-secret", "local-dev-service-token", "local-dev-service-secret"}
)
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})
_MIN_SECRET_LEN = 32


class ServiceIdentityError(RuntimeError):
    pass


def is_strict_env() -> bool:
    raw = os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or "development"
    return raw.strip().lower() not in {"development", "dev", "local", "test"}


def _reject_value(name: str, value: str) -> list[str]:
    problems: list[str] = []
    if value in _DEV_SENTINELS:
        problems.append(f"{name} is unset or a known development value")
    elif len(value) < _MIN_SECRET_LEN:
        problems.append(f"{name} must be at least {_MIN_SECRET_LEN} characters")
    return problems


def require_local_service_secret() -> str:
    value = os.environ.get("COSA_LOCAL_SERVICE_SECRET", "")
    if not is_strict_env():
        return value or "dev-secret"
    problems = _reject_value("COSA_LOCAL_SERVICE_SECRET", value)
    if problems:
        raise ServiceIdentityError("; ".join(problems))
    return value


def require_service_token(env_var: str, *, purpose: str) -> str:
    value = os.environ.get(env_var, "")
    if not is_strict_env():
        return value or "local-dev-service-token"
    problems = _reject_value(env_var, value)
    if problems:
        raise ServiceIdentityError(f"{'; '.join(problems)} (needed for {purpose})")
    return value


def require_internal_url(env_var: str, *, purpose: str, default_dev: str) -> str:
    value = os.environ.get(env_var, "")
    if not is_strict_env():
        return value or default_dev
    if not value:
        raise ServiceIdentityError(f"{env_var} is required in strict environments (for {purpose})")
    from urllib.parse import urlparse

    host = (urlparse(value).hostname or "").lower()
    if host in _LOOPBACK_HOSTS:
        raise ServiceIdentityError(
            f"{env_var}={value!r} points at a loopback host; use the internal service DNS name (for {purpose})"
        )
    return value


def validate_service_identity(
    *,
    need_secret: bool,
    tokens: list[tuple[str, str]],
    urls: list[tuple[str, str, str]],
) -> None:
    """Batch startup check. `tokens`: (env_var, purpose). `urls`: (env_var, purpose, default_dev)."""
    problems: list[str] = []
    if need_secret:
        try:
            require_local_service_secret()
        except ServiceIdentityError as e:
            problems.append(str(e))
    for env_var, purpose in tokens:
        try:
            require_service_token(env_var, purpose=purpose)
        except ServiceIdentityError as e:
            problems.append(str(e))
    for env_var, purpose, default_dev in urls:
        try:
            require_internal_url(env_var, purpose=purpose, default_dev=default_dev)
        except ServiceIdentityError as e:
            problems.append(str(e))
    if problems:
        raise ServiceIdentityError(
            "service identity validation failed:\n  - " + "\n  - ".join(problems)
        )
