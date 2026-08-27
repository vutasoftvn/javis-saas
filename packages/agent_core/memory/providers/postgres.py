from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text

from agent_core.memory.base import ConfigurationError, MemoryNotFoundError, MemoryStore
from agent_core.memory.models import MemoryItem, MemoryKind, MemoryStatus

__all__ = ["PostgresMemoryStore"]


class PostgresMemoryStore:
    """PostgreSQL implementation của MemoryStore Protocol.

    Từ Wave 8 (migration 009_memory_v2.sql), các field generic
    scope/provenance/lifecycle (tenant_id, company_id, sensitivity,
    provenance_run_id, expires_at, scope_type/scope_id...) đọc/ghi qua CỘT
    THẬT, không còn pack vào `metadata` JSONB như trước migration 009 — closes
    technical debt đã ghi chú rõ trong lịch sử file này ("packed vào metadata
    để tránh mở migration mới trong cùng epic").
    """

    def __init__(self, db_session_factory: Any = None) -> None:
        if db_session_factory is None:
            raise ConfigurationError(
                "PostgresMemoryStore requires a valid `db_session_factory`. "
                "For in-memory testing without a database, use `InMemoryMemoryStore`."
            )
        self._session_factory = db_session_factory

    async def put(self, item: MemoryItem) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_memory.agent_memories (
                        id, application_id, workspace_id,
                        scope_type, scope_id, agent_key, subject_type, subject_id,
                        kind, content, content_hash, importance, tags, sensitivity,
                        source_run_id, source_event_id, provenance, status,
                        valid_from, valid_until, supersedes_memory_id, metadata,
                        created_at, updated_at
                    ) VALUES (
                        :id, :application_id, :workspace_id,
                        :scope_type, :scope_id, :agent_key, :subject_type, :subject_id,
                        :kind, :content, :content_hash, :importance, :tags, :sensitivity,
                        :source_run_id, :source_event_id, :provenance, :status,
                        :valid_from, :valid_until, :supersedes_memory_id, :metadata,
                        :created_at, :updated_at
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        content_hash = EXCLUDED.content_hash,
                        importance = EXCLUDED.importance,
                        tags = EXCLUDED.tags,
                        status = EXCLUDED.status,
                        valid_until = EXCLUDED.valid_until,
                        supersedes_memory_id = EXCLUDED.supersedes_memory_id,
                        metadata = EXCLUDED.metadata,
                        updated_at = EXCLUDED.updated_at;
                    """
                ),
                {
                    "id": item.id,
                    "application_id": item.application_id,
                    "workspace_id": item.workspace_id,
                    "scope_type": item.scope_type or "WORKSPACE",
                    "scope_id": item.scope_id or item.workspace_id,
                    "agent_key": item.agent_key,
                    "subject_type": item.subject_type,
                    "subject_id": item.subject_id,
                    "kind": item.kind.value,
                    "content": item.content,
                    "content_hash": item.content_hash,
                    "importance": item.importance,
                    "tags": json.dumps(list(item.tags)),
                    "sensitivity": item.sensitivity,
                    "source_run_id": item.provenance_run_id,
                    "source_event_id": item.source_event_id,
                    "provenance": json.dumps(item.provenance),
                    "status": item.status.value,
                    "valid_from": item.valid_from,
                    "valid_until": item.expires_at,
                    "supersedes_memory_id": item.supersedes_memory_id,
                    "metadata": json.dumps(item.metadata),
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                },
            )
            await session.commit()

    async def search(
        self,
        *,
        workspace_id: str,
        agent_key: Optional[str] = None,
        kind: Optional[MemoryKind] = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        async with self._session_factory() as session:
            clauses = ["workspace_id = :workspace_id", "status = 'ACTIVE'"]
            params: dict[str, Any] = {"workspace_id": workspace_id, "limit": limit}

            if agent_key is not None:
                clauses.append("agent_key = :agent_key")
                params["agent_key"] = agent_key
            if kind is not None:
                clauses.append("kind = :kind")
                params["kind"] = kind.value

            where_sql = " AND ".join(clauses)
            result = await session.execute(
                text(
                    f"""
                    SELECT id, application_id, workspace_id,
                           scope_type, scope_id, agent_key, subject_type, subject_id,
                           kind, content, content_hash, importance, tags, sensitivity,
                           source_run_id, source_event_id, provenance, status,
                           valid_from, valid_until, supersedes_memory_id, metadata,
                           created_at, updated_at
                    FROM agent_memory.agent_memories
                    WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT :limit;
                    """
                ),
                params,
            )
            rows = result.mappings().all()
            return [self._row_to_item(row) for row in rows]

    async def delete(self, item_id: str, workspace_id: str) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                text("DELETE FROM agent_memory.agent_memories WHERE id = :id AND workspace_id = :workspace_id RETURNING id;"),
                {"id": item_id, "workspace_id": workspace_id},
            )
            row = result.fetchone()
            if not row:
                raise MemoryNotFoundError(item_id)
            await session.commit()

    @staticmethod
    def _parse_json(val: Any) -> Any:
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

    @classmethod
    def _row_to_item(cls, row: Any) -> MemoryItem:
        tags_val = cls._parse_json(row["tags"]) or []
        return MemoryItem(
            id=row["id"],
            application_id=row["application_id"],
            workspace_id=row["workspace_id"],
            scope_type=row["scope_type"],
            scope_id=row["scope_id"],
            agent_key=row["agent_key"],
            subject_type=row["subject_type"],
            subject_id=row["subject_id"],
            kind=MemoryKind(row["kind"]),
            content=row["content"],
            content_hash=row["content_hash"],
            importance=float(row["importance"]),
            tags=tuple(tags_val),
            sensitivity=row["sensitivity"],
            provenance_run_id=row["source_run_id"],
            source_event_id=row["source_event_id"],
            provenance=cls._parse_json(row["provenance"]) or {},
            status=MemoryStatus(row["status"]),
            valid_from=row["valid_from"],
            expires_at=row["valid_until"],
            supersedes_memory_id=row["supersedes_memory_id"],
            metadata=cls._parse_json(row["metadata"]) or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
