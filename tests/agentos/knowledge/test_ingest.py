import pytest

from agentos.core.embedding_provider import StubEmbeddingProvider
from agentos.knowledge.ingest import KnowledgeIngestPipeline
from agentos.knowledge.models import KnowledgeSource, KnowledgeSourceType
from agentos.knowledge.store import InMemoryKnowledgeStore


@pytest.mark.asyncio
async def test_ingest_chunks_embeds_and_stores_every_chunk():
    provider = StubEmbeddingProvider(dimensions=4)
    store = InMemoryKnowledgeStore()
    pipeline = KnowledgeIngestPipeline(provider, store, chunk_size=50, overlap=10)
    source = KnowledgeSource(workspace_id="ws1", title="Onboarding guide", source_type=KnowledgeSourceType.DOC)

    chunks = await pipeline.ingest(source, "a" * 120)

    assert len(chunks) > 1
    assert all(c.source_id == source.id for c in chunks)
    assert all(c.workspace_id == "ws1" for c in chunks)
    assert all(c.embedding is not None for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    results = await store.search(workspace_id="ws1", query_embedding=chunks[0].embedding)
    assert results[0].chunk.id == chunks[0].id


@pytest.mark.asyncio
async def test_ingest_stores_the_source_even_when_text_is_blank():
    provider = StubEmbeddingProvider()
    store = InMemoryKnowledgeStore()
    pipeline = KnowledgeIngestPipeline(provider, store)
    source = KnowledgeSource(workspace_id="ws1", title="Empty doc", source_type=KnowledgeSourceType.DOC)

    chunks = await pipeline.ingest(source, "   ")

    assert chunks == []
    assert provider.calls == []  # không gọi embedding API cho input rỗng
