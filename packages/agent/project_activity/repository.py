from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from sqlalchemy import text

from agent.persistence import BasePostgresRepository
from agent.project_activity.models import ProjectActivityEventRecord

__all__ = [
    "InMemoryProjectActivityRepository",
    "PostgresProjectActivityRepository",
    "ProjectActivityRepository",
]


@runtime_checkable
class ProjectActivityRepository(Protocol):
    """Protocol cho Project Activity projection — durable, sequence-numbered,
    idempotent theo (workspace_id, project_id, idempotency_key)."""

    async def append_if_absent(
        self, event: ProjectActivityEventRecord
    ) -> ProjectActivityEventRecord: ...

    async def list_since(
        self,
        *,
        workspace_id: str,
        project_id: str,
        after_sequence: int | None = None,
        limit: int = 100,
    ) -> list[ProjectActivityEventRecord]: ...


class InMemoryProjectActivityRepository:
    """In-memory implementation — test/dev, không dùng production (cùng
    nguyên tắc với các repository khác trong `packages/agent`)."""

    def __init__(self) -> None:
        self._events: dict[str, ProjectActivityEventRecord] = {}
        # (workspace_id, project_id, idempotency_key) -> event_id
        self._idempotency_index: dict[tuple[str, str, str], str] = {}
        # (workspace_id, project_id) -> last sequence
        self._sequence_counters: dict[tuple[str, str], int] = {}

    async def append_if_absent(
        self, event: ProjectActivityEventRecord
    ) -> ProjectActivityEventRecord:
        idx_key = (event.workspace_id, event.project_id, event.idempotency_key)
        existing_id = self._idempotency_index.get(idx_key)
        if existing_id is not None:
            # Duplicate delivery — trả về row gốc, KHÔNG tiêu tốn sequence mới.
            return self._events[existing_id].model_copy(deep=True)

        seq_key = (event.workspace_id, event.project_id)
        seq = self._sequence_counters.get(seq_key, 0) + 1
        self._sequence_counters[seq_key] = seq

        stored = event.model_copy(deep=True)
        stored.project_sequence = seq
        self._events[stored.event_id] = stored
        self._idempotency_index[idx_key] = stored.event_id
        return stored.model_copy(deep=True)

    async def list_since(
        self,
        *,
        workspace_id: str,
        project_id: str,
        after_sequence: int | None = None,
        limit: int = 100,
    ) -> list[ProjectActivityEventRecord]:
        items = [
            e
            for e in self._events.values()
            if e.workspace_id == workspace_id and e.project_id == project_id
        ]
        items.sort(key=lambda e: e.project_sequence or 0)
        if after_sequence is not None:
            items = [e for e in items if (e.project_sequence or 0) > after_sequence]
        return [e.model_copy(deep=True) for e in items[:limit]]


