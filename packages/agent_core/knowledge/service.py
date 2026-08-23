from __future__ import annotations

import hashlib
import uuid
from typing import Any, Optional
from agent_core.knowledge.chunking import chunk_text
from agent_core.knowledge.models import CitationProvenance, KnowledgeChunk, KnowledgeDocument
from agent_core.knowledge.store import InMemoryKnowledgeStore, KnowledgeStore

__all__ = ["KnowledgeIngestionService"]


class KnowledgeIngestionService:
    """Service chịu trách nhiệm ingest, chunk và retrieve Knowledge theo Master Guide §26."""

    def __init__(self, store: Optional[KnowledgeStore] = None) -> None:
        self._store = store or InMemoryKnowledgeStore()

    async def ingest_raw_text(
        self,
        *,
        workspace_id: str,
        title: str,
        text_content: str,
        source_uri: Optional[str] = None,
        media_type: str = "text/plain",
        chunk_size: int = 800,
        overlap: int = 100,
    ) -> KnowledgeDocument:
        checksum = hashlib.sha256(text_content.encode("utf-8")).hexdigest()
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"

        raw_chunks = chunk_text(text_content, chunk_size=chunk_size, overlap=overlap)
        chunk_models = []
        for idx, c_text in enumerate(raw_chunks):
            chunk_models.append(
                KnowledgeChunk(
                    id=f"chk_{doc_id}_{idx}",
                    document_id=doc_id,
                    workspace_id=workspace_id,
                    chunk_index=idx,
                    content=c_text,
                    page_or_section=f"Section {idx + 1}",
                )
            )

        doc = KnowledgeDocument(
            id=doc_id,
            workspace_id=workspace_id,
            title=title,
            source_uri=source_uri,
            media_type=media_type,
            checksum=checksum,
            ingest_status="completed",
            chunks=chunk_models,
        )

        await self._store.save_document(doc)
        return doc

    async def retrieve_citations(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int = 5,
    ) -> list[CitationProvenance]:
        return await self._store.search_chunks(
            workspace_id=workspace_id,
            query=query,
            limit=limit,
        )
