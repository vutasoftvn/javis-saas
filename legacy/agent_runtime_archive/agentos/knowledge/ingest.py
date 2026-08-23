from __future__ import annotations

import hashlib
from typing import Optional

from agentos.core.embedding_provider import EmbeddingProvider
from agentos.knowledge.chunking import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, chunk_text
from agentos.knowledge.models import KnowledgeChunk, KnowledgeSource
from agentos.knowledge.parsers.base import DocumentParser
from agentos.knowledge.store import KnowledgeStore


class IngestEmbeddingMismatchError(ValueError):
    """Raised when the embedding provider returns an unexpected number of embedding vectors."""
    pass


class KnowledgeIngestPipeline:
    """ingest → parse → chunk → embed → index pipeline (blueprint §66).
    
    Supports optional `DocumentParser` (or auto-resolved parser) to process raw markdown/text
    before chunking and embedding.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        store: KnowledgeStore,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._store = store
        self._chunk_size = chunk_size
        self._overlap = overlap

    async def ingest(
        self,
        source: KnowledgeSource,
        raw_text: str | bytes,
        parser: Optional[DocumentParser] = None,
    ) -> list[KnowledgeChunk]:
        # Parse document if parser is provided or if input is bytes
        if parser is not None:
            text_to_chunk = parser.parse(raw_text, filename=source.uri or source.title)
        elif isinstance(raw_text, bytes):
            text_to_chunk = raw_text.decode("utf-8", errors="replace")
        else:
            text_to_chunk = raw_text

        texts = chunk_text(text_to_chunk, chunk_size=self._chunk_size, overlap=self._overlap)
        if not texts:
            await self._store.put_source(source)
            return []

        embeddings = await self._embedding_provider.embed(texts)
        if len(embeddings) != len(texts):
            raise IngestEmbeddingMismatchError(
                f"Embedding provider returned {len(embeddings)} vectors for {len(texts)} chunks. "
                "Failing ingest to prevent silent data loss."
            )

        model_name = getattr(self._embedding_provider, "model", None) or getattr(
            self._embedding_provider, "model_name", "default"
        )

        chunks: list[KnowledgeChunk] = []
        for index, (chunk_text_value, embedding) in enumerate(zip(texts, embeddings)):
            content_hash = hashlib.sha256(chunk_text_value.encode("utf-8")).hexdigest()
            dimensions = len(embedding) if embedding else None
            chunks.append(
                KnowledgeChunk(
                    source_id=source.id,
                    workspace_id=source.workspace_id,
                    chunk_index=index,
                    content=chunk_text_value,
                    embedding=embedding,
                    embedding_model=str(model_name),
                    embedding_dimensions=dimensions,
                    embedding_version="v1",
                    content_hash=content_hash,
                    metadata={"source_title": source.title, "source_uri": source.uri},
                )
            )

        await self._store.put_source(source)
        await self._store.put_chunks(chunks)
        return chunks
