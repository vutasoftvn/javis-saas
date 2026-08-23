import pytest

from agentos.core.embedding_provider import EmbeddingProvider, StubEmbeddingProvider
from agentos.knowledge.ingest import IngestEmbeddingMismatchError, KnowledgeIngestPipeline
from agentos.knowledge.models import KnowledgeSource, KnowledgeSourceType
from agentos.knowledge.parsers.markdown import MarkdownParser
from agentos.knowledge.store import InMemoryKnowledgeStore


class _MismatchEmbeddingProvider(EmbeddingProvider):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Returns fewer vectors than requested texts
        return [[0.1, 0.2]] if texts else []


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
    assert all(c.content_hash is not None for c in chunks)
    assert all(c.embedding_dimensions == 4 for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    results = await store.search(workspace_id="ws1", query_embedding=chunks[0].embedding)
    assert results[0].chunk.id == chunks[0].id


@pytest.mark.asyncio
async def test_ingest_raises_on_embedding_count_mismatch():
    provider = _MismatchEmbeddingProvider()
    store = InMemoryKnowledgeStore()
    pipeline = KnowledgeIngestPipeline(provider, store, chunk_size=30, overlap=5)
    source = KnowledgeSource(workspace_id="ws1", title="Test doc", source_type=KnowledgeSourceType.DOC)

    # 100 characters with chunk_size=30 produces > 1 chunks
    with pytest.raises(IngestEmbeddingMismatchError) as exc_info:
        await pipeline.ingest(source, "This is a long text chunking into multiple pieces for testing.")
    assert "Failing ingest to prevent silent data loss" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ingest_stores_the_source_even_when_text_is_blank():
    provider = StubEmbeddingProvider()
    store = InMemoryKnowledgeStore()
    pipeline = KnowledgeIngestPipeline(provider, store)
    source = KnowledgeSource(workspace_id="ws1", title="Empty doc", source_type=KnowledgeSourceType.DOC)

    chunks = await pipeline.ingest(source, "   ")

    assert chunks == []
    assert provider.calls == []  # không gọi embedding API cho input rỗng


@pytest.mark.asyncio
async def test_ingest_with_markdown_parser():
    provider = StubEmbeddingProvider(dimensions=4)
    store = InMemoryKnowledgeStore()
    pipeline = KnowledgeIngestPipeline(provider, store)
    source = KnowledgeSource(workspace_id="ws1", title="Policy", source_type=KnowledgeSourceType.POLICY)

    md_content = """# Company Policy
<!-- Internal Note -->
All employees must log expenses by Friday.
"""
    chunks = await pipeline.ingest(source, md_content, parser=MarkdownParser())
    assert len(chunks) >= 1
    assert "Internal Note" not in chunks[0].content
    assert "All employees must log expenses by Friday" in chunks[0].content
