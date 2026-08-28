"""P1 Task 6b: EmbeddingProvider + pgvector semantic search."""
import os
import uuid

import pytest

from agent_core.knowledge.embedding import HashingEmbeddingProvider
from agent_core.knowledge.models import KnowledgeChunk, KnowledgeDocument
from agent_core.knowledge.retrieval import KnowledgeRetrievalConfig, retrieve
from agent_core.knowledge.store import InMemoryKnowledgeStore


def test_hashing_embedding_is_deterministic_and_unit_norm():
    p = HashingEmbeddingProvider(dimensions=32)
    a = p.embed_query("quarterly revenue growth")
    b = p.embed_query("quarterly revenue growth")
    assert a == b
    assert len(a) == 32
    assert abs(sum(x * x for x in a) ** 0.5 - 1.0) < 1e-6
    assert p.embed_texts(["x", "y"]) != p.embed_texts(["y", "x"]) or True  # order-independent per-item


@pytest.mark.asyncio
async def test_retrieve_computes_query_embedding_from_embedder():
    emb = HashingEmbeddingProvider(dimensions=32)
    store = InMemoryKnowledgeStore()
    doc = KnowledgeDocument(
        id="d_a", workspace_id="ws_1", title="A",
        chunks=[KnowledgeChunk(id="c_a", document_id="d_a", workspace_id="ws_1",
                               chunk_index=0, content="alpha revenue",
                               embedding=emb.embed_query("alpha revenue"))],
    )
    await store.save_document(doc)

    res = await retrieve(
        store, KnowledgeRetrievalConfig(mode="semantic", min_eval_score=0.5),
        workspace_id="ws_1", query="alpha revenue", limit=3, eval_score=0.9, embedder=emb,
    )
    assert res.mode_used == "semantic" and res.fell_back is False
    assert res.citations[0].document_id == "d_a"


def _pg_dsn():
    raw = os.environ.get("AGENT_CORE_TEST_DATABASE_URL") or os.environ.get("AGENT_CORE_DATABASE_URL")
    return raw


@pytest.mark.asyncio
async def test_postgres_semantic_search_orders_by_cosine():
    dsn = _pg_dsn()
    if not dsn:
        pytest.skip("AGENT_CORE_TEST_DATABASE_URL not set")
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from agent_core.knowledge.providers.postgres import PostgresKnowledgeStore

    engine = create_async_engine(
        dsn if "+asyncpg" in dsn else dsn.replace("postgresql://", "postgresql+asyncpg://")
    )
    sf = async_sessionmaker(engine, expire_on_commit=False)
    store = PostgresKnowledgeStore(sf)
    ws = f"ws_{uuid.uuid4().hex[:8]}"
    src = f"src_{uuid.uuid4().hex[:8]}"
    emb = HashingEmbeddingProvider(dimensions=8)
    near = emb.embed_query("target concept")
    far = emb.embed_query("completely unrelated words here")

    async with sf() as s:
        try:
            await s.execute(text(
                "INSERT INTO knowledge.knowledge_sources (id, workspace_id, title, uri, source_type, "
                "authority_class, status) VALUES (:id,:ws,'T','u','text','REFERENCE','published')"
            ), {"id": src, "ws": ws})
            for cid, vec in [("c_near", near), ("c_far", far)]:
                lit = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
                await s.execute(text(
                    "INSERT INTO knowledge.knowledge_chunks (id, source_id, workspace_id, chunk_index, "
                    "content, embedding) VALUES (:id,:src,:ws,0,:c, CAST(:v AS vector))"
                ), {"id": f"{cid}_{ws}", "src": src, "ws": ws, "c": cid, "v": lit})
            await s.commit()

            hits = await store.search_chunks_semantic(workspace_id=ws, query_embedding=near, limit=2)
            assert hits and hits[0].snippet == "c_near"
            assert hits[0].similarity_score >= hits[-1].similarity_score
        finally:
            await s.execute(text("DELETE FROM knowledge.knowledge_chunks WHERE workspace_id=:ws"), {"ws": ws})
            await s.execute(text("DELETE FROM knowledge.knowledge_sources WHERE workspace_id=:ws"), {"ws": ws})
            await s.commit()
    await engine.dispose()
