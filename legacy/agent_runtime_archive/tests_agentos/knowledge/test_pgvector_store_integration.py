"""Integration test cho PgVectorKnowledgeStore chạy với Postgres + pgvector thật
(không fake session) — đúng acceptance criteria 7C của phase-7-memory-knowledge.md.

Yêu cầu env var `AGENTOS_TEST_DATABASE_URL` trỏ tới 1 Postgres đã bật extension
`vector` và chạy migration `agentos/migrations/001_agent_memory_and_knowledge.sql`.
Bỏ qua (skip) nếu biến này không được set.
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("AGENTOS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="AGENTOS_TEST_DATABASE_URL not set — skipping real-Postgres integration test",
)


@pytest_asyncio.fixture
async def session_factory():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_insert_query_returns_reasonable_similarity_score(session_factory):
    from agentos.knowledge.models import KnowledgeChunk, KnowledgeSource, KnowledgeSourceType
    from agentos.knowledge.store import PgVectorKnowledgeStore

    store = PgVectorKnowledgeStore(db_session_factory=session_factory)
    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    source = KnowledgeSource(
        workspace_id=workspace_id,
        title="Company Refund Policy",
        source_type=KnowledgeSourceType.POLICY,
        uri="policy/refund.md",
    )
    await store.put_source(source)

    matching_chunk = KnowledgeChunk(
        source_id=source.id,
        workspace_id=workspace_id,
        chunk_index=0,
        content="Refunds are processed within 14 business days.",
        embedding=[1.0, 0.0, 0.0, 0.0],
        embedding_model="stub",
        embedding_dimensions=4,
        embedding_version="v1",
        content_hash="hash-a",
    )
    unrelated_chunk = KnowledgeChunk(
        source_id=source.id,
        workspace_id=workspace_id,
        chunk_index=1,
        content="The office is closed on public holidays.",
        embedding=[0.0, 1.0, 0.0, 0.0],
        embedding_model="stub",
        embedding_dimensions=4,
        embedding_version="v1",
        content_hash="hash-b",
    )
    await store.put_chunks([matching_chunk, unrelated_chunk])

    results = await store.search(workspace_id=workspace_id, query_embedding=[1.0, 0.0, 0.0, 0.0], limit=5)

    assert len(results) == 2
    assert results[0].chunk.id == matching_chunk.id
    assert results[0].score == pytest.approx(1.0, abs=1e-6)
    assert results[1].score < results[0].score

    await store.delete_source(source.id)


@pytest.mark.asyncio
async def test_workspace_isolation_at_sql_layer(session_factory):
    from agentos.knowledge.models import KnowledgeChunk, KnowledgeSource, KnowledgeSourceType
    from agentos.knowledge.store import PgVectorKnowledgeStore

    store = PgVectorKnowledgeStore(db_session_factory=session_factory)
    ws_a = f"ws-a-{uuid.uuid4().hex[:8]}"
    ws_b = f"ws-b-{uuid.uuid4().hex[:8]}"

    source_a = KnowledgeSource(workspace_id=ws_a, title="A Doc", source_type=KnowledgeSourceType.DOC)
    source_b = KnowledgeSource(workspace_id=ws_b, title="B Doc", source_type=KnowledgeSourceType.DOC)
    await store.put_source(source_a)
    await store.put_source(source_b)

    chunk_a = KnowledgeChunk(
        source_id=source_a.id,
        workspace_id=ws_a,
        chunk_index=0,
        content="Workspace A confidential content",
        embedding=[1.0, 0.0, 0.0, 0.0],
        content_hash="hash-ws-a",
    )
    chunk_b = KnowledgeChunk(
        source_id=source_b.id,
        workspace_id=ws_b,
        chunk_index=0,
        content="Workspace B confidential content",
        embedding=[1.0, 0.0, 0.0, 0.0],
        content_hash="hash-ws-b",
    )
    await store.put_chunks([chunk_a, chunk_b])

    results_a = await store.search(workspace_id=ws_a, query_embedding=[1.0, 0.0, 0.0, 0.0], limit=10)
    results_b = await store.search(workspace_id=ws_b, query_embedding=[1.0, 0.0, 0.0, 0.0], limit=10)

    assert {r.chunk.id for r in results_a} == {chunk_a.id}
    assert {r.chunk.id for r in results_b} == {chunk_b.id}

    await store.delete_source(source_a.id)
    await store.delete_source(source_b.id)


@pytest.mark.asyncio
async def test_ingest_markdown_end_to_end_then_search_finds_content(session_factory):
    from agentos.core.embedding_provider import StubEmbeddingProvider
    from agentos.knowledge.ingest import KnowledgeIngestPipeline
    from agentos.knowledge.models import KnowledgeSource, KnowledgeSourceType
    from agentos.knowledge.parsers.markdown import MarkdownParser
    from agentos.knowledge.retrieval import KnowledgeRetriever
    from agentos.knowledge.store import PgVectorKnowledgeStore

    store = PgVectorKnowledgeStore(db_session_factory=session_factory)
    embedding_provider = StubEmbeddingProvider(dimensions=8)
    pipeline = KnowledgeIngestPipeline(embedding_provider, store)

    workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
    source = KnowledgeSource(
        workspace_id=workspace_id,
        title="Onboarding Guide",
        source_type=KnowledgeSourceType.DOC,
        uri="docs/onboarding.md",
    )
    raw_markdown = "# Onboarding\n\nNew hires must complete security training within 7 days of joining."

    chunks = await pipeline.ingest(source, raw_markdown, parser=MarkdownParser())
    assert len(chunks) >= 1
    assert chunks[0].metadata["source_title"] == "Onboarding Guide"
    assert chunks[0].metadata["source_uri"] == "docs/onboarding.md"

    retriever = KnowledgeRetriever(embedding_provider, store)
    citations = await retriever.retrieve_citations(
        workspace_id=workspace_id,
        query_text="security training requirement",
    )

    assert len(citations) >= 1
    assert "security training" in citations[0].chunk_text.lower()
    assert citations[0].source_title == "Onboarding Guide"
    assert citations[0].source_uri == "docs/onboarding.md"

    await store.delete_source(source.id)
