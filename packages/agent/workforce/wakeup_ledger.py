"""Sổ cái wakeup của workforce (Dự án C).

`record_if_absent` dedup theo `(workspace_id, assignment_id, source_ref)`, an toàn khi chạy song song.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import AwareDatetime, BaseModel
from sqlalchemy import text

__all__ = ["InMemoryWakeupLedger", "PostgresWakeupLedger", "WakeupEntry", "WakeupLedger"]


class WakeupEntry(BaseModel):
    wake_id: str
    workspace_id: str
    assignment_id: str
    project_id: str
    reason_kind: str
    source_ref: str
    hop: int
    created_at: AwareDatetime
    handled_at: AwareDatetime | None = None


class WakeupLedger(Protocol):
    async def record_if_absent(self, entry: WakeupEntry) -> bool: ...

    async def count_since(self, workspace_id: str, assignment_id: str, since: datetime) -> int: ...

    async def list_unhandled(
        self, workspace_id: str, assignment_id: str, project_id: str, limit: int = 20
    ) -> list[WakeupEntry]: ...

    async def mark_handled(self, workspace_id: str, wake_ids: Sequence[str]) -> int: ...


class InMemoryWakeupLedger:
    def __init__(self) -> None:
        self._by_source: dict[tuple[str, str, str], WakeupEntry] = {}

    async def record_if_absent(self, entry: WakeupEntry) -> bool:
        key = (entry.workspace_id, entry.assignment_id, entry.source_ref)
        if key in self._by_source:
            return False
        self._by_source[key] = entry
        return True

    async def count_since(self, workspace_id: str, assignment_id: str, since: datetime) -> int:
        return sum(
            1
            for e in self._by_source.values()
            if e.workspace_id == workspace_id
            and e.assignment_id == assignment_id
            and e.created_at >= since
        )

    async def list_unhandled(
        self, workspace_id: str, assignment_id: str, project_id: str, limit: int = 20
    ) -> list[WakeupEntry]:
        rows = [
            e
            for e in self._by_source.values()
            if e.workspace_id == workspace_id
            and e.assignment_id == assignment_id
            and e.project_id == project_id
            and e.handled_at is None
        ]
        rows.sort(key=lambda e: (e.created_at, e.wake_id))
        return rows[: max(1, limit)]

    async def mark_handled(self, workspace_id: str, wake_ids: Sequence[str]) -> int:
        wanted = set(wake_ids)
        now = datetime.now(UTC)
        count = 0
        for key, e in list(self._by_source.items()):
            if e.workspace_id == workspace_id and e.wake_id in wanted and e.handled_at is None:
                self._by_source[key] = e.model_copy(update={"handled_at": now})
                count += 1
        return count


_INSERT = text(
    """
    INSERT INTO agent.workforce_wakeups
      (wake_id, workspace_id, assignment_id, project_id, reason_kind, source_ref, hop, created_at)
    VALUES (:wake_id, :workspace_id, :assignment_id, :project_id, :reason_kind, :source_ref, :hop, :created_at)
    ON CONFLICT (workspace_id, assignment_id, source_ref) DO NOTHING
    RETURNING wake_id
    """
)
_COUNT = text(
    """
    SELECT count(*) FROM agent.workforce_wakeups
    WHERE workspace_id = :workspace_id AND assignment_id = :assignment_id AND created_at >= :since
    """
)
_UNHANDLED = text(
    """
    SELECT wake_id, workspace_id, assignment_id, project_id, reason_kind, source_ref, hop,
           created_at, handled_at
    FROM agent.workforce_wakeups
    WHERE workspace_id = :workspace_id AND assignment_id = :assignment_id
      AND project_id = :project_id AND handled_at IS NULL
    ORDER BY created_at ASC, wake_id ASC LIMIT :limit
    """
)
_MARK = text(
    """
    UPDATE agent.workforce_wakeups SET handled_at = now()
    WHERE workspace_id = :workspace_id AND wake_id = ANY(:wake_ids) AND handled_at IS NULL
    """
)


class PostgresWakeupLedger:
    def __init__(self, session_factory: Any) -> None:
        if session_factory is None:
            raise ValueError("PostgresWakeupLedger requires a session_factory")
        self._session_factory = session_factory

    async def record_if_absent(self, entry: WakeupEntry) -> bool:
        params = entry.model_dump(exclude={"handled_at"})
        async with self._session_factory() as session:
            result = await session.execute(_INSERT, params)
            inserted = result.first() is not None
            await session.commit()
        return inserted

    async def count_since(self, workspace_id: str, assignment_id: str, since: datetime) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                _COUNT,
                {"workspace_id": workspace_id, "assignment_id": assignment_id, "since": since},
            )
            return int(result.scalar_one())

    async def list_unhandled(
        self, workspace_id: str, assignment_id: str, project_id: str, limit: int = 20
    ) -> list[WakeupEntry]:
        async with self._session_factory() as session:
            rows = (
                (
                    await session.execute(
                        _UNHANDLED,
                        {
                            "workspace_id": workspace_id,
                            "assignment_id": assignment_id,
                            "project_id": project_id,
                            "limit": max(1, limit),
                        },
                    )
                )
                .mappings()
                .all()
            )
        return [WakeupEntry(**dict(r)) for r in rows]

    async def mark_handled(self, workspace_id: str, wake_ids: Sequence[str]) -> int:
        ids = list(wake_ids)
        if not ids:
            return 0
        async with self._session_factory() as session:
            result = await session.execute(_MARK, {"workspace_id": workspace_id, "wake_ids": ids})
            await session.commit()
            return int(result.rowcount or 0)
