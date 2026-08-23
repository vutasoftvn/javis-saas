from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional, Protocol, runtime_checkable

from sqlalchemy import text

from agentos.knowledge.models import KnowledgeChunk, KnowledgeSearchResult, KnowledgeSource


class KnowledgeSourceNotFoundError(Exception):
    def __init__(self, source_id: str) -> None:
        super().__init__(f"Knowledge source not found: {source_id}")
        self.source_id = source_id


class ConfigurationError(Exception):
    """Raised when a knowledge store is improperly configured."""
    pass


@runtime_checkable
class KnowledgeStore(Protocol):
    async def put_source(self, source: KnowledgeSource) -> None:
        ...

    async def put_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        ...

    async def search(
        self, *, workspace_id: str, query_embedding: list[float], limit: int = 10
    ) -> list[KnowledgeSearchResult]:
        ...

    async def delete_source(self, source_id: str) -> None:
        ...


def _to_pgvector_literal(embedding: Optional[list[float]]) -> Optional[str]:
    """Serialize a Python float list into pgvector's text input format ("[0.1,0.2,...]").

    asyncpg has no built-in codec for the `vector` type, so values must travel as text
    and be cast on the SQL side (`::vector`) rather than relying on driver-level typing.
    """
    if embedding is None:
        return None
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


def _from_pgvector_literal(raw: Any) -> Optional[list[float]]:
    """Parse pgvector's text output format ("[0.1,0.2,...]") back into a float list.

    Handles both the `::text`-cast string from a real Postgres row and a plain list
    (e.g. from a fake session in unit tests) so callers don't need to special-case shape.
    """
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        return [float(x) for x in raw]
    return [float(x) for x in raw.strip("[]").split(",")] if raw else []


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"embedding dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemoryKnowledgeStore:
    """Store MVP: in-memory dict, computing exact cosine similarity in pure Python.
    Used for unit testing and environments without PostgreSQL/pgvector.
    """

    def __init__(self) -> None:
        self._sources: dict[str, KnowledgeSource] = {}
        self._chunks: dict[str, list[KnowledgeChunk]] = {}  # source_id -> chunks

    async def put_source(self, source: KnowledgeSource) -> None:
        self._sources[source.id] = source

    async def put_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        for chunk in chunks:
            self._chunks.setdefault(chunk.source_id, [])
            self._chunks[chunk.source_id] = [c for c in self._chunks[chunk.source_id] if c.id != chunk.id]
            self._chunks[chunk.source_id].append(chunk)

    async def search(
        self, *, workspace_id: str, query_embedding: list[float], limit: int = 10
    ) -> list[KnowledgeSearchResult]:
        scored: list[KnowledgeSearchResult] = []
        for chunks in self._chunks.values():
            for chunk in chunks:
                if chunk.workspace_id != workspace_id or chunk.embedding is None:
                    continue
                score = _cosine_similarity(query_embedding, chunk.embedding)
                scored.append(KnowledgeSearchResult(chunk=chunk, score=score))
        scored.sort(key=lambda result: result.score, reverse=True)
        return scored[:limit]

    async def delete_source(self, source_id: str) -> None:
        if source_id not in self._sources:
            raise KnowledgeSourceNotFoundError(source_id)
        del self._sources[source_id]
        self._chunks.pop(source_id, None)


