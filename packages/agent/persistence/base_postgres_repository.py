"""Base PostgreSQL repository with shared session and query lifecycle management."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class BasePostgresRepository:
    """Abstract base class for PostgreSQL repositories.

    Provides shared helpers for:
    - Session lifecycle (_execute, _commit)
    - Pagination (_list_paginated)
    - Tenancy context setup (_setup_tenancy)
    - JSON parsing (_parse_json)

    Subclasses must initialize `self._session_factory` pointing to an
    AsyncSession factory (create_async_engine -> async_sessionmaker).
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        """Initialize with a session factory.

        Args:
            session_factory: Async session factory (from create_async_engine + async_sessionmaker)
        """
        if session_factory is None:
            raise ValueError(f"{self.__class__.__name__} requires a valid session_factory.")
        self._session_factory = session_factory

    async def _execute(
        self,
        session: AsyncSession,
        statement: Any,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a raw SQL statement.

        Args:
            session: Active async session
            statement: SQLAlchemy text() statement
            params: Parameter dict for the statement

        Returns:
            Result object from session.execute()
        """
        return await session.execute(statement, params or {})

    async def _commit(self, session: AsyncSession) -> None:
        """Commit the current transaction.

        Args:
            session: Active async session
        """
        await session.commit()

    async def _setup_tenancy(self, session: AsyncSession, workspace_id: str) -> None:
        """Set PostgreSQL session config for workspace isolation.

        Uses Postgres `set_config()` to inject workspace_id into session state
        for row-level security (RLS) policies.

        Args:
            session: Active async session
            workspace_id: Workspace ID to enforce
        """
        await session.execute(
            text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
            {"workspace_id": workspace_id},
        )

    async def _list_paginated(
        self,
        session: AsyncSession,
        query: str,
        params: dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        """Execute a paginated list query.

        Returns both the paginated result set and the total count.
        Assumes query returns only filtered/ordered rows (no LIMIT/OFFSET);
        this method adds them.

        Args:
            session: Active async session
            query: Base SQL query (e.g., "SELECT * FROM table WHERE workspace_id = :workspace_id")
            params: Query parameters
            limit: Max rows to return
            offset: Rows to skip

        Returns:
            Tuple of (results list, total count)
        """
        # Count total matching rows
        count_query = f"SELECT COUNT(*) AS total FROM ({query}) AS _count"
        count_res = await session.execute(text(count_query), params)
        first_row = count_res.mappings().first()
        total = int(first_row["total"]) if first_row is not None else 0

        # Fetch paginated results
        paginated_query = f"{query} LIMIT :limit OFFSET :offset"
        paginated_params = {**params, "limit": limit, "offset": offset}
        res = await session.execute(text(paginated_query), paginated_params)
        rows = list(res.mappings().all())

        return rows, total

    @staticmethod
    def _parse_json(val: Any) -> Any:
        """Parse JSON-like values, returning original if parsing fails.

        Used in row-to-record converters to safely handle JSON columns
        that may come from DB as strings, dicts, or None.

        Args:
            val: Value that might be JSON

        Returns:
            Parsed dict/list, or original value if not JSON
        """
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val
        return val


__all__ = ["BasePostgresRepository"]
