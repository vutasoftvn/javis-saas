from __future__ import annotations

import os
from typing import Protocol

from agent_core.knowledge.models import CitationProvenance, KnowledgeChunk, KnowledgeDocument

__all__ = ["InMemoryKnowledgeStore", "KnowledgeStore", "get_knowledge_store"]


class KnowledgeStore(Protocol):
    async def save_document(self, doc: KnowledgeDocument) -> None: ...
    async def get_document(self, doc_id: str) -> KnowledgeDocument | None: ...
    async def search_chunks(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int = 5,
    ) -> list[CitationProvenance]: ...


class InMemoryKnowledgeStore:
    """In-memory Knowledge Store hỗ trợ tìm kiếm từ khoá / similarity đơn giản."""

    def __init__(self) -> None:
        self._docs: dict[str, KnowledgeDocument] = {}
        self._chunks: dict[str, KnowledgeChunk] = {}

    async def save_document(self, doc: KnowledgeDocument) -> None:
        self._docs[doc.id] = doc.model_copy(deep=True)
        for chunk in doc.chunks:
            self._chunks[chunk.id] = chunk.model_copy(deep=True)

    async def get_document(self, doc_id: str) -> KnowledgeDocument | None:
        doc = self._docs.get(doc_id)
        return doc.model_copy(deep=True) if doc else None

    async def search_chunks(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int = 5,
    ) -> list[CitationProvenance]:
        query_terms = [t.lower() for t in query.split() if len(t) > 1]
        scored_results: list[tuple[float, KnowledgeChunk, KnowledgeDocument]] = []

        for chunk in self._chunks.values():
            if chunk.workspace_id != workspace_id:
                continue
            doc = self._docs.get(chunk.document_id)
            if not doc:
                continue

            content_lower = chunk.content.lower()
            matches = sum(1 for term in query_terms if term in content_lower)
            score = (matches / len(query_terms)) if query_terms else 0.0

            if matches > 0 or not query_terms:
                scored_results.append((score, chunk, doc))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, chunk, doc in scored_results[:limit]:
            results.append(
                CitationProvenance(
                    chunk_id=chunk.id,
                    document_id=doc.id,
                    document_title=doc.title,
                    source_uri=doc.source_uri,
                    page_or_section=chunk.page_or_section,
                    snippet=chunk.content,
                    similarity_score=score if score > 0 else 1.0,
                )
            )
        return results

    async def search_chunks_semantic(
        self,
        *,
        workspace_id: str,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[CitationProvenance]:
        """Cosine similarity trên `KnowledgeChunk.embedding` do caller cung cấp
        (P1 Task 6). Chỉ xét chunk cùng workspace VÀ có embedding cùng số chiều."""
        import math

        def cosine(a: list[float], b: list[float]) -> float:
            if not a or not b or len(a) != len(b):
                return -1.0
            dot = sum(x * y for x, y in zip(a, b, strict=False))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(y * y for y in b))
            return dot / (na * nb) if na and nb else -1.0

        scored: list[tuple[float, KnowledgeChunk, KnowledgeDocument]] = []
        for chunk in self._chunks.values():
            if chunk.workspace_id != workspace_id or not chunk.embedding:
                continue
            doc = self._docs.get(chunk.document_id)
            if not doc:
                continue
            scored.append((cosine(list(query_embedding), list(chunk.embedding)), chunk, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            CitationProvenance(
                chunk_id=chunk.id,
                document_id=doc.id,
                document_title=doc.title,
                source_uri=doc.source_uri,
                page_or_section=chunk.page_or_section,
                snippet=chunk.content,
                similarity_score=max(score, 0.0),
            )
            for score, chunk, doc in scored[:limit]
        ]


def get_knowledge_store(database_url: str | None = None) -> KnowledgeStore:
    """Production mặc định dùng PostgresKnowledgeStore — cùng nguyên tắc
    no-silent-fallback đã áp dụng cho get_memory_store() (DB_FINAL_CUTOVER.md
    §8-9). Muốn in-memory cho test/dev, dùng InMemoryKnowledgeStore() trực tiếp."""
    resolved_url = database_url or os.environ.get("AGENT_CORE_DATABASE_URL")
    if not resolved_url:
        raise RuntimeError(
            "get_knowledge_store() requires AGENT_CORE_DATABASE_URL to be set — "
            "production must not silently fall back to InMemoryKnowledgeStore. "
            "For tests/local dev, use InMemoryKnowledgeStore() directly."
        )
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from agent_core.knowledge.providers.postgres import PostgresKnowledgeStore

    engine = create_async_engine(resolved_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return PostgresKnowledgeStore(db_session_factory=factory)
