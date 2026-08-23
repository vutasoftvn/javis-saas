from __future__ import annotations

from typing import Any

from agentos.memory.base import ConfigurationError, MemoryNotFoundError, MemoryStore
from agentos.memory.providers.in_memory import InMemoryMemoryStore
from agentos.memory.providers.postgres import PostgresMemoryStore


def get_memory_store(store_type: str = "in_memory", **kwargs: Any) -> MemoryStore:
    """Factory function để cấp phát MemoryStore theo cấu hình."""
    if store_type in ("postgres", "pgvector"):
        return PostgresMemoryStore(**kwargs)
    return InMemoryMemoryStore()


__all__ = [
    "ConfigurationError",
    "InMemoryMemoryStore",
    "MemoryNotFoundError",
    "MemoryStore",
    "PostgresMemoryStore",
    "get_memory_store",
]
