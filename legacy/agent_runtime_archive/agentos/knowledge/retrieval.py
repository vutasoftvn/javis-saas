from __future__ import annotations

from typing import Optional, Union

from agentos.core.embedding_provider import EmbeddingProvider
from agentos.core.models import TaskContext
from agentos.knowledge.models import KnowledgeCitation, KnowledgeSearchResult
from agentos.knowledge.store import KnowledgeStore

DEFAULT_LIMIT = 5


class KnowledgeRetriever:
    """Semantic knowledge retrieval pipeline (blueprint §66 "retrieve").
    
    Embeds the user goal/query and performs cosine similarity search
    against vector embeddings stored in `KnowledgeStore`.
    """

    def __init__(self, embedding_provider: EmbeddingProvider, store: KnowledgeStore) -> None:
        self._embedding_provider = embedding_provider
        self._store = store

    async def retrieve(
        self,
        task_or_workspace_id: Optional[Union[TaskContext, str]] = None,
        *,
        workspace_id: Optional[str] = None,
        query_text: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> list[KnowledgeSearchResult]:
        """Retrieve top semantic search results."""
        if isinstance(task_or_workspace_id, TaskContext):
            target_workspace_id = task_or_workspace_id.workspace_id
            target_query = task_or_workspace_id.goal
        elif isinstance(task_or_workspace_id, str):
            target_workspace_id = task_or_workspace_id
            target_query = query_text or ""
        else:
            target_workspace_id = workspace_id or ""
            target_query = query_text or ""

        if not target_workspace_id or not target_query:
            return []

        embeddings = await self._embedding_provider.embed([target_query])
        if not embeddings:
            return []
        query_embedding = embeddings[0]
        return await self._store.search(
            workspace_id=target_workspace_id,
            query_embedding=query_embedding,
            limit=limit,
        )

    async def retrieve_citations(
        self,
        *,
        workspace_id: str,
        query_text: str,
        limit: int = DEFAULT_LIMIT,
    ) -> list[KnowledgeCitation]:
        """Retrieve citations containing structured provenance for knowledge snippets."""
        results = await self.retrieve(workspace_id=workspace_id, query_text=query_text, limit=limit)
        citations: list[KnowledgeCitation] = []
        for res in results:
            section_or_page = res.chunk.metadata.get("section") or res.chunk.metadata.get("heading")
            citations.append(
                KnowledgeCitation(
                    chunk_id=res.chunk.id,
                    source_id=res.chunk.source_id,
                    source_title=res.chunk.metadata.get("source_title"),
                    source_uri=res.chunk.metadata.get("source_uri"),
                    chunk_text=res.chunk.content,
                    page_or_section=section_or_page,
                    similarity_score=res.score,
                )
            )
        return citations

    async def retrieve_for_task(
        self,
        task: TaskContext,
        limit: int = DEFAULT_LIMIT,
    ) -> list[KnowledgeCitation]:
        """Convenience method to retrieve structured citations for a given TaskContext."""
        return await self.retrieve_citations(
            workspace_id=task.workspace_id,
            query_text=task.goal,
            limit=limit,
        )
