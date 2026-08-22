from __future__ import annotations

from agentos.core.embedding_provider import EmbeddingProvider
from agentos.knowledge.models import KnowledgeSearchResult
from agentos.knowledge.store import KnowledgeStore

DEFAULT_LIMIT = 5


class KnowledgeRetriever:
    """Truy xuất semantic thật (blueprint §66 "retrieve") — khác
    `agentos/memory/retrieval.py::score_relevance()` vốn chỉ term-overlap:
    ở đây câu hỏi được embed thật rồi so cosine similarity với chunk đã
    embed sẵn trong `KnowledgeStore`.
    """

    def __init__(self, embedding_provider: EmbeddingProvider, store: KnowledgeStore) -> None:
        self._embedding_provider = embedding_provider
        self._store = store

    async def retrieve(
        self, *, workspace_id: str, query_text: str, limit: int = DEFAULT_LIMIT
    ) -> list[KnowledgeSearchResult]:
        [query_embedding] = await self._embedding_provider.embed([query_text])
        return await self._store.search(workspace_id=workspace_id, query_embedding=query_embedding, limit=limit)
