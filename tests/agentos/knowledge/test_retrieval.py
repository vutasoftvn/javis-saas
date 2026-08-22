import pytest

from agentos.core.embedding_provider import StubEmbeddingProvider
from agentos.knowledge.ingest import KnowledgeIngestPipeline
from agentos.knowledge.models import KnowledgeSource, KnowledgeSourceType
from agentos.knowledge.retrieval import KnowledgeRetriever
from agentos.knowledge.store import InMemoryKnowledgeStore


@pytest.mark.asyncio
async def test_retrieve_finds_the_chunk_most_similar_to_the_query():
    provider = StubEmbeddingProvider(dimensions=6)
    store = InMemoryKnowledgeStore()
    pipeline = KnowledgeIngestPipeline(provider, store, chunk_size=200, overlap=20)
    source = KnowledgeSource(workspace_id="ws1", title="Refund policy", source_type=KnowledgeSourceType.POLICY)
    await pipeline.ingest(source, "Refunds are processed within 14 business days of the return request.")

    retriever = KnowledgeRetriever(provider, store)
    results = await retriever.retrieve(workspace_id="ws1", query_text="Refunds are processed within 14 business days of the return request.", limit=3)

    assert len(results) >= 1
    # embed cùng 1 câu y hệt (StubEmbeddingProvider tất định theo nội dung)
    # phải cho similarity cao nhất có thể (chunk == query text).
    assert results[0].score == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_retrieve_scopes_by_workspace_id():
    provider = StubEmbeddingProvider(dimensions=4)
    store = InMemoryKnowledgeStore()
    pipeline = KnowledgeIngestPipeline(provider, store)
    await pipeline.ingest(
        KnowledgeSource(workspace_id="ws-a", title="Doc A", source_type=KnowledgeSourceType.DOC), "content in workspace A"
    )
    await pipeline.ingest(
        KnowledgeSource(workspace_id="ws-b", title="Doc B", source_type=KnowledgeSourceType.DOC), "content in workspace B"
    )

    retriever = KnowledgeRetriever(provider, store)
    results = await retriever.retrieve(workspace_id="ws-a", query_text="content in workspace A")

    assert all(r.chunk.workspace_id == "ws-a" for r in results)
