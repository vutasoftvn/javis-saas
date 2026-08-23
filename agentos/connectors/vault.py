from __future__ import annotations

import os
from typing import Optional, Protocol, runtime_checkable


class SecretNotFoundError(Exception):
    """Raised when a requested credential is not found in the secret store."""


@runtime_checkable
class SecretStore(Protocol):
    """Protocol for secure credential and token retrieval (§16.2)."""

    async def get_secret(self, key: str, *, workspace_id: Optional[str] = None) -> str: ...


class InMemoryVaultStore:
    """In-memory secure secret store implementation for test and runtime usage."""

    def __init__(self, initial_secrets: Optional[dict[str, str]] = None) -> None:
        self._secrets: dict[str, str] = dict(initial_secrets or {})

    def set_secret(self, key: str, value: str, *, workspace_id: Optional[str] = None) -> None:
        lookup_key = f"{workspace_id}:{key}" if workspace_id else key
        self._secrets[lookup_key] = value

    async def get_secret(self, key: str, *, workspace_id: Optional[str] = None) -> str:
        if workspace_id:
            scoped_key = f"{workspace_id}:{key}"
            if scoped_key in self._secrets:
                return self._secrets[scoped_key]

        if key in self._secrets:
            return self._secrets[key]

        # Fallback to environment variables if available
        env_val = os.getenv(key.upper())
        if env_val:
            return env_val

        raise SecretNotFoundError(f"Secret '{key}' not found (workspace: {workspace_id})")
