import pytest

from agentos.core.embedding_provider import StubEmbeddingProvider
from agentos.core.models import TaskContext
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
    assert not any(r.chunk.workspace_id == "ws-b" for r in results)


@pytest.mark.asyncio
async def test_retrieve_citations_and_retrieve_for_task():
    provider = StubEmbeddingProvider(dimensions=4)
    store = InMemoryKnowledgeStore()
    pipeline = KnowledgeIngestPipeline(provider, store)
    source = KnowledgeSource(workspace_id="ws1", title="Onboarding Handbook", source_type=KnowledgeSourceType.MANUAL)
    await pipeline.ingest(source, "Step 1: Set up email. Step 2: Join Slack.")

    retriever = KnowledgeRetriever(provider, store)
    task = TaskContext(workspace_id="ws1", agent_key="hr", goal="Set up email")

    citations = await retriever.retrieve_for_task(task)
    assert len(citations) >= 1
    assert citations[0].source_id == source.id
    assert "Set up email" in citations[0].chunk_text


@pytest.mark.asyncio
async def test_retrieve_empty_workspace_returns_empty_list():
    provider = StubEmbeddingProvider(dimensions=4)
    store = InMemoryKnowledgeStore()
    retriever = KnowledgeRetriever(provider, store)

    results = await retriever.retrieve(workspace_id="empty-ws", query_text="any question")
    assert results == []