class PostgresProjectActivityRepository(BasePostgresRepository):
    """PostgreSQL implementation persisting to `agent.project_activity_*`
    (migration 005). `append_if_absent` thực hiện đúng 4 bước mô tả trong
    task brief, cả 4 trong CÙNG 1 transaction (session chưa commit cho tới
    cuối):

    1. claim idempotency_key trong `agent.project_activity_idempotency`
       (INSERT ... ON CONFLICT DO NOTHING — atomic ở tầng DB, an toàn dưới
       concurrent writer khác connection/process);
    2. nếu đã claim trước đó (INSERT không insert được gì) — đọc lại event
       gốc theo event_id đã claim, trả về nguyên trạng;
    3. tăng đúng 1 cursor (workspace_id, project_id) trong
       `agent.project_activity_sequences` (UPDATE ... SET last_sequence =
       last_sequence + 1 — lock đúng 1 row, serialize hoá các claim cùng
       project);
    4. insert event với project_sequence vừa tăng;
    5. commit tất cả cùng lúc.
    """

    def __init__(self, db_session_factory: Any) -> None:
        super().__init__(db_session_factory)

    async def append_if_absent(
        self, event: ProjectActivityEventRecord
    ) -> ProjectActivityEventRecord:
        async with self._session_factory() as session:
            # 1. claim idempotency_key
            claim_res = await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.project_activity_idempotency (
                        workspace_id, project_id, idempotency_key, event_id, created_at
                    ) VALUES (
                        :workspace_id, :project_id, :idempotency_key, :event_id, :created_at
                    )
                    ON CONFLICT (workspace_id, project_id, idempotency_key) DO NOTHING
                    RETURNING event_id
                    """
                ),
                {
                    "workspace_id": event.workspace_id,
                    "project_id": event.project_id,
                    "idempotency_key": event.idempotency_key,
                    "event_id": event.event_id,
                    "created_at": event.recorded_at,
                },
            )
            claimed = claim_res.mappings().first()

            if claimed is None:
                # 2. đã claim trước đó — đọc lại event_id đã claim rồi trả về
                # đúng row gốc (không phải row của event mới truyền vào).
                existing_res = await self._execute(
                    session,
                    text(
                        """
                        SELECT event_id FROM agent.project_activity_idempotency
                        WHERE workspace_id = :workspace_id
                          AND project_id = :project_id
                          AND idempotency_key = :idempotency_key
                        """
                    ),
                    {
                        "workspace_id": event.workspace_id,
                        "project_id": event.project_id,
                        "idempotency_key": event.idempotency_key,
                    },
                )
                existing_row = existing_res.mappings().first()
                original_event_id = existing_row["event_id"]

                event_res = await self._execute(
                    session,
                    text(self._SELECT_EVENT_SQL),
                    {"event_id": original_event_id},
                )
                event_row = event_res.mappings().first()
                await self._commit(session)
                if event_row is None:
                    raise RuntimeError(
                        f"project_activity_idempotency claimed event_id={original_event_id} "
                        "but no matching row in project_activity_events — data corruption"
                    )
                return self._row_to_event(event_row)

            # 3. tăng đúng 1 cursor (workspace_id, project_id)
            seq_res = await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.project_activity_sequences (
                        workspace_id, project_id, last_sequence
                    ) VALUES (:workspace_id, :project_id, 1)
                    ON CONFLICT (workspace_id, project_id) DO UPDATE SET
                        last_sequence = agent.project_activity_sequences.last_sequence + 1
                    RETURNING last_sequence
                    """
                ),
                {"workspace_id": event.workspace_id, "project_id": event.project_id},
            )
            next_sequence = seq_res.mappings().first()["last_sequence"]

            # 4. insert event với project_sequence vừa tăng
            await self._execute(
                session,
                text(
                    """
                    INSERT INTO agent.project_activity_events (
                        event_id, workspace_id, project_id, project_sequence, kind, phase,
                        status, actor_kind, actor_id, correlation_id, source_type, source_id,
                        source_version, summary, classification, payload_hash, occurred_at,
                        recorded_at
                    ) VALUES (
                        :event_id, :workspace_id, :project_id, :project_sequence, :kind, :phase,
                        :status, :actor_kind, :actor_id, :correlation_id, :source_type, :source_id,
                        :source_version, CAST(:summary AS jsonb), :classification, :payload_hash,
                        :occurred_at, :recorded_at
                    )
                    """
                ),
                {
                    "event_id": event.event_id,
                    "workspace_id": event.workspace_id,
                    "project_id": event.project_id,
                    "project_sequence": next_sequence,
                    "kind": event.kind,
                    "phase": event.phase,
                    "status": event.status,
                    "actor_kind": event.actor_kind,
                    "actor_id": event.actor_id,
                    "correlation_id": event.correlation_id,
                    "source_type": event.source_type,
                    "source_id": event.source_id,
                    "source_version": event.source_version,
                    "summary": self._dump_json(event.summary),
                    "classification": event.classification,
                    "payload_hash": event.payload_hash,
                    "occurred_at": event.occurred_at,
                    "recorded_at": event.recorded_at,
                },
            )
            # 5. commit tất cả (claim + sequence increment + insert) cùng lúc.
            await self._commit(session)

        stored = event.model_copy(deep=True)
        stored.project_sequence = next_sequence
        return stored

    async def list_since(
        self,
        *,
        workspace_id: str,
        project_id: str,
        after_sequence: int | None = None,
        limit: int = 100,
    ) -> list[ProjectActivityEventRecord]:
        query = self._SELECT_EVENT_SQL.replace(
            "WHERE event_id = :event_id",
            "WHERE workspace_id = :workspace_id AND project_id = :project_id",
        )
        params: dict[str, Any] = {"workspace_id": workspace_id, "project_id": project_id}
        if after_sequence is not None:
            query += " AND project_sequence > :after_sequence"
            params["after_sequence"] = after_sequence
        query += " ORDER BY project_sequence ASC LIMIT :limit"
        params["limit"] = limit

        async with self._session_factory() as session:
            res = await self._execute(session, text(query), params)
            return [self._row_to_event(r) for r in res.mappings().all()]

    _SELECT_EVENT_SQL = """
        SELECT event_id, workspace_id, project_id, project_sequence, kind, phase, status,
               actor_kind, actor_id, correlation_id, source_type, source_id, source_version,
               summary, classification, payload_hash, occurred_at, recorded_at
        FROM agent.project_activity_events
        WHERE event_id = :event_id
    """

    @staticmethod
    def _dump_json(val: Any) -> str:
        import json

        return json.dumps(val or {})

    @classmethod
    def _row_to_event(cls, row: Any) -> ProjectActivityEventRecord:
        return ProjectActivityEventRecord(
            event_id=row["event_id"],
            workspace_id=row["workspace_id"],
            project_id=row["project_id"],
            project_sequence=row["project_sequence"],
            idempotency_key="",  # không tồn tại trên events table — chỉ cần cho append
            kind=row["kind"],
            phase=row["phase"],
            status=row["status"],
            actor_kind=row["actor_kind"],
            actor_id=row["actor_id"],
            correlation_id=row["correlation_id"],
            source_type=row["source_type"],
            source_id=row["source_id"],
            source_version=row["source_version"],
            summary=cls._parse_json(row["summary"]) or {},
            classification=row["classification"],
            payload_hash=row["payload_hash"],
            occurred_at=row["occurred_at"],
            recorded_at=row["recorded_at"],
        )
