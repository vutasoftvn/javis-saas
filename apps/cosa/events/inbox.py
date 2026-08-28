from __future__ import annotations

from typing import Any, Literal


async def record(
    conn: Any,
    *,
    workspace_id: str,
    event_id: str,
    consumer_name: str,
    event_type: str,
    correlation_id: str,
    outcome: str,
    scheduled_task_id: str | None = None,
    aggregate_type: str | None = None,
    aggregate_id: str | None = None,
) -> Literal["recorded", "duplicate"]:
    if hasattr(conn, "record"):
        return await conn.record(
            conn,
            workspace_id=workspace_id,
            event_id=event_id,
            consumer_name=consumer_name,
            event_type=event_type,
            correlation_id=correlation_id,
            outcome=outcome,
            scheduled_task_id=scheduled_task_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
        )
    query = """
        INSERT INTO event_inbox (
            workspace_id, event_id, consumer_name, event_type,
            correlation_id, outcome, scheduled_task_id, aggregate_type, aggregate_id
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (workspace_id, event_id, consumer_name) DO NOTHING
        RETURNING id;
    """
    row = await conn.fetchrow(
        query,
        workspace_id,
        event_id,
        consumer_name,
        event_type,
        correlation_id,
        outcome,
        scheduled_task_id,
        aggregate_type,
        aggregate_id,
    )
    if row is None:
        return "duplicate"
    return "recorded"


async def set_outcome(
    conn: Any,
    workspace_id: str,
    event_id: str,
    consumer_name: str,
    outcome: str,
    scheduled_task_id: str | None = None,
) -> None:
    if hasattr(conn, "set_outcome"):
        return await conn.set_outcome(
            conn,
            workspace_id=workspace_id,
            event_id=event_id,
            consumer_name=consumer_name,
            outcome=outcome,
            scheduled_task_id=scheduled_task_id,
        )
    query = """
        UPDATE event_inbox
        SET outcome = $1,
            scheduled_task_id = COALESCE($2, scheduled_task_id)
        WHERE workspace_id = $3 AND event_id = $4 AND consumer_name = $5;
    """
    await conn.execute(query, outcome, scheduled_task_id, workspace_id, event_id, consumer_name)
