"""Durable callback outbox for Agent Platform founder-asset commands.

The Company outbox may redeliver an already-recorded command after Agent-side
authoring completed but its status callback could not be delivered.  This
outbox preserves the exact callback payload so a duplicate command retries
only that callback, never the authoring side effect.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

DeliveryStatus = Literal["PENDING", "DELIVERED"]


@dataclass(frozen=True)
class FounderAssetCallbackRecord:
    workspace_id: str
    command_id: str
    payload: dict[str, Any]
    delivery_status: DeliveryStatus = "PENDING"
    delivery_attempts: int = 0
    last_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    delivered_at: datetime | None = None


class FounderAssetCallbackOutbox(Protocol):
    async def enqueue(self, record: FounderAssetCallbackRecord) -> FounderAssetCallbackRecord: ...
    async def get(self, workspace_id: str, command_id: str) -> FounderAssetCallbackRecord | None: ...
    async def mark_delivered(self, workspace_id: str, command_id: str) -> None: ...
    async def mark_failed(self, workspace_id: str, command_id: str, error: str) -> None: ...


class InMemoryFounderAssetCallbackOutbox:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], FounderAssetCallbackRecord] = {}

    async def enqueue(self, record: FounderAssetCallbackRecord) -> FounderAssetCallbackRecord:
        key = (record.workspace_id, record.command_id)
        existing = self._records.get(key)
        if existing is not None:
            if existing.payload != record.payload:
                raise ValueError("Founder asset callback payload conflicts with the durable command record")
            return existing
        now = datetime.now(UTC)
        stored = replace(record, created_at=now, updated_at=now)
        self._records[key] = stored
        return stored

    async def get(self, workspace_id: str, command_id: str) -> FounderAssetCallbackRecord | None:
        return self._records.get((workspace_id, command_id))

    async def mark_delivered(self, workspace_id: str, command_id: str) -> None:
        key = (workspace_id, command_id)
        current = self._records.get(key)
        if current is None:
            raise KeyError(f"Founder asset callback {command_id} not found")
        now = datetime.now(UTC)
        self._records[key] = replace(
            current,
            delivery_status="DELIVERED",
            delivery_attempts=current.delivery_attempts + 1,
            last_error=None,
            delivered_at=now,
            updated_at=now,
        )

    async def mark_failed(self, workspace_id: str, command_id: str, error: str) -> None:
        key = (workspace_id, command_id)
        current = self._records.get(key)
        if current is None:
            raise KeyError(f"Founder asset callback {command_id} not found")
        self._records[key] = replace(
            current,
            delivery_status="PENDING",
            delivery_attempts=current.delivery_attempts + 1,
            last_error=error,
            updated_at=datetime.now(UTC),
        )


class PostgresFounderAssetCallbackOutbox:
    """asyncpg-backed callback outbox scoped by Workspace and command ID."""

    def __init__(self, database: Any) -> None:
        self._database = database

    @staticmethod
    def _from_row(row: Any) -> FounderAssetCallbackRecord:
        raw_payload = row["payload"]
        payload = raw_payload if isinstance(raw_payload, dict) else json.loads(raw_payload)
        return FounderAssetCallbackRecord(
            workspace_id=row["workspace_id"],
            command_id=row["command_id"],
            payload=payload,
            delivery_status=row["delivery_status"],
            delivery_attempts=row["delivery_attempts"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            delivered_at=row["delivered_at"],
        )

    async def _get_in_connection(
        self, conn: Any, workspace_id: str, command_id: str
    ) -> FounderAssetCallbackRecord | None:
        row = await conn.fetchrow(
            """
            SELECT workspace_id, command_id, payload, delivery_status, delivery_attempts,
                   last_error, created_at, updated_at, delivered_at
            FROM agent.founder_asset_callback_outbox
            WHERE workspace_id = $1 AND command_id = $2
            """,
            workspace_id,
            command_id,
        )
        return self._from_row(row) if row is not None else None

    async def enqueue(self, record: FounderAssetCallbackRecord) -> FounderAssetCallbackRecord:
        async with self._database.begin() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO agent.founder_asset_callback_outbox (
                    workspace_id, command_id, payload, delivery_status, delivery_attempts,
                    created_at, updated_at
                ) VALUES ($1, $2, $3::jsonb, 'PENDING', 0, now(), now())
                ON CONFLICT (workspace_id, command_id) DO NOTHING
                RETURNING workspace_id, command_id, payload, delivery_status, delivery_attempts,
                          last_error, created_at, updated_at, delivered_at
                """,
                record.workspace_id,
                record.command_id,
                json.dumps(record.payload, sort_keys=True, separators=(",", ":")),
            )
            stored = self._from_row(row) if row is not None else await self._get_in_connection(
                conn, record.workspace_id, record.command_id
            )
            if stored is None:
                raise RuntimeError("Failed to persist founder asset callback outbox record")
            if stored.payload != record.payload:
                raise ValueError("Founder asset callback payload conflicts with the durable command record")
            return stored

    async def get(self, workspace_id: str, command_id: str) -> FounderAssetCallbackRecord | None:
        async with self._database.begin() as conn:
            return await self._get_in_connection(conn, workspace_id, command_id)

    async def mark_delivered(self, workspace_id: str, command_id: str) -> None:
        async with self._database.begin() as conn:
            await conn.execute(
                """
                UPDATE agent.founder_asset_callback_outbox
                SET delivery_status = 'DELIVERED', delivery_attempts = delivery_attempts + 1,
                    last_error = NULL, delivered_at = now(), updated_at = now()
                WHERE workspace_id = $1 AND command_id = $2
                """,
                workspace_id,
                command_id,
            )

    async def mark_failed(self, workspace_id: str, command_id: str, error: str) -> None:
        async with self._database.begin() as conn:
            await conn.execute(
                """
                UPDATE agent.founder_asset_callback_outbox
                SET delivery_status = 'PENDING', delivery_attempts = delivery_attempts + 1,
                    last_error = $3, updated_at = now()
                WHERE workspace_id = $1 AND command_id = $2
                """,
                workspace_id,
                command_id,
                error[:2048],
            )
