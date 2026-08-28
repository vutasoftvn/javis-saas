"""PostgresRunCounter — đếm số run đã schedule cho một aggregate trong ngày,
để enforce `max_runs_per_aggregate_per_day` của EventTriggerRule.

Rate-limit theo (workspace, aggregate) / ngày, gộp mọi rule — `rule_id` không
dùng (event_inbox không lưu rule_id; một aggregate hiếm khi có nhiều rule
cùng loại). Đủ chặt cho mục đích chống bão trigger.
"""
from __future__ import annotations

from typing import Any

__all__ = ["PostgresRunCounter"]


class PostgresRunCounter:
    def __init__(self, pool: Any) -> None:
        self._pool = pool

    async def today(self, workspace_id: str, rule_id: str, aggregate_id: str) -> int:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT count(*) AS n FROM event_inbox
                WHERE workspace_id = $1
                  AND aggregate_id = $2
                  AND outcome = 'accepted'
                  AND received_at >= date_trunc('day', now())
                """,
                workspace_id,
                aggregate_id,
            )
        return int(row["n"]) if row else 0
