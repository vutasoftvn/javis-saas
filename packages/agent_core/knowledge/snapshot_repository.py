from __future__ import annotations

import json
from typing import Any, Optional, Protocol, runtime_checkable

from sqlalchemy import text

from agent_core.knowledge.snapshot import KnowledgeSnapshot
from agent_core.registry.repository import SpecVersionHashConflictError

__all__ = [
    "KnowledgeSnapshotRepository",
    "InMemoryKnowledgeSnapshotRepository",
    "PostgresKnowledgeSnapshotRepository",
]


@runtime_checkable
class KnowledgeSnapshotRepository(Protocol):
    """Protocol cho persistence KnowledgeSnapshot (knowledge.snapshots,
    migration 015, Wave M6)."""

    async def publish(self, snapshot: KnowledgeSnapshot) -> KnowledgeSnapshot: ...
    async def get(self, snapshot_id: str, version: str) -> Optional[KnowledgeSnapshot]: ...


class InMemoryKnowledgeSnapshotRepository:
    """In-memory implementation — chỉ dùng test/local dev, không dùng
    production (không durable qua restart)."""

    def __init__(self) -> None:
        self._snapshots: dict[tuple[str, str], KnowledgeSnapshot] = {}

    async def publish(self, snapshot: KnowledgeSnapshot) -> KnowledgeSnapshot:
        pinned = snapshot.with_hash() if snapshot.definition_hash is None else snapshot
        key = (pinned.id, pinned.version)
        existing = self._snapshots.get(key)
        if existing is not None:
            if existing.definition_hash != pinned.definition_hash:
                raise SpecVersionHashConflictError(
                    "knowledge_snapshot", pinned.id, pinned.version, existing.definition_hash, pinned.definition_hash
                )
            return existing.model_copy(deep=True)
        stored = pinned.model_copy(deep=True)
        self._snapshots[key] = stored
        return stored.model_copy(deep=True)

    async def get(self, snapshot_id: str, version: str) -> Optional[KnowledgeSnapshot]:
        r = self._snapshots.get((snapshot_id, version))
        return r.model_copy(deep=True) if r else None


class PostgresKnowledgeSnapshotRepository:
    """PostgreSQL implementation — persist vào knowledge.snapshots
    (migration 015). PRIMARY KEY (snapshot_id, version) composite ngay từ
    đầu — publish() có thể idempotent-check qua get() trước INSERT, tương
    tự PostgresSpecRegistryRepository (Wave M0/M1)."""

    def __init__(self, db_session_factory: Any) -> None:
        if db_session_factory is None:
            raise ValueError("PostgresKnowledgeSnapshotRepository requires a valid db_session_factory.")
        self._session_factory = db_session_factory

    async def publish(self, snapshot: KnowledgeSnapshot) -> KnowledgeSnapshot:
        pinned = snapshot.with_hash() if snapshot.definition_hash is None else snapshot
        existing = await self.get(pinned.id, pinned.version)
        if existing is not None:
            if existing.definition_hash != pinned.definition_hash:
                raise SpecVersionHashConflictError(
                    "knowledge_snapshot", pinned.id, pinned.version, existing.definition_hash, pinned.definition_hash
                )
            return existing

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO knowledge.snapshots (snapshot_id, version, workspace_id, definition_hash, content)
                    VALUES (:snapshot_id, :version, :workspace_id, :definition_hash, :content)
                    ON CONFLICT (snapshot_id, version) DO NOTHING
                    """
                ),
                {
                    "snapshot_id": pinned.id,
                    "version": pinned.version,
                    "workspace_id": pinned.workspace_id,
                    "definition_hash": pinned.definition_hash,
                    "content": json.dumps(pinned.model_dump(mode="json")),
                },
            )
            await session.commit()

        stored = await self.get(pinned.id, pinned.version)
        if stored is None:
            return pinned
        if stored.definition_hash != pinned.definition_hash:
            raise SpecVersionHashConflictError(
                "knowledge_snapshot", pinned.id, pinned.version, stored.definition_hash, pinned.definition_hash
            )
        return stored

    async def get(self, snapshot_id: str, version: str) -> Optional[KnowledgeSnapshot]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT content
                    FROM knowledge.snapshots
                    WHERE snapshot_id = :snapshot_id AND version = :version
                    """
                ),
                {"snapshot_id": snapshot_id, "version": version},
            )
            row = res.mappings().first()
            if row is None:
                return None
            content = row["content"]
            if isinstance(content, str):
                content = json.loads(content)
            return KnowledgeSnapshot(**content)
