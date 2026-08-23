from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text

from agent_core.memory.base import ConfigurationError, MemoryNotFoundError, MemoryStore
from agent_core.memory.models import MemoryItem, MemoryKind

__all__ = ["PostgresMemoryStore"]


class PostgresMemoryStore:
    """PostgreSQL implementation của MemoryStore Protocol.

    Port từ bản archive của agentos/memory (đã retire), điều chỉnh theo
    MemoryItem model canonical (packages/agent_core/memory/models.py) — model
    canonical có thêm tenant_id, company_id, sensitivity, provenance_run_id,
    expires_at mà migration 003_agent_memory_and_knowledge.sql (Phase 1) chưa
    có cột riêng cho — các field này được gói vào cột metadata JSONB sẵn có
    thay vì mở migration mới trong cùng epic.
    """

    def __init__(self, db_session_factory: Any = None) -> None:
        if db_session_factory is None:
            raise ConfigurationError(
                "PostgresMemoryStore requires a valid `db_session_factory`. "
                "For in-memory testing without a database, use `InMemoryMemoryStore`."
            )
        self._session_factory = db_session_factory

    @staticmethod
    def _pack_metadata(item: MemoryItem) -> dict[str, Any]:
        packed = dict(item.metadata)
        packed["_tenant_id"] = item.tenant_id
        packed["_company_id"] = item.company_id
        packed["_sensitivity"] = item.sensitivity
        packed["_provenance_run_id"] = item.provenance_run_id
        packed["_expires_at"] = item.expires_at.isoformat() if item.expires_at else None
        return packed

    @staticmethod
    def _unpack_metadata(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        meta = dict(raw)
        extra = {
            "tenant_id": meta.pop("_tenant_id", None),
            "company_id": meta.pop("_company_id", None),
            "sensitivity": meta.pop("_sensitivity", "normal"),
            "provenance_run_id": meta.pop("_provenance_run_id", None),
            "expires_at": datetime.fromisoformat(meta.pop("_expires_at")) if meta.get("_expires_at") else None,
        }
        return meta, extra

    async def put(self, item: MemoryItem) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_memory.agent_memories
                        (id, workspace_id, agent_key, kind, content, importance, tags, metadata, created_at)
                    VALUES (:id, :workspace_id, :agent_key, :kind, :content, :importance, :tags, :metadata, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        importance = EXCLUDED.importance,
                        tags = EXCLUDED.tags,
                        metadata = EXCLUDED.metadata;
                    """
                ),
                {
                    "id": item.id,
                    "workspace_id": item.workspace_id,
                    "agent_key": item.agent_key,
                    "kind": item.kind.value,
                    "content": item.content,
                    "importance": item.importance,
                    "tags": json.dumps(list(item.tags)),
                    "metadata": json.dumps(self._pack_metadata(item)),
                    "created_at": item.created_at,
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
            clauses = ["workspace_id = :workspace_id"]
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
                    SELECT id, workspace_id, agent_key, kind, content, importance, tags, metadata, created_at
                    FROM agent_memory.agent_memories
                    WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT :limit;
                    """
                ),
                params,
            )
            rows = result.mappings().all()

            items: list[MemoryItem] = []
            for row in rows:
                tags_val = row["tags"]
                if isinstance(tags_val, str):
                    tags_val = json.loads(tags_val)
                metadata_val = row["metadata"]
                if isinstance(metadata_val, str):
                    metadata_val = json.loads(metadata_val)

                meta, extra = self._unpack_metadata(metadata_val or {})
                items.append(
                    MemoryItem(
                        id=row["id"],
                        workspace_id=row["workspace_id"],
                        agent_key=row["agent_key"],
                        kind=MemoryKind(row["kind"]),
                        content=row["content"],
                        importance=float(row["importance"]),
                        tags=tuple(tags_val or []),
                        metadata=meta,
                        created_at=row["created_at"],
                        **extra,
                    )
                )
            return items

    async def delete(self, item_id: str) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                text("DELETE FROM agent_memory.agent_memories WHERE id = :id RETURNING id;"),
                {"id": item_id},
            )
            row = result.fetchone()
            if not row:
                raise MemoryNotFoundError(item_id)
            await session.commit()
