"""Cross-origin configuration for browser-based development clients."""

from __future__ import annotations

import os


_DEVELOPMENT_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:5000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5000",
)


def parse_allowed_origins(raw: str | None) -> list[str]:
    """Return non-empty, normalized origins from a comma-separated value."""
    return [origin.strip() for origin in (raw or "").split(",") if origin.strip()]


def configured_allowed_origins() -> list[str]:
    """Read explicit origins, falling back to local Flutter Web development."""
    configured = parse_allowed_origins(os.environ.get("CORS_ALLOWED_ORIGINS"))
    if configured:
        return configured
    if os.environ.get("APP_ENV", "development").strip().lower() in {"development", "dev", "test"}:
        return list(_DEVELOPMENT_ORIGINS)
    return []
