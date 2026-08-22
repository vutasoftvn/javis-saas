from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional, Protocol, runtime_checkable

from agentos.knowledge.models import KnowledgeChunk, KnowledgeSearchResult, KnowledgeSource


class KnowledgeSourceNotFoundError(Exception):
    def __init__(self, source_id: str) -> None:
        super().__init__(f"Knowledge source not found: {source_id}")
        self.source_id = source_id


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
    """Store MVP: dict trong process, tính cosine similarity thật bằng
    Python thuần (không phải term-overlap giả — khác
    `agentos/memory/retrieval.py`, ở đây có embedding vector thật nên tính
    similarity thật được). Dùng cho test nhanh và môi trường chưa có
    Postgres/pgvector.
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
    """PostgreSQL + pgvector implementation of `KnowledgeStore`. Cùng
    pattern session_factory với `agentos/memory/pgvector_store.py`'s
    `PgVectorMemoryStore` (đã được chấp nhận vào codebase dù bảng
    `agent_memories` chưa có migration — ADR-012 "no migration anywhere in
    the repo... a real scope decision, not a quick fix").

    Migration cho 2 bảng `knowledge_sources`/`knowledge_chunks` (bảng sau
    cần cột `embedding vector(N)` + extension `pgvector`) CỐ TÌNH CHƯA VIẾT
    ở đây — cùng lý do ADR-012 đã nêu cho `agent_memories`: quyết định
    migration này thuộc `agentos/` sống ở database nào (cùng Postgres với
    `services/`, hay riêng) là quyết định sở hữu chưa được chốt, không nên
    tự quyết trong lúc build Knowledge Layer logic. Code SQL dưới đây đúng
    cú pháp cho schema dự kiến, nhưng KHÔNG chạy được cho tới khi migration
    đó tồn tại — y hệt tình trạng hiện tại của `PgVectorMemoryStore`.
    """

    def __init__(self, db_session_factory: Any = None) -> None:
        self._session_factory = db_session_factory

    async def put_source(self, source: KnowledgeSource) -> None:
        if self._session_factory is None:
            return
        async with self._session_factory() as session:
            await session.execute(
                """
                INSERT INTO knowledge_sources (id, workspace_id, title, source_type, uri, created_at, metadata)
                VALUES (:id, :workspace_id, :title, :source_type, :uri, :created_at, :metadata)
                ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, metadata = EXCLUDED.metadata;
                """,
                {
                    "id": source.id,
                    "workspace_id": source.workspace_id,
                    "title": source.title,
                    "source_type": source.source_type.value,
                    "uri": source.uri,
                    "created_at": source.created_at,
                    "metadata": json.dumps(source.metadata),
                },
            )
            await session.commit()

    async def put_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        if self._session_factory is None or not chunks:
            return
        async with self._session_factory() as session:
            for chunk in chunks:
                await session.execute(
                    """
                    INSERT INTO knowledge_chunks
                        (id, source_id, workspace_id, chunk_index, content, embedding, created_at, metadata)
                    VALUES
                        (:id, :source_id, :workspace_id, :chunk_index, :content, :embedding, :created_at, :metadata)
                    ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding;
                    """,
                    {
                        "id": chunk.id,
                        "source_id": chunk.source_id,
                        "workspace_id": chunk.workspace_id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "embedding": chunk.embedding,
                        "created_at": chunk.created_at,
                        "metadata": json.dumps(chunk.metadata),
                    },
                )
            await session.commit()

    async def search(
        self, *, workspace_id: str, query_embedding: list[float], limit: int = 10
    ) -> list[KnowledgeSearchResult]:
        if self._session_factory is None:
            return []
        async with self._session_factory() as session:
            # `<=>` là cosine distance operator của pgvector — distance
            # càng nhỏ càng giống nhau, nên score = 1 - distance để cùng
            # chiều "càng cao càng liên quan" với InMemoryKnowledgeStore.
            result = await session.execute(
                """
                SELECT id, source_id, workspace_id, chunk_index, content, embedding, created_at, metadata,
                       1 - (embedding <=> :query_embedding) AS score
                FROM knowledge_chunks
                WHERE workspace_id = :workspace_id AND embedding IS NOT NULL
                ORDER BY embedding <=> :query_embedding
                LIMIT :limit;
                """,
                {"workspace_id": workspace_id, "query_embedding": query_embedding, "limit": limit},
            )
            rows = result.fetchall()

        results: list[KnowledgeSearchResult] = []
        for row in rows:
            chunk = KnowledgeChunk(
                id=row[0],
                source_id=row[1],
                workspace_id=row[2],
                chunk_index=row[3],
                content=row[4],
                embedding=list(row[5]) if row[5] is not None else None,
                created_at=row[6] if isinstance(row[6], datetime) else datetime.now(timezone.utc),
                metadata=json.loads(row[7]) if isinstance(row[7], str) else (row[7] or {}),
            )
            results.append(KnowledgeSearchResult(chunk=chunk, score=float(row[8])))
        return results

    async def delete_source(self, source_id: str) -> None:
        if self._session_factory is None:
            return
        async with self._session_factory() as session:
            result = await session.execute(
                "DELETE FROM knowledge_sources WHERE id = :id RETURNING id;", {"id": source_id}
            )
            row = result.fetchone()
            if not row:
                raise KnowledgeSourceNotFoundError(source_id)
            await session.execute("DELETE FROM knowledge_chunks WHERE source_id = :id;", {"id": source_id})
            await session.commit()


def get_knowledge_store(store_type: str = "in_memory", **kwargs: Any) -> KnowledgeStore:
    """Factory function để cấp phát KnowledgeStore theo cấu hình — cùng
    convention với `agentos/memory/store.py::get_memory_store`.
    """
    if store_type == "pgvector":
        return PgVectorKnowledgeStore(**kwargs)
    return InMemoryKnowledgeStore()
