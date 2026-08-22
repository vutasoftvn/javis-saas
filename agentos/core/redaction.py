from __future__ import annotations

from typing import Any

# CLAUDE.md §12 ("Do not store or expose private chain-of-thought") and
# addendum §15.2 ("Bắt buộc secret redaction"): API key, authorization
# header, OAuth/access/refresh token, password, raw secrets must never
# reach durable trace/audit storage. Exact-match on normalized key names
# (not substring) so lookalike fields like input_tokens/output_tokens
# (agentos/core/executor.py:82-83) are never wrongly redacted.
REDACTED_PLACEHOLDER = "***REDACTED***"

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "secret",
        "client_secret",
        "api_key",
        "apikey",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "oauth_token",
        "session_token",
        "bearer_token",
        "authorization",
        "auth",
        "auth_token",
        "bearer",
        "private_key",
        "credit_card",
        "ssn",
    }
)


def _normalize_key(key: Any) -> str:
    if not isinstance(key, str):
        return ""
    return key.strip().lower().replace("-", "_").replace(" ", "_")


def redact_payload(payload: Any) -> Any:
    """Recursively redact known-sensitive fields before an event payload is
    persisted or exported. Returns a new structure; never mutates the input.
    """
    if isinstance(payload, dict):
        return {
            key: REDACTED_PLACEHOLDER if _normalize_key(key) in _SENSITIVE_KEYS else redact_payload(value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    return payload
