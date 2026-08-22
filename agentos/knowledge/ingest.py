from __future__ import annotations

from agentos.core.embedding_provider import EmbeddingProvider
from agentos.knowledge.chunking import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, chunk_text
from agentos.knowledge.models import KnowledgeChunk, KnowledgeSource
from agentos.knowledge.store import KnowledgeStore


class KnowledgeIngestPipeline:
    """ingest → parse → chunk → embed → index (blueprint §66) — parse
    (trích text từ PDF/HTML/docx...) KHÔNG thuộc phạm vi này: pipeline nhận
    text đã trích sẵn (`raw_text`), caller chịu trách nhiệm parse định dạng
    gốc trước khi gọi `ingest()`. Đây là ranh giới cố tình, giống cách
    `EpisodeConsolidator` nhận `raw_episode_text` thay vì tự parse trace.
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

    async def ingest(self, source: KnowledgeSource, raw_text: str) -> list[KnowledgeChunk]:
        texts = chunk_text(raw_text, chunk_size=self._chunk_size, overlap=self._overlap)
        if not texts:
            await self._store.put_source(source)
            return []

        embeddings = await self._embedding_provider.embed(texts)
        chunks = [
            KnowledgeChunk(
                source_id=source.id,
                workspace_id=source.workspace_id,
                chunk_index=index,
                content=text,
                embedding=embedding,
            )
            for index, (text, embedding) in enumerate(zip(texts, embeddings))
        ]

        await self._store.put_source(source)
        await self._store.put_chunks(chunks)
        return chunks