class PgVectorKnowledgeStore:
    """PostgreSQL + pgvector implementation of `KnowledgeStore`.
    
    Persists sources and vectorized chunks into schema `knowledge`:
    - `knowledge.knowledge_sources`
    - `knowledge.knowledge_chunks`
    """

    def __init__(self, db_session_factory: Any = None) -> None:
        if db_session_factory is None:
            raise ConfigurationError(
                "PgVectorKnowledgeStore requires a valid `db_session_factory`. "
                "For in-memory testing without a database, use `InMemoryKnowledgeStore`."
            )
        self._session_factory = db_session_factory

    async def put_source(self, source: KnowledgeSource) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO knowledge.knowledge_sources (id, workspace_id, title, source_type, uri, created_at, metadata)
                    VALUES (:id, :workspace_id, :title, :source_type, :uri, :created_at, :metadata)
                    ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, metadata = EXCLUDED.metadata;
                    """
                ),
                {
                    "id": source.id,
                    "workspace_id": source.workspace_id,
                    "title": source.title,
                    "source_type": source.source_type.value if hasattr(source.source_type, "value") else str(source.source_type),
                    "uri": source.uri,
                    "created_at": source.created_at,
                    "metadata": json.dumps(source.metadata) if isinstance(source.metadata, dict) else source.metadata,
                },
            )
            await session.commit()

    async def put_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        if not chunks:
            return
        async with self._session_factory() as session:
            for chunk in chunks:
                await session.execute(
                    text(
                        """
                        INSERT INTO knowledge.knowledge_chunks
                            (id, source_id, workspace_id, chunk_index, content, embedding, embedding_model,
                             embedding_dimensions, embedding_version, content_hash, created_at, metadata)
                        VALUES
                            (:id, :source_id, :workspace_id, :chunk_index, :content, CAST(:embedding AS vector), :embedding_model,
                             :embedding_dimensions, :embedding_version, :content_hash, :created_at, :metadata)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            content_hash = EXCLUDED.content_hash;
                        """
                    ),
                    {
                        "id": chunk.id,
                        "source_id": chunk.source_id,
                        "workspace_id": chunk.workspace_id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "embedding": _to_pgvector_literal(chunk.embedding),
                        "embedding_model": chunk.embedding_model,
                        "embedding_dimensions": chunk.embedding_dimensions,
                        "embedding_version": chunk.embedding_version,
                        "content_hash": chunk.content_hash,
                        "created_at": chunk.created_at,
                        "metadata": json.dumps(chunk.metadata) if isinstance(chunk.metadata, dict) else chunk.metadata,
                    },
                )
            await session.commit()

    async def search(
        self, *, workspace_id: str, query_embedding: list[float], limit: int = 10
    ) -> list[KnowledgeSearchResult]:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT id, source_id, workspace_id, chunk_index, content, embedding::text,
                           embedding_model, embedding_dimensions, embedding_version, content_hash,
                           created_at, metadata,
                           1 - (embedding <=> CAST(:query_embedding AS vector)) AS score
                    FROM knowledge.knowledge_chunks
                    WHERE workspace_id = :workspace_id AND embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :limit;
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "query_embedding": _to_pgvector_literal(query_embedding),
                    "limit": limit,
                },
            )
            rows = result.fetchall()

        results: list[KnowledgeSearchResult] = []
        for row in rows:
            meta_val = row[11]
            if isinstance(meta_val, str):
                try:
                    meta_val = json.loads(meta_val)
                except Exception:
                    meta_val = {}

            chunk = KnowledgeChunk(
                id=row[0],
                source_id=row[1],
                workspace_id=row[2],
                chunk_index=row[3],
                content=row[4],
                embedding=_from_pgvector_literal(row[5]),
                embedding_model=row[6],
                embedding_dimensions=row[7],
                embedding_version=row[8],
                content_hash=row[9],
                created_at=row[10] if isinstance(row[10], datetime) else datetime.now(timezone.utc),
                metadata=meta_val or {},
            )
            results.append(KnowledgeSearchResult(chunk=chunk, score=float(row[12])))
        return results

    async def delete_source(self, source_id: str) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                text("DELETE FROM knowledge.knowledge_sources WHERE id = :id RETURNING id;"), {"id": source_id}
            )
            row = result.fetchone()
            if not row:
                raise KnowledgeSourceNotFoundError(source_id)
            await session.execute(
                text("DELETE FROM knowledge.knowledge_chunks WHERE source_id = :id;"), {"id": source_id}
            )
            await session.commit()


def get_knowledge_store(store_type: str = "in_memory", **kwargs: Any) -> KnowledgeStore:
    """Factory function to allocate KnowledgeStore by type."""
    if store_type in ("pgvector", "postgres"):
        return PgVectorKnowledgeStore(**kwargs)
    return InMemoryKnowledgeStore()


__all__ = [
    "ConfigurationError",
    "InMemoryKnowledgeStore",
    "KnowledgeSourceNotFoundError",
    "KnowledgeStore",
    "PgVectorKnowledgeStore",
    "get_knowledge_store",
]
