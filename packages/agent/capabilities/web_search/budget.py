from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import text


class WebSearchQuotaExceededError(Exception):
    """Raised when web search query cap or cost cap is exceeded for a workspace."""

    code = "QUOTA_EXCEEDED"

    def __init__(self, message: str, *, workspace_id: str, current_usage: dict[str, Any]) -> None:
        super().__init__(message)
        self.workspace_id = workspace_id
        self.current_usage = current_usage


@runtime_checkable
class WebSearchBudgetStore(Protocol):
    """Protocol for web search rate and quota management per workspace."""

    async def check_and_consume(
        self,
        workspace_id: str,
        *,
        cost: float = 1.0,
        query_count: int = 1,
    ) -> bool:
        """Check if workspace has remaining budget and consume atomically.

        Raises WebSearchQuotaExceededError if limit is reached.
        """
        ...


class InMemoryWebSearchBudgetStore:
    """In-memory budget tracker for development, testing, and sandbox environments."""

    def __init__(
        self,
        *,
        daily_query_cap: int | None = None,
        daily_cost_cap: float | None = None,
    ) -> None:
        self.daily_query_cap = (
            daily_query_cap
            if daily_query_cap is not None
            else int(os.environ.get("WEB_SEARCH_DAILY_QUERY_CAP", "100"))
        )
        self.daily_cost_cap = (
            daily_cost_cap
            if daily_cost_cap is not None
            else float(os.environ.get("WEB_SEARCH_DAILY_COST_CAP", "10.0"))
        )
        self._lock = asyncio.Lock()
        self._usage: dict[tuple[str, str], dict[str, Any]] = {}

    async def check_and_consume(
        self,
        workspace_id: str,
        *,
        cost: float = 1.0,
        query_count: int = 1,
    ) -> bool:
        today_str = datetime.now(UTC).date().isoformat()
        key = (str(workspace_id), today_str)

        async with self._lock:
            record = self._usage.setdefault(
                key,
                {"query_count": 0, "cost_accumulated": 0.0},
            )

            new_count = record["query_count"] + query_count
            new_cost = record["cost_accumulated"] + cost

            if new_count > self.daily_query_cap or new_cost > self.daily_cost_cap:
                raise WebSearchQuotaExceededError(
                    f"Web search quota exceeded for workspace {workspace_id}: "
                    f"queries={new_count}/{self.daily_query_cap}, cost={new_cost:.2f}/{self.daily_cost_cap:.2f}",
                    workspace_id=str(workspace_id),
                    current_usage={
                        "query_count": record["query_count"],
                        "cost_accumulated": record["cost_accumulated"],
                        "daily_query_cap": self.daily_query_cap,
                        "daily_cost_cap": self.daily_cost_cap,
                    },
                )

            record["query_count"] = new_count
            record["cost_accumulated"] = new_cost
            return True


class PostgresWebSearchBudgetStore:
    """PostgreSQL-backed durable budget store with atomic increment."""

    def __init__(
        self,
        session_factory: Any,
        *,
        daily_query_cap: int | None = None,
        daily_cost_cap: float | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.daily_query_cap = (
            daily_query_cap
            if daily_query_cap is not None
            else int(os.environ.get("WEB_SEARCH_DAILY_QUERY_CAP", "100"))
        )
        self.daily_cost_cap = (
            daily_cost_cap
            if daily_cost_cap is not None
            else float(os.environ.get("WEB_SEARCH_DAILY_COST_CAP", "10.0"))
        )

    async def check_and_consume(
        self,
        workspace_id: str,
        *,
        cost: float = 1.0,
        query_count: int = 1,
    ) -> bool:
        today_date = datetime.now(UTC).date()
        ws_id = str(workspace_id)

        upsert_stmt = text(
            """
            INSERT INTO agent.agent_web_search_budget (
                workspace_id,
                window_start,
                query_count,
                cost_accumulated,
                daily_query_cap,
                daily_cost_cap,
                updated_at
            )
            VALUES (
                :workspace_id,
                :window_start,
                :query_count,
                :cost,
                :daily_query_cap,
                :daily_cost_cap,
                NOW()
            )
            ON CONFLICT (workspace_id, window_start)
            DO UPDATE SET
                query_count = agent.agent_web_search_budget.query_count + :query_count,
                cost_accumulated = agent.agent_web_search_budget.cost_accumulated + :cost,
                updated_at = NOW()
            WHERE
                agent.agent_web_search_budget.query_count + :query_count <= agent.agent_web_search_budget.daily_query_cap
                AND agent.agent_web_search_budget.cost_accumulated + :cost <= agent.agent_web_search_budget.daily_cost_cap
            RETURNING query_count, cost_accumulated, daily_query_cap, daily_cost_cap;
            """
        )

        async with (
            self.session_factory() as session,
            session.begin(),
        ):
            result = await session.execute(
                upsert_stmt,
                {
                    "workspace_id": ws_id,
                    "window_start": today_date,
                    "query_count": query_count,
                    "cost": cost,
                    "daily_query_cap": self.daily_query_cap,
                    "daily_cost_cap": self.daily_cost_cap,
                },
            )
            row = result.fetchone()
            if row is None:
                # Fetch current row to provide accurate error details
                fetch_stmt = text(
                    """
                    SELECT query_count, cost_accumulated, daily_query_cap, daily_cost_cap
                    FROM agent.agent_web_search_budget
                    WHERE workspace_id = :workspace_id AND window_start = :window_start;
                    """
                )
                curr = await session.execute(
                    fetch_stmt,
                    {"workspace_id": ws_id, "window_start": today_date},
                )
                curr_row = curr.fetchone()
                current_usage = (
                    {
                        "query_count": curr_row[0],
                        "cost_accumulated": float(curr_row[1]),
                        "daily_query_cap": curr_row[2],
                        "daily_cost_cap": float(curr_row[3]),
                    }
                    if curr_row
                    else {
                        "query_count": self.daily_query_cap,
                        "cost_accumulated": self.daily_cost_cap,
                        "daily_query_cap": self.daily_query_cap,
                        "daily_cost_cap": self.daily_cost_cap,
                    }
                )
                raise WebSearchQuotaExceededError(
                    f"Web search quota exceeded for workspace {workspace_id}: "
                    f"queries={current_usage['query_count']}/{current_usage['daily_query_cap']}, "
                    f"cost={current_usage['cost_accumulated']:.2f}/{current_usage['daily_cost_cap']:.2f}",
                    workspace_id=ws_id,
                    current_usage=current_usage,
                )
            return True
