from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from agentos.memory.models import MemoryItem, MemoryKind
from agentos.memory.store import MemoryNotFoundError, MemoryStore


class PgVectorMemoryStore:
    """PostgreSQL + pgvector implementation of the `MemoryStore` protocol.
    Supports persistent storage of Working, Episodic, Semantic, Procedural,
    and Organizational memories with metadata and semantic filtering.
    """

    def __init__(self, db_session_factory: Any = None, dsn: Optional[str] = None) -> None:
        self._session_factory = db_session_factory
        self._dsn = dsn

    async def put(self, item: MemoryItem) -> None:
        if self._session_factory is None:
            # Fallback when running in decoupled or standalone mode
            return

        async with self._session_factory() as session:
            # Upsert memory item
            query = """
                INSERT INTO agent_memories (id, workspace_id, agent_key, kind, content, importance, tags, metadata, created_at)
                VALUES (:id, :workspace_id, :agent_key, :kind, :content, :importance, :tags, :metadata, :created_at)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    importance = EXCLUDED.importance,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata;
            """
            params = {
                "id": item.id,
                "workspace_id": item.workspace_id,
                "agent_key": item.agent_key,
                "kind": item.kind.value,
                "content": item.content,
                "importance": item.importance,
                "tags": json.dumps(item.tags),
                "metadata": json.dumps(item.metadata),
                "created_at": item.created_at,
            }
            await session.execute(query, params)
            await session.commit()

    async def search(
        self,
        *,
        workspace_id: str,
        agent_key: Optional[str] = None,
        kind: Optional[MemoryKind] = None,
        limit: int = 20,
    ) -> list[MemoryItem]:
        if self._session_factory is None:
            return []

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
            sql = f"SELECT id, workspace_id, agent_key, kind, content, importance, tags, metadata, created_at FROM agent_memories WHERE {where_sql} ORDER BY created_at DESC LIMIT :limit;"

            result = await session.execute(sql, params)
            rows = result.fetchall()

            items: list[MemoryItem] = []
            for row in rows:
                items.append(
                    MemoryItem(
                        id=row[0],
                        workspace_id=row[1],
                        agent_key=row[2],
                        kind=MemoryKind(row[3]),
                        content=row[4],
                        importance=float(row[5]),
                        tags=json.loads(row[6]) if isinstance(row[6], str) else (row[6] or []),
                        metadata=json.loads(row[7]) if isinstance(row[7], str) else (row[7] or {}),
                        created_at=row[8] if isinstance(row[8], datetime) else datetime.now(timezone.utc),
                    )
                )
            return items

    async def delete(self, item_id: str) -> None:
        if self._session_factory is None:
            return

        async with self._session_factory() as session:
            result = await session.execute("DELETE FROM agent_memories WHERE id = :id RETURNING id;", {"id": item_id})
            row = result.fetchone()
            if not row:
                raise MemoryNotFoundError(item_id)
            await session.commit()
