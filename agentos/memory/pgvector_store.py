from __future__ import annotations

"""Compatibility alias: `PgVectorMemoryStore` has been renamed to `PostgresMemoryStore`
in `agentos.memory.providers.postgres` (Phase 7B) to accurately reflect its role
as a PostgreSQL relational persistence adapter.
"""

from agentos.memory.providers.postgres import PostgresMemoryStore

# Backward compatibility alias
PgVectorMemoryStore = PostgresMemoryStore

__all__ = ["PgVectorMemoryStore", "PostgresMemoryStore"]
