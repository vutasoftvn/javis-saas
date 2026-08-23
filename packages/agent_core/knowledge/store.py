from __future__ import annotations

from typing import Any, Optional, Protocol
from agent_core.knowledge.models import CitationProvenance, KnowledgeChunk, KnowledgeDocument

__all__ = ["KnowledgeStore", "InMemoryKnowledgeStore"]


class KnowledgeStore(Protocol):
    async def save_document(self, doc: KnowledgeDocument) -> None: ...
    async def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]: ...
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

    async def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
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
