from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field
from sqlalchemy import text

__all__ = [
    "InMemoryRunStreamEventRepository",
    "PostgresRunStreamEventRepository",
    "RunStreamEventRecord",
    "RunStreamEventRepository",
]


class RunStreamEventRecord(BaseModel):
    """Durable SSE fanout event — agent_conversation.run_stream_events
    (migration 011). KHÔNG phải agent_core.run_events (đó là governance/audit
    ledger nội bộ kernel, vocabulary khác — xem comment trong migration 011
    và COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §29.6 Phase 5)."""

    sequence: int | None = None
    run_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str
    correlation_id: str | None = None
    schema_version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class RunStreamEventRepository(Protocol):
    async def append(self, event: RunStreamEventRecord) -> RunStreamEventRecord: ...
    async def list_since(
        self, run_id: str, after_sequence: int | None = None
    ) -> list[RunStreamEventRecord]: ...
    async def list_since_for_conversation(
        self,
        conversation_id: str,
        after_sequence: int | None = None,
        limit: int | None = None,
    ) -> list[RunStreamEventRecord]: ...


class InMemoryRunStreamEventRepository:
    """In-memory implementation — test/dev, không dùng production (đúng
    nguyên tắc "production không silent fallback in-memory" đã áp dụng nhất
    quán trong toàn bộ agent_core)."""

    def __init__(self) -> None:
        self._events: dict[str, list[RunStreamEventRecord]] = {}
        self._lock = asyncio.Lock()
        self._global_seq = 0

    async def append(self, event: RunStreamEventRecord) -> RunStreamEventRecord:
        async with self._lock:
            self._global_seq += 1
            stored = event.model_copy(deep=True)
            stored.sequence = self._global_seq
            self._events.setdefault(event.run_id, []).append(stored)
            return stored.model_copy(deep=True)

    async def list_since(
        self, run_id: str, after_sequence: int | None = None
    ) -> list[RunStreamEventRecord]:
        events = self._events.get(run_id, [])
        if after_sequence is not None:
            return [e.model_copy(deep=True) for e in events if (e.sequence or 0) > after_sequence]
        return [e.model_copy(deep=True) for e in events]

    async def list_since_for_conversation(
        self,
        conversation_id: str,
        after_sequence: int | None = None,
        limit: int | None = None,
    ) -> list[RunStreamEventRecord]:
        matched: list[RunStreamEventRecord] = []
        for events in self._events.values():
            for e in events:
                if e.conversation_id == conversation_id and (
                    after_sequence is None or (e.sequence or 0) > after_sequence
                ):
                    matched.append(e.model_copy(deep=True))
        matched.sort(key=lambda e: e.sequence or 0)
        if limit is not None:
            matched = matched[:limit]
        return matched


class PostgresRunStreamEventRepository:
    """PostgreSQL implementation — agent_conversation.run_stream_events
    (migration 011)."""

    def __init__(self, db_session_factory: Any) -> None:
        if db_session_factory is None:
            raise ValueError(
                "PostgresRunStreamEventRepository requires a valid db_session_factory."
            )
        self._session_factory = db_session_factory

    async def append(self, event: RunStreamEventRecord) -> RunStreamEventRecord:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    INSERT INTO agent_conversation.run_stream_events (
                        run_id, event_type, payload, conversation_id, correlation_id,
                        schema_version, created_at
                    ) VALUES (
                        :run_id, :event_type, :payload, :conversation_id, :correlation_id,
                        :schema_version, :created_at
                    )
                    RETURNING sequence
                    """
                ),
                {
                    "run_id": event.run_id,
                    "event_type": event.event_type,
                    "payload": json.dumps(event.payload),
                    "conversation_id": event.conversation_id,
                    "correlation_id": event.correlation_id,
                    "schema_version": event.schema_version,
                    "created_at": event.created_at,
                },
            )
            sequence = res.scalar_one()
            await session.commit()
        stored = event.model_copy(deep=True)
        stored.sequence = int(sequence)
        return stored

    async def list_since(
        self, run_id: str, after_sequence: int | None = None
    ) -> list[RunStreamEventRecord]:
        query = """
            SELECT sequence, run_id, event_type, payload, conversation_id, correlation_id,
                   schema_version, created_at
            FROM agent_conversation.run_stream_events
            WHERE run_id = :run_id
        """
        params: dict[str, Any] = {"run_id": run_id}
        if after_sequence is not None:
            query += " AND sequence > :after_sequence"
            params["after_sequence"] = after_sequence
        query += " ORDER BY sequence ASC"

        async with self._session_factory() as session:
            res = await session.execute(text(query), params)
            rows = res.mappings().all()
        return [
            RunStreamEventRecord(
                sequence=r["sequence"],
                run_id=r["run_id"],
                event_type=r["event_type"],
                payload=self._parse_json(r["payload"]),
                conversation_id=r["conversation_id"],
                correlation_id=r["correlation_id"],
                schema_version=r["schema_version"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def list_since_for_conversation(
        self,
        conversation_id: str,
        after_sequence: int | None = None,
        limit: int | None = None,
    ) -> list[RunStreamEventRecord]:
        query = """
            SELECT sequence, run_id, event_type, payload, conversation_id, correlation_id,
                   schema_version, created_at
            FROM agent_conversation.run_stream_events
            WHERE conversation_id = :conversation_id
        """
        params: dict[str, Any] = {"conversation_id": conversation_id}
        if after_sequence is not None:
            query += " AND sequence > :after_sequence"
            params["after_sequence"] = after_sequence
        query += " ORDER BY sequence ASC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"

        async with self._session_factory() as session:
            res = await session.execute(text(query), params)
            rows = res.mappings().all()
        return [
            RunStreamEventRecord(
                sequence=r["sequence"],
                run_id=r["run_id"],
                event_type=r["event_type"],
                payload=self._parse_json(r["payload"]),
                conversation_id=r["conversation_id"],
                correlation_id=r["correlation_id"],
                schema_version=r["schema_version"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    @staticmethod
    def _parse_json(val: Any) -> dict[str, Any]:
        if val is None:
            return {}
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return {}
        return {}
